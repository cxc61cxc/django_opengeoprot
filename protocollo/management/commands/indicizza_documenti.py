import os

from django.core.management.base import BaseCommand
from django.conf import settings

from protocollo.models import Documento, IndiceDocumento


class Command(BaseCommand):
    help = 'Indicizza in blocco il testo estratto di tutti i documenti allegati per la ricerca full-text rapida.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forza',
            action='store_true',
            help='Ricalcola anche i documenti già indicizzati.',
        )

    def handle(self, *args, **options):
        # Import lazy per evitare import circolare con protocollo.views
        from protocollo.views import (
            _estrai_testo_documento,
            _testo_coerente,
            _sanitizza_testo,
        )  # noqa: WPS433

        qs = Documento.objects.exclude(document='').exclude(document__isnull=True)

        if not options['forza']:
            # Escludi i documenti già indicizzati con testo non vuoto
            gia_indici = set(
                IndiceDocumento.objects
                .exclude(testo='')
                .values_list('documento_id', flat=True)
            )
            qs = qs.exclude(id__in=gia_indici)

        totale = qs.count()
        self.stdout.write("Documenti da indicizzare: {}".format(totale))

        indicizzati = 0
        saltati = 0
        incoerenti = 0
        errori = 0

        for i, doc in enumerate(qs.iterator(), start=1):
            filepath = os.path.join(settings.MEDIA_ROOT, doc.document.name)
            if not os.path.exists(filepath) or not os.path.isfile(filepath):
                saltati += 1
                self.stdout.write(
                    "[{}/{}] SALTATO (file assente): {}".format(i, totale, doc.document.name)
                )
                continue

            try:
                testo = _estrai_testo_documento(filepath)
            except Exception as e:
                errori += 1
                self.stdout.write(self.style.WARNING(
                    "[{}/{}] ERRORE estrazione {}: {}".format(i, totale, doc.document.name, e)
                ))
                continue

            testo = _sanitizza_testo(testo)

            if not _testo_coerente(testo):
                incoerenti += 1
                continue

            IndiceDocumento.objects.update_or_create(
                documento=doc,
                defaults={'testo': testo},
            )
            indicizzati += 1
            if i % 50 == 0:
                self.stdout.write("[{}/{}] indicizzati finora: {}".format(i, totale, indicizzati))

        self.stdout.write(self.style.SUCCESS(
            "Completato. Indicizzati: {}, saltati (file assente): {}, incoerenti (no testo valido): {}, errori: {} / totale esaminati: {}".format(
                indicizzati, saltati, incoerenti, errori, totale
            )
        ))
