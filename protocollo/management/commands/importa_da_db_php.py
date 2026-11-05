import getpass
import psycopg2
import re
from datetime import datetime
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.contrib.gis.db.models import Union

from protocollo.models import (
    TipoPratica, Soggetto, Particella, Pratica, TipoSoggetto,
    Anaprat, Cataprat, Diario, Documento, SostituzioneSoggetto
)
from django.contrib.auth import get_user_model
from viario.models import Civici

User = get_user_model()


def _normalize_name(value):
    if value is None:
        return ''
    value = str(value).strip()
    value = re.sub(r'\s+', ' ', value)
    return value


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, (datetime,)):
        return value.date()
    value = str(value).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_ubicazione(value):
    if not value:
        return None, None
    value = str(value).strip()
    if not value:
        return None, None

    if ',' in value:
        parts = value.split(',', 1)
        via = parts[0].strip()
        civico = parts[1].strip()
        return via, civico

    m = re.search(r'(?:n\.?\s*)(\S+)\s*$', value, re.IGNORECASE)
    if m:
        civico = m.group(1)
        via = value[:m.start()].strip()
        return via, civico

    tokens = value.rsplit(' ', 1)
    if len(tokens) == 2 and len(tokens[1]) <= 5:
        return tokens[0].strip(), tokens[1].strip()

    return value.strip(), None


def _match_street(via):
    if not via:
        return None
    via = via.strip()
    if not via:
        return None
    return Civici.objects.filter(street__iexact=via).first() or Civici.objects.filter(street__icontains=via).first()


class Command(BaseCommand):
    help = 'Importa dati dal DB sorgente PHP (dbsrvgis.protocollo)'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='dbsrvgis')
        parser.add_argument('--port', default='5432')
        parser.add_argument('--dbname', default='protocollo')
        parser.add_argument('--user', default='cxc')
        parser.add_argument('--password', default=None)
        parser.add_argument('--solo-pratiche', action='store_true')
        parser.add_argument('--solo-soggetti', action='store_true')
        parser.add_argument('--solo-part', action='store_true')

    def _connect(self, options):
        password = options['password']
        if not password:
            password = getpass.getpass('Password per PostgreSQL sorgente: ')
        return psycopg2.connect(
            host=options['host'],
            port=options['port'],
            dbname=options['dbname'],
            user=options['user'],
            password=password,
        )

    def _reset_sequences(self):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT sequence_name 
                FROM information_schema.sequences 
                WHERE sequence_schema = 'public' 
                AND sequence_name LIKE '%_id_seq'
            """)
            for (seq_name,) in cursor.fetchall():
                table_name = seq_name.replace('_id_seq', '')
                try:
                    cursor.execute(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1, false)")
                except Exception:
                    pass

    def handle(self, *args, **options):
        conn = self._connect(options)
        conn.autocommit = True
        cur = conn.cursor()

        self._reset_sequences()

        if options['solo_soggetti']:
            self.importa_soggetti(cur)
        elif options['solo_part']:
            self.importa_particelle(cur)
        elif options['solo_pratiche']:
            self.importa_pratiche(cur)
        else:
            self.stdout.write(self.style.NOTICE('Import completo'))
            self.importa_soggetti(cur)
            self.importa_particelle(cur)
            self.importa_pratiche(cur)

        self._reset_sequences()

        cur.close()
        conn.close()

    # ------------------------------------------------------------------
    # SOGGETTI
    # ------------------------------------------------------------------
    def importa_soggetti(self, cur):
        self.stdout.write('Importazione soggetti...')
        cur.execute('SELECT id, cognome, nome, codice_fiscale, data_nascita, comune_nascita, comune_residenza, addr, email, tel FROM soggetti')
        rows = cur.fetchall()
        count = 0
        for r in rows:
            _id, cognome, nome, cf, dn, cn, cr, addr, email, tel = r
            defaults = {
                'data_nascita': _parse_date(dn),
                'comune_nascita': _normalize_name(cn)[:80] or None,
                'comune_residenza': _normalize_name(cr)[:80] or None,
                'addr': _normalize_name(addr)[:150] or None,
                'email': _normalize_name(email)[:254] or None,
                'pec': None,
                'cellulare': _normalize_name(tel)[:100] or None,
                'telefono': _normalize_name(tel)[:100] or None,
                'fax': None,
                'user': None,
            }
            Soggetto.objects.update_or_create(
                cognome=_normalize_name(cognome)[:150],
                nome=_normalize_name(nome)[:100],
                codice_fiscale=(_normalize_name(cf)[:16] if _normalize_name(cf) else None),
                defaults=defaults,
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Soggetti importati/aggiornati: {count}'))

    # ------------------------------------------------------------------
    # PARTICELLE
    # ------------------------------------------------------------------
    def importa_particelle(self, cur):
        self.stdout.write('Importazione particelle...')
        cur.execute('SELECT DISTINCT fg, map FROM vw_particelle_pratica WHERE fg IS NOT NULL AND map IS NOT NULL')
        rows = cur.fetchall()
        count = 0
        for fg, mp in rows:
            Particella.objects.get_or_create(
                foglio=_normalize_name(fg),
                mappale=_normalize_name(mp),
                defaults={'mpoly': None},
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Particelle create/trovate: {count}'))

    # ------------------------------------------------------------------
    # PRATICHE + ANAPRAT + CATAPRAT
    # ------------------------------------------------------------------
    def importa_pratiche(self, cur):
        self.stdout.write('Importazione pratiche...')

        # Mappa tipo -> TipoPratica
        cur.execute('SELECT DISTINCT tipo_pratica FROM pratiche WHERE tipo_pratica IS NOT NULL')
        tipi = {_normalize_name(r[0]) for r in cur.fetchall()}
        tipo_map = {}
        for nome in tipi:
            tp, _ = TipoPratica.objects.get_or_create(name=nome, defaults={'description': None, 'user': None, 'settore': None})
            tipo_map[nome] = tp

        # Precarico soggetti per lookup rapido
        soggetti_by_key = {(s.cognome, s.nome, s.codice_fiscale): s for s in Soggetto.objects.all()}
        soggetti_by_id = {int(s.id): s for s in Soggetto.objects.all()}

        cur.execute("""
            SELECT
                p.id_pratica,
                p.prot_gen,
                p.data_prot_gen,
                p.tipo_pratica,
                p.oggetto,
                p.ubicazione,
                p.nota,
                p.protint,
                p.num_prog,
                p.codifica,
                p.geom
            FROM pratiche p
            WHERE p.prot_gen IS NOT NULL
        """)
        rows = cur.fetchall()
        totali = len(rows)
        count = 0

        for r in rows:
            (
                id_pratica,
                prot_gen,
                data_prot_gen,
                tipo_pratica,
                oggetto,
                ubicazione,
                nota,
                protint,
                num_prog,
                codifica,
                geom,
            ) = r

            # Normalizza prot_gen
            if prot_gen is not None:
                prot_gen = str(int(prot_gen))
            else:
                continue

            tipo = tipo_map.get(_normalize_name(tipo_pratica))

            via, civico = _parse_ubicazione(ubicazione)
            street_obj = _match_street(via)

            geom_obj = None
            if geom is not None:
                try:
                    geom_obj = GEOSGeometry(str(geom), srid=4326)
                except Exception:
                    geom_obj = None

            pratica, _ = Pratica.objects.get_or_create(
                prot_gen=prot_gen,
                data_prot_gen=data_prot_gen,
                defaults={
                    'stato': 'a',
                    'code_p': None,
                    'classe': None,
                    'sub_code': None,
                    'street': street_obj,
                    'housenumber': civico,
                    'posizione': geom_obj,
                    'mpoly_pratica': None,
                    'tipo_pratica': tipo,
                    'oggetto': _normalize_name(oggetto) or None,
                    'annotazioni': _normalize_name(ubicazione) or None,
                    'user': None,
                },
            )

            # Aggiorna annotazioni se nel sorgente è più ricco
            if nota and (not pratica.annotazioni or len(nota) > len(pratica.annotazioni or '')):
                pratica.annotazioni = _normalize_name(nota)
                pratica.save(update_fields=['annotazioni', 'mpoly_pratica', 'data_mod'])

            # ANAPRAT da anaprat
            cur.execute('SELECT id_soggetto, tipo_soggetto FROM anaprat WHERE id_pratica = %s', (id_pratica,))
            for id_soggetto, tipo_soggetto in cur.fetchall():
                soggetto = soggetti_by_id.get(int(id_soggetto))
                if not soggetto:
                    continue
                tipo_sogg = None
                ts = _normalize_name(tipo_soggetto)
                if ts:
                    tipo_sogg, _ = TipoSoggetto.objects.get_or_create(name=ts, defaults={'user': None})
                Anaprat.objects.get_or_create(
                    pratica=pratica,
                    soggetto=soggetto,
                    tipo=tipo_sogg,
                    defaults={'user': None},
                )

            # ANAPRAT da vw_soggetti_pratica (completa)
            cur.execute('SELECT id_soggetto, tipo_soggetto, cognome, nome, codice_fiscale FROM vw_soggetti_pratica WHERE id_pratica = %s', (id_pratica,))
            for id_soggetto, tipo_soggetto, cognome, nome, cf in cur.fetchall():
                if id_soggetto is None:
                    continue
                soggetto = soggetti_by_id.get(int(id_soggetto))
                if not soggetto:
                    key = (_normalize_name(cognome), _normalize_name(nome), _normalize_name(cf))
                    soggetto = soggetti_by_key.get(key)
                if not soggetto:
                    continue
                tipo_sogg = None
                ts = _normalize_name(tipo_soggetto)
                if ts:
                    tipo_sogg, _ = TipoSoggetto.objects.get_or_create(name=ts, defaults={'user': None})
                Anaprat.objects.get_or_create(
                    pratica=pratica,
                    soggetto=soggetto,
                    tipo=tipo_sogg,
                    defaults={'user': None},
                )

            # CATAPRAT da vw_particelle_pratica
            cur.execute('SELECT fg, map, sub FROM vw_particelle_pratica WHERE id_pratica = %s', (id_pratica,))
            for fg, mp, sub in cur.fetchall():
                if not fg or not mp:
                    continue
                particella, _ = Particella.objects.get_or_create(
                    foglio=_normalize_name(fg),
                    mappale=_normalize_name(mp),
                    defaults={'mpoly': None},
                )
                Cataprat.objects.get_or_create(
                    pratica=pratica,
                    particella=particella,
                    defaults={
                        'subalterno': _normalize_name(sub) or '-',
                        'user': None,
                    },
                )

            count += 1
            if count % 500 == 0 or count == totali:
                self.stdout.write(f'  {count}/{totali}')

        self.stdout.write(self.style.SUCCESS(f'Pratiche importate: {count}'))
        self.stdout.write('Ricalcolo geometrie pratiche...')
        self._ricalcola_geometrie()

    def _ricalcola_geometrie(self):
        pratiche = Pratica.objects.all()
        totali = pratiche.count()
        count = 0
        for p in pratiche:
            p.update_mpoly_pratica()
            count += 1
            if count % 500 == 0 or count == totali:
                self.stdout.write(f'  {count}/{totali}')
