from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Rinumerate gli ID della tabella Particelle partendo da 1 e rende la colonna auto-incrementale'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.stdout.write('Assegnazione ID sequenziali da 1...')
            cursor.execute('BEGIN;')
            cursor.execute('''
                UPDATE catasto_particelle p
                SET id = sub.new_id
                FROM (
                    SELECT ctid, row_number() OVER (ORDER BY ctid) AS new_id
                    FROM catasto_particelle
                ) sub
                WHERE p.ctid = sub.ctid;
            ''')
            cursor.execute('''
                CREATE SEQUENCE IF NOT EXISTS catasto_particelle_id_seq;
            ''')
            cursor.execute('''
                ALTER TABLE catasto_particelle ALTER COLUMN id SET DEFAULT nextval('catasto_particelle_id_seq');
            ''')
            cursor.execute('''
                ALTER TABLE catasto_particelle ALTER COLUMN id SET NOT NULL;
            ''')
            cursor.execute('''
                SELECT setval('catasto_particelle_id_seq', COALESCE(MAX(id), 1), false) FROM catasto_particelle;
            ''')
            cursor.execute('COMMIT;')

            cursor.execute('SELECT min(id), max(id), count(*) FROM catasto_particelle')
            row = cursor.fetchone()
            self.stdout.write(self.style.SUCCESS(f'ID aggiornati: min={row[0]}, max={row[1]}, count={row[2]}'))
