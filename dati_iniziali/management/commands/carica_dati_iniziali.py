import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dati_iniziali import io_csv


class Command(BaseCommand):
    help = (
        'Carica al primo avvio i dati iniziali generati con export_dati_iniziali: '
        'prima i gruppi (con i permessi), poi i tipi di pratica. '
        'I riferimenti mancanti (settore, servizio, u.o., utente) restano vuoti '
        'e vengono segnalati.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            dest='cartella',
            default=None,
            help='Cartella contenente i CSV (default: <BASE_DIR>/data)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Aggiorna i record gia presenti (descrizione, riferimenti, permessi).',
        )
        parser.add_argument(
            '--keep-ids',
            action='store_true',
            help='Mantiene gli id originali (colonna id_orig) dei tipi di pratica.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Non scrive nulla: mostra cosa verrebbe fatto.',
        )

    def handle(self, *args, **options):
        cartella = options['cartella'] or os.path.join(settings.BASE_DIR, 'data')
        for file in (io_csv.FILE_GRUPPI, io_csv.FILE_TIPO_PRATICA):
            if not os.path.exists(os.path.join(cartella, file)):
                raise CommandError(
                    f'File non trovato: {os.path.join(cartella, file)}. '
                    'Esegui prima "python manage.py export_dati_iniziali".'
                )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Modalita dry-run: nessuna scrittura.'))

        report_gruppi = io_csv.carica_gruppi(
            os.path.join(cartella, io_csv.FILE_GRUPPI),
            force=options['force'],
            dry_run=options['dry_run'],
        )
        self._stampa('GRUPPI', report_gruppi)

        report_tipi = io_csv.carica_tipo_pratica(
            os.path.join(cartella, io_csv.FILE_TIPO_PRATICA),
            force=options['force'],
            keep_ids=options['keep_ids'],
            dry_run=options['dry_run'],
        )
        self._stampa('TIPI DI PRATICA', report_tipi)

    def _stampa(self, titolo, report):
        self.stdout.write(f'\n{titolo}')
        self.stdout.write(
            f"  creati: {report['creati']} - gia presenti: {report['presenti']} "
            f"- aggiornati: {report['aggiornati']}"
        )
        for avviso in report['avvisi']:
            self.stdout.write(self.style.WARNING(f'  ! {avviso}'))
