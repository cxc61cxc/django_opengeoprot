import getpass
import psycopg2
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Mostra esempi di ubicazione dal DB sorgente'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='dbsrvgis')
        parser.add_argument('--port', default='5432')
        parser.add_argument('--dbname', default='protocollo')
        parser.add_argument('--user', default='cxc')
        parser.add_argument('--password', default=None)
        parser.add_argument('--limit', type=int, default=20)

    def handle(self, *args, **options):
        password = options['password']
        if not password:
            password = getpass.getpass('Password PostgreSQL sorgente: ')
        conn = psycopg2.connect(
            host=options['host'],
            port=options['port'],
            dbname=options['dbname'],
            user=options['user'],
            password=password,
        )
        cur = conn.cursor()
        cur.execute('SELECT ubicazione FROM pratiche WHERE ubicazione IS NOT NULL LIMIT %s', (options['limit'],))
        for r in cur.fetchall():
            self.stdout.write(r[0])
        cur.close()
        conn.close()
