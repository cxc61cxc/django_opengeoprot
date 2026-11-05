import csv
import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry
from protocollo.models import (
    TipoPratica, Soggetto, Particella, Pratica, TipoSoggetto,
    Anaprat, Cataprat, Diario, Documento, SostituzioneSoggetto
)
from django.contrib.auth import get_user_model
from viario.models import Civici

User = get_user_model()

class Command(BaseCommand):
    help = 'Importa dati da esportazioni CSV/JSON del gestionale PHP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tabella',
            type=str,
            required=True,
            help='Nome tabella da importare (tipopratica, soggetto, particella, pratica, ...)'
        )
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Percorso del file CSV/JSON da importare'
        )
        parser.add_argument(
            '--encoding',
            type=str,
            default='utf-8',
            help='Encoding del file (default: utf-8)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        tabella = options['tabella'].lower()
        file_path = options['file']
        encoding = options['encoding']

        if not os.path.exists(file_path):
            raise CommandError(f'File non trovato: {file_path}')

        if tabella == 'tipopratica':
            self.importa_tipopratica(file_path, encoding)
        elif tabella == 'soggetto':
            self.importa_soggetto(file_path, encoding)
        elif tabella == 'particella':
            self.importa_particella(file_path, encoding)
        elif tabella == 'pratica':
            self.importa_pratica(file_path, encoding)
        else:
            raise CommandError(f'Tabella {tabella} non supportata da questo comando')

    # ------------------------------------------------------------------
    # TIPOPRATICA
    # ------------------------------------------------------------------
    def importa_tipopratica(self, file_path, encoding):
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter='|')
            count = 0
            for row in reader:
                user = None
                uid = row.get('user_id')
                if uid and uid.strip():
                    try:
                        user = User.objects.get(pk=int(uid))
                    except User.DoesNotExist:
                        user = None

                TipoPratica.objects.update_or_create(
                    name=row['name'].strip(),
                    defaults={
                        'description': row.get('description', '').strip() or None,
                        'user': user,
                        'settore': row.get('settore', '').strip() or None,
                    }
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Importati/aggiornati {count} TipoPratica'))

    # ------------------------------------------------------------------
    # SOGGETTO
    # ------------------------------------------------------------------
    def importa_soggetto(self, file_path, encoding):
        """
        Atteso CSV con intestazioni simili a:
        cognome,nome,data_nascita,comune_nascita,codice_fiscale,
        comune_residenza,addr,addr_sede,email,pec,cellulare,telefono,fax,user_id
        """
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=',')
            count = 0
            for row in reader:
                user = None
                uid = row.get('user_id')
                if uid and uid.strip():
                    try:
                        user = User.objects.get(pk=int(uid))
                    except User.DoesNotExist:
                        user = None

                Soggetto.objects.update_or_create(
                    cognome=row.get('cognome', '').strip(),
                    nome=row.get('nome', '').strip(),
                    codice_fiscale=row.get('codice_fiscale', '').strip() or None,
                    defaults={
                        'data_nascita': row.get('data_nascita') or None,
                        'comune_nascita': row.get('comune_nascita', '').strip() or None,
                        'comune_residenza': row.get('comune_residenza', '').strip() or None,
                        'addr': row.get('addr', '').strip() or None,
                        'addr_sede': row.get('addr_sede', '').strip() or None,
                        'email': row.get('email', '').strip() or None,
                        'pec': row.get('pec', '').strip() or None,
                        'cellulare': row.get('cellulare', '').strip() or None,
                        'telefono': row.get('telefono', '').strip() or None,
                        'fax': row.get('fax', '').strip() or None,
                        'user': user,
                    }
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Importati/aggiornati {count} Soggetto'))

    # ------------------------------------------------------------------
    # PARTICELLA
    # ------------------------------------------------------------------
    def importa_particella(self, file_path, encoding):
        """
        Atteso CSV con intestazioni: foglio,mappale,mpoly (WKT o EWKT)
        Se il CSV non ha geometria, imporla solo con foglio e mappale.
        """
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=',')
            count = 0
            for row in reader:
                foglio = row.get('foglio', '').strip()
                mappale = row.get('mappale', '').strip()
                mpoly_wkt = row.get('mpoly', '').strip()

                defaults = {}
                if mpoly_wkt:
                    try:
                        defaults['mpoly'] = GEOSGeometry(mpoly_wkt, srid=4326)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(
                            f'Geometria non valida per particella {foglio}-{mappale}: {e}'
                        ))

                Particella.objects.update_or_create(
                    foglio=foglio,
                    mappale=mappale,
                    defaults=defaults
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Importati/aggiornati {count} Particella'))

    # ------------------------------------------------------------------
    # PRATICA
    # ------------------------------------------------------------------
    def importa_pratica(self, file_path, encoding):
        """
        Importa Pratica gestendo:
        - FK a TipoPratica (per name o per vecchio ID)
        - FK a Civici (strada)
        - FK a User
        - M2M con Soggetto (Anaprat) e Particella (Cataprat)
        
        Per le M2M si assume che nel CSV/JSON ci siano colonne come:
        soggetti_json: [{"cognome":" Rossi","nome":"Mario","tipo":"richiedente"}, ...]
        particelle_json: [{"foglio":"1","mappale":"2","subalterno":"1"}, ...]
        Oppure campi separati: soggetti_ids, particelle_ids, ecc.
        """
        with open(file_path, 'r', encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=',')
            count = 0
            for row in reader:
                # --- FK TipoPratica ---
                tipo_pratica = None
                tp_name = row.get('tipo_pratica_name', '').strip()
                tp_vecchio_id = row.get('tipo_pratica_id', '').strip()
                if tp_name:
                    tipo_pratica = TipoPratica.objects.filter(name__iexact=tp_name).first()
                if not tipo_pratica and tp_vecchio_id:
                    # Se hai salvato una mappatura vecchio_id -> nuovo_id,
                    # usala qui. Altrimenti cerca per nome.
                    pass

                # --- FK Civici (strada) ---
                street = None
                civico_id = row.get('street_id', '').strip()
                if civico_id:
                    try:
                        street = Civici.objects.get(pk=int(civico_id))
                    except Civici.DoesNotExist:
                        street = None

                # --- FK User ---
                user = None
                uid = row.get('user_id')
                if uid and uid.strip():
                    try:
                        user = User.objects.get(pk=int(uid))
                    except User.DoesNotExist:
                        user = None

                pratica, created = Pratica.objects.update_or_create(
                    prot_gen=row.get('prot_gen', '').strip(),
                    data_prot_gen=row.get('data_prot_gen') or None,
                    defaults={
                        'stato': row.get('stato', 'a').strip() or 'a',
                        'code_p': int(row['code_p']) if row.get('code_p') else None,
                        'classe': int(row['classe']) if row.get('classe') else None,
                        'sub_code': int(row['sub_code']) if row.get('sub_code') else None,
                        'street': street,
                        'housenumber': row.get('housenumber', '').strip() or None,
                        'tipo_pratica': tipo_pratica,
                        'oggetto': row.get('oggetto', '').strip() or None,
                        'annotazioni': row.get('annotazioni', '').strip() or None,
                        'user': user,
                    }
                )

                # --- M2M Soggetto (Anaprat) ---
                soggetti_raw = row.get('soggetti_json', '').strip()
                if soggetti_raw:
                    try:
                        soggetti_list = json.loads(soggetti_raw)
                        for s in soggetti_list:
                            cognome = s.get('cognome', '').strip()
                            nome = s.get('nome', '').strip()
                            tipo_nome = s.get('tipo', '').strip()
                            if not cognome or not nome:
                                continue

                            soggetto, _ = Soggetto.objects.get_or_create(
                                cognome=cognome,
                                nome=nome,
                                codice_fiscale=s.get('codice_fiscale', '').strip() or None,
                                defaults={
                                    'data_nascita': s.get('data_nascita') or None,
                                    'comune_nascita': s.get('comune_nascita', '').strip() or None,
                                    'comune_residenza': s.get('comune_residenza', '').strip() or None,
                                    'addr': s.get('addr', '').strip() or None,
                                    'email': s.get('email', '').strip() or None,
                                    'pec': s.get('pec', '').strip() or None,
                                    'cellulare': s.get('cellulare', '').strip() or None,
                                    'telefono': s.get('telefono', '').strip() or None,
                                    'fax': s.get('fax', '').strip() or None,
                                    'user': user,
                                }
                            )

                            tipo_sogg = None
                            if tipo_nome:
                                tipo_sogg, _ = TipoSoggetto.objects.get_or_create(
                                    name=tipo_nome,
                                    defaults={'user': user}
                                )

                            Anaprat.objects.update_or_create(
                                pratica=pratica,
                                soggetto=soggetto,
                                tipo=tipo_sogg,
                                defaults={'user': user}
                            )
                    except json.JSONDecodeError:
                        self.stdout.write(self.style.WARNING(
                            f'JSON non valido per soggetti in pratica {pratica.prot_gen}'
                        ))

                # --- M2M Particella (Cataprat) ---
                particelle_raw = row.get('particelle_json', '').strip()
                if particelle_raw:
                    try:
                        particelle_list = json.loads(particelle_raw)
                        for p in particelle_list:
                            foglio = p.get('foglio', '').strip()
                            mappale = p.get('mappale', '').strip()
                            subalterno = p.get('subalterno', '-').strip() or '-'
                            if not foglio or not mappale:
                                continue

                            particella, _ = Particella.objects.get_or_create(
                                foglio=foglio,
                                mappale=mappale
                            )

                            Cataprat.objects.update_or_create(
                                pratica=pratica,
                                particella=particella,
                                defaults={
                                    'subalterno': subalterno,
                                    'user': user
                                }
                            )
                    except json.JSONDecodeError:
                        self.stdout.write(self.style.WARNING(
                            f'JSON non valido per particelle in pratica {pratica.prot_gen}'
                        ))

                count += 1

        self.stdout.write(self.style.SUCCESS(f'Importati/aggiornati {count} Pratica'))
