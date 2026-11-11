import os

from django.conf import settings
from django.core.management.base import BaseCommand

from dati_iniziali import io_csv


class Command(BaseCommand):
    help = (
        'Esporta in CSV i dati iniziali da caricare al primo avvio: '
        'tipi di pratica (tipo_pratica.csv) e gruppi con i permessi (gruppi.csv).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            dest='cartella',
            default=None,
            help='Cartella di destinazione (default: <BASE_DIR>/data)',
        )

    def handle(self, *args, **options):
        cartella = options['cartella'] or os.path.join(settings.BASE_DIR, 'data')
        percorso_tipi = os.path.join(cartella, io_csv.FILE_TIPO_PRATICA)
        percorso_gruppi = os.path.join(cartella, io_csv.FILE_GRUPPI)

        righe_tipi = io_csv.esporta_tipo_pratica(percorso_tipi)
        righe_gruppi = io_csv.esporta_gruppi(percorso_gruppi)

        self.stdout.write(self.style.SUCCESS(
            f'Tipi di pratica: {righe_tipi} righe -> {percorso_tipi}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Gruppi: {righe_gruppi} righe -> {percorso_gruppi}'
        ))
        self.stdout.write(
            'Per caricarli sul nuovo sistema: python manage.py carica_dati_iniziali '
            f'--dir "{cartella}"'
        )
