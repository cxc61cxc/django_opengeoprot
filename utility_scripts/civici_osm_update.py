#!/usr/bin/env python
import os
import sys
import argparse
import csv
import tempfile
import subprocess
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carrara.settings')

import django
django.setup()

from django.db import connections

try:
    import osmium
    HAS_PYOSMIUM = True
except ImportError:
    HAS_PYOSMIUM = False

if not HAS_PYOSMIUM:
    try:
        from lxml import etree
    except ImportError:
        print("ERRORE: pyosmium o lxml sono necessari per l'elaborazione.", file=sys.stderr)
        sys.exit(1)


def download_file(url, dest_path):
    print(f"Download in corso da {url}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
        print("Download completato.")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(
                f"File non trovato su Geofabrik (404). "
                f"Verifica che l'URL sia corretto: {url}\n"
                f"Controlla https://download.geofabrik.de/ per la URL aggiornata."
            ) from e
        raise RuntimeError(f"Errore HTTP {e.code} durante il download: {e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"Errore durante il download: {e}") from e


def filter_osm(input_path, output_path):
    cmd = [
        'osmium', 'tags-filter',
        input_path,
        'n/addr:street',
        '-o', output_path,
    ]
    print(f"Filtraggio: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True)
    print("Filtraggio completato.")


def get_table_columns(cursor, table_name='civici_osm'):
    cursor.execute(
        "SELECT string_agg(quote_ident(column_name), ',' ORDER BY ordinal_position) "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        [table_name],
    )
    row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"Tabella {table_name} non trovata")
    return [c.strip('"') for c in row[0].split(',')]


def process_with_pyosmium(filtered_file):
    class CiviciHandler(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.nodes = {}

        def node(self, n):
            tags = dict(n.tags)
            is_carrara = tags.get('addr:city') == 'Carrara' or tags.get('addr:postcode') == '54033'
            has_civico = 'addr:housenumber' in tags
            is_entrance = tags.get('entrance', '') in ['yes', 'main', 'home', 'service']
            if is_carrara and (has_civico or is_entrance):
                if n.id not in self.nodes:
                    self.nodes[n.id] = {'creation': n, 'last': n}
                else:
                    self.nodes[n.id]['last'] = n

    handler = CiviciHandler()
    handler.apply_file(filtered_file)
    print(f"Trovati {len(handler.nodes)} civici/ingressi validi per Carrara")
    return handler.nodes


def process_with_xml(filtered_file):
    nodes = {}
    xml_temp = filtered_file + '.xml'

    print("Conversione in XML per elaborazione...")
    with open(xml_temp, 'wb') as f:
        subprocess.run(
            ['osmium', 'show', '-t', 'node', '-f', 'xml', filtered_file],
            stdout=f,
            check=True,
        )

    context = etree.iterparse(xml_temp, events=('end',), tag='node')
    for event, elem in context:
        nid = int(elem.get('id'))
        version = int(elem.get('version'))
        visible = elem.get('visible', 'true') != 'false'
        timestamp = elem.get('timestamp', '')
        user = elem.get('user', '')
        lon = elem.get('lon')
        lat = elem.get('lat')

        tags = {}
        for tag in elem.findall('tag'):
            tags[tag.get('k')] = tag.get('v')

        is_carrara = tags.get('addr:city') == 'Carrara' or tags.get('addr:postcode') == '54033'
        has_civico = 'addr:housenumber' in tags
        is_entrance = tags.get('entrance', '') in ['yes', 'main', 'home', 'service']

        if is_carrara and (has_civico or is_entrance) and visible:
            if nid not in nodes:
                nodes[nid] = {
                    'creation': {
                        'id': nid,
                        'version': version,
                        'user': user,
                        'timestamp': timestamp,
                        'tags': dict(tags),
                        'lon': lon,
                        'lat': lat,
                    },
                    'last': None,
                }

            if nodes[nid]['last'] is None or version > nodes[nid]['last']['version']:
                nodes[nid]['last'] = {
                    'id': nid,
                    'version': version,
                    'user': user,
                    'timestamp': timestamp,
                    'tags': dict(tags),
                    'lon': lon,
                    'lat': lat,
                }

        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    os.remove(xml_temp)
    print(f"Trovati {len(nodes)} civici/ingressi validi per Carrara")
    return nodes


def write_csv(nodes, columns, csv_path):
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)

        for node_id, data in nodes.items():
            creation = data['creation']
            last = data['last']
            tags = last['tags']

            row = []
            for col in columns:
                if col == 'id':
                    row.append(str(node_id))
                elif col == 'geom':
                    if last['lon'] and last['lat']:
                        row.append(f"SRID=4326;POINT({last['lon']} {last['lat']})")
                    else:
                        row.append('')
                elif col == '@id':
                    row.append(f"node/{node_id}")
                elif col == 'last_user':
                    row.append(last['user'])
                elif col == 'last_timestamp':
                    row.append(last['timestamp'])
                elif col == 'creation_user':
                    row.append(creation['user'])
                elif col == 'creation_timestamp':
                    row.append(creation['timestamp'])
                else:
                    row.append(tags.get(col, ''))

            writer.writerow(row)

    print(f"CSV generato: {csv_path} ({len(nodes)} record)")


def load_to_db(csv_path, columns):
    conn_wrapper = connections['anagrafe_civica']
    conn_wrapper.ensure_connection()
    raw_conn = conn_wrapper.connection

    col_list = ', '.join(f'"{c}"' for c in columns)

    with raw_conn.cursor() as cur:
        cur.execute('TRUNCATE TABLE public.civici_osm')
        with open(csv_path, 'r', encoding='utf-8') as f:
            cur.copy_expert(
                f'COPY public.civici_osm ({col_list}) FROM STDIN WITH CSV HEADER',
                f,
            )

    print("Dati caricati con successo.")


def verify(cursor, columns):
    counts = [
        "COUNT(*) AS totale",
        "COUNT(last_user) AS con_last_user",
        "COUNT(last_timestamp) AS con_last_ts",
    ]
    if 'creation_user' in columns:
        counts.append("COUNT(creation_user) AS con_creation_user")
    if 'creation_timestamp' in columns:
        counts.append("COUNT(creation_timestamp) AS con_creation_ts")

    cursor.execute(f"SELECT {', '.join(counts)} FROM public.civici_osm")
    row = cursor.fetchone()
    print(f"Verifica: {row}")

    if 'creation_user' in columns:
        try:
            cursor.execute(
                'SELECT id, "addr:street", "addr:housenumber", last_user, creation_user '
                'FROM public.civici_osm WHERE creation_user IS NOT NULL LIMIT 5',
            )
            rows = cursor.fetchall()
            for r in rows:
                print(r)
        except Exception as e:
            print(f"Attenzione: lettura creation_user non riuscita ({e})")
    else:
        print("Colonna creation_user non presente, salto query dettaglio.")


def main():
    parser = argparse.ArgumentParser(description='Aggiorna civici OSM per Carrara')
    parser.add_argument('--osm-url',
                        default='https://download.geofabrik.de/europe/italy-latest.osm.pbf',
                        help='URL del file OSM (.osm.pbf o .osh.pbf)')
    parser.add_argument('--osm-file', default=None,
                        help='Percorso di un file OSM locale (salta il download)')
    parser.add_argument('--work-dir', default=None)
    args = parser.parse_args()

    work_dir = args.work_dir or tempfile.mkdtemp(prefix='osm_carrara_')
    osm_file = args.osm_file or os.path.join(work_dir, 'italy-latest.osm.pbf')
    filtered_file = os.path.join(work_dir, 'carrara_civici.osh.pbf')
    csv_file = os.path.join(work_dir, 'civici.csv')

    os.makedirs(work_dir, exist_ok=True)

    print("=" * 50)
    print("Aggiornamento civici OSM - Carrara")
    print(f"Work dir: {work_dir}")
    print(f"pyosmium: {'SI' if HAS_PYOSMIUM else 'NO (uso XML fallback)'}")
    print("=" * 50)

    if not HAS_PYOSMIUM:
        global etree
        from lxml import etree

    success = False
    try:
        if args.osm_file:
            print(f"[1/5] Uso file locale: {osm_file}")
            if not os.path.exists(osm_file):
                raise RuntimeError(f"File locale non trovato: {osm_file}")
        elif not os.path.exists(osm_file):
            print("[1/5] Download OSM Italia...")
            download_file(args.osm_url, osm_file)
        else:
            print("[1/5] File OSM già presente, salto download.")

        print("[2/5] Filtraggio locale (nodi con addr:street)...")
        filter_osm(osm_file, filtered_file)

        print("[3/5] Lettura schema tabella PostGIS...")
        conn_wrapper = connections['anagrafe_civica']
        with conn_wrapper.cursor() as cursor:
            columns = get_table_columns(cursor)
        print(f"Colonne rilevate: {len(columns)}")

        print("[4/5] Elaborazione metadati e generazione CSV...")
        if HAS_PYOSMIUM:
            nodes = process_with_pyosmium(filtered_file)
        else:
            nodes = process_with_xml(filtered_file)

        write_csv(nodes, columns, csv_file)

        print("[5/5] TRUNCATE e caricamento in PostGIS...")
        load_to_db(csv_file, columns)

        print("\n=== VERIFICA FINALE ===")
        with conn_wrapper.cursor() as cursor:
            verify(cursor, columns)

        success = True

    finally:
        if os.path.exists(filtered_file):
            os.remove(filtered_file)
        if os.path.exists(csv_file):
            os.remove(csv_file)
        if success:
            print(f"\nCompletato. Work dir: {work_dir}")


if __name__ == '__main__':
    main()
