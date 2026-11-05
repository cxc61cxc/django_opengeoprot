import os
import re
import shutil
import getpass
import psycopg2
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.base import File
from django.db import transaction

from protocollo.models import Pratica, Documento
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Importa allegati da upload_file del DB sorgente PHP'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='dbsrvgis')
        parser.add_argument('--port', default='5432')
        parser.add_argument('--dbname', default='protocollo')
        parser.add_argument('--user', default='cxc')
        parser.add_argument('--password', default=None)
        parser.add_argument('--source-dir', default='', help='Cartella sorgente uploads (opzionale)')
        parser.add_argument('--skip-files', action='store_true', help='Importa solo metadati senza copiare i file')
        parser.add_argument('--dry-run', action='store_true')

    def _connect(self, options):
        password = options['password']
        if not password:
            password = getpass.getpass('Password PostgreSQL sorgente: ')
        return psycopg2.connect(
            host=options['host'],
            port=options['port'],
            dbname=options['dbname'],
            user=options['user'],
            password=password,
        )

    @transaction.atomic
    def handle(self, *args, **options):
        conn = self._connect(options)
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute('SELECT id_pratica, prot_gen, data_prot_gen FROM pratiche WHERE prot_gen IS NOT NULL')
        mappa = {}
        for old_id, prot_gen, data_prot_gen in cur.fetchall():
            prot_gen = str(int(prot_gen)) if prot_gen is not None else None
            mappa[old_id] = (prot_gen, data_prot_gen)

        pratiche_lookup = {}
        for p in Pratica.objects.all():
            if p.data_prot_gen:
                pratiche_lookup[(str(p.prot_gen), p.data_prot_gen)] = p

        cur.execute('SELECT id_up, id_pratica, data_crea_up, nome_up FROM upload_file ORDER BY id_up')
        rows = cur.fetchall()
        totali = len(rows)
        self.stdout.write(f'Record upload_file: {totali}')

        count = 0
        creati = 0
        saltati = 0
        for id_up, id_pratica, data_crea_up, nome_up in rows:
            nome_up = (nome_up or '').strip()
            if not nome_up:
                saltati += 1
                continue

            key = mappa.get(int(id_pratica))
            if not key:
                saltati += 1
                continue
            prot_gen, data_prot_gen = key
            pratica = pratiche_lookup.get((prot_gen, data_prot_gen))
            if not pratica:
                saltati += 1
                continue

            defaults = {
                'posta': 'c',
                'prot': prot_gen[:20] if prot_gen else None,
                'data_prot': data_prot_gen,
                'name': nome_up[:700],
                'username': None,
            }

            if options['dry_run']:
                self.stdout.write(f'[{id_up}] -> pratica {pratica.id} | {nome_up}')
            else:
                doc, created = Documento.objects.update_or_create(
                    pratica=pratica,
                    name=nome_up[:700],
                    defaults=defaults,
                )

                if not options['skip_files'] and options['source_dir']:
                    source_path = os.path.join(options['source_dir'], nome_up)
                    if os.path.exists(source_path):
                        rel_path = os.path.join('protocollo', 'uploads', os.path.basename(nome_up))
                        dest_abs = os.path.join(settings.MEDIA_ROOT, rel_path)
                        os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
                        if not os.path.exists(dest_abs):
                            shutil.copy2(source_path, dest_abs)
                        with open(dest_abs, 'rb') as f:
                            doc.document.save(os.path.basename(nome_up), File(f), save=True)
                        if created:
                            creati += 1
                    else:
                        self.stdout.write(self.style.WARNING(f'File non trovato: {source_path}'))
                else:
                    if created:
                        creati += 1

            count += 1
            if count % 500 == 0 or count == totali:
                self.stdout.write(f'  {count}/{totali}')

        cur.close()
        conn.close()
        self.stdout.write(self.style.SUCCESS(f'Documenti creati/aggiornati: {creati}, saltati: {saltati}'))
