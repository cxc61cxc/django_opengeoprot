import os
from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from django.db import connection
from catasto.models import Particelle


class Command(BaseCommand):
    help = 'Importa le particelle da uno shapefile, svuotando prima la tabella e rinumerando gli ID'

    def add_arguments(self, parser):
        parser.add_argument(
            'shp_path',
            nargs='?',
            default='/home/cxc/Scrivania/particelle/particelle.shp',
            help='Percorso al file .shp delle particelle'
        )

    def handle(self, *args, **options):
        shp_path = options['shp_path']

        if not os.path.exists(shp_path):
            self.stdout.write(self.style.ERROR(f'File non trovato: {shp_path}'))
            return

        self.stdout.write('Svuotamento tabella Particelle...')
        deleted, _ = Particelle.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Eliminati {deleted} record precedenti.'))

        self.stdout.write(f'Lettura shapefile: {shp_path}')
        ds = DataSource(shp_path)
        layer = ds[0]
        objs = []
        for idx, feature in enumerate(layer, start=1):
            foglio_raw = feature.get('Foglio')
            mappale = feature.get('Mappale')

            if foglio_raw is None:
                foglio = None
            else:
                foglio = str(int(foglio_raw)).zfill(4)

            geom = feature.geom
            geos_geom = geom.geos
            if geos_geom.geom_type == 'Polygon':
                mpoly = MultiPolygon([geos_geom])
            elif geos_geom.geom_type == 'MultiPolygon':
                mpoly = MultiPolygon(list(geos_geom))
            else:
                self.stdout.write(self.style.WARNING(f'Tipo geometria non supportato: {geos_geom.geom_type}, salto.'))
                continue

            objs.append(Particelle(
                id=idx,
                foglio=foglio,
                mappale=mappale,
                mpoly=mpoly
            ))

        Particelle.objects.bulk_create(objs, batch_size=1000)
        count = len(objs)
        self.stdout.write(self.style.SUCCESS(f'Importazione completata: {count} particelle inserite.'))

        self.stdout.write('Aggiornamento sequenza ID...')
        with connection.cursor() as cursor:
            cursor.execute('''
                CREATE SEQUENCE IF NOT EXISTS catasto_particelle_id_seq;
            ''')
            cursor.execute('''
                ALTER TABLE catasto_particelle ALTER COLUMN id SET DEFAULT nextval('catasto_particelle_id_seq');
            ''')
            cursor.execute('''
                SELECT setval('catasto_particelle_id_seq', COALESCE(MAX(id), 1), false) FROM catasto_particelle;
            ''')
            cursor.execute('SELECT min(id), max(id), count(*) FROM catasto_particelle')
            row = cursor.fetchone()
            self.stdout.write(self.style.SUCCESS(f'ID aggiornati: min={row[0]}, max={row[1]}, count={row[2]}'))
