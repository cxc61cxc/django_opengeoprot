import getpass
import psycopg2
import sys
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Ispetta il database sorgente (PHP) e mostra tabelle/colonne'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='dbsrvgis')
        parser.add_argument('--port', default='5432')
        parser.add_argument('--dbname', default='protocollo')
        parser.add_argument('--user', default='cxc')
        parser.add_argument('--password', default=None)

    def handle(self, *args, **options):
        password = options['password']
        if not password:
            password = getpass.getpass('Password per PostgreSQL: ')

        conn = psycopg2.connect(
            host=options['host'],
            port=options['port'],
            dbname=options['dbname'],
            user=options['user'],
            password=password
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tabelle = [r[0] for r in cur.fetchall()]

        self.stdout.write(self.style.SUCCESS(f'Trovate {len(tabelle)} tabelle:'))
        for t in tabelle:
            self.stdout.write(f' - {t}')

        self.stdout.write('\nColonne per tabella:\n')
        for t in tabelle:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (t,))
            cols = cur.fetchall()
            self.stdout.write(f'[{t}]')
            for c in cols:
                self.stdout.write(f'   {c[0]} ({c[1]})')
            self.stdout.write('')

        # Salva output su file
        out_path = '/tmp/db_sorgente_struttura.txt'
        with open(out_path, 'w', encoding='utf-8') as out:
            out.write(f'Trovate {len(tabelle)} tabelle:\n')
            for t in tabelle:
                out.write(f' - {t}\n')
            out.write('\nColonne per tabella:\n')
            for t in tabelle:
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position;
                """, (t,))
                cols = cur.fetchall()
                out.write(f'[{t}]\n')
                for c in cols:
                    out.write(f'   {c[0]} ({c[1]})\n')
                out.write('\n')

        cur.close()
        conn.close()
        self.stdout.write(self.style.SUCCESS(f'Struttura salvata in {out_path}'))
