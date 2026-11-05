import os
from django.core.management.base import BaseCommand
from django.conf import settings
from protocollo.models import Documento


class Command(BaseCommand):
    help = 'Collega i file fisici esistenti ai record Documento'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        docs = Documento.objects.all()
        totali = docs.count()
        self.stdout.write(f'Documenti totali: {totali}')
        count = 0
        aggiornati = 0
        for d in docs:
            count += 1
            if d.document and d.document.name:
                continue
            filename = (d.name or '').strip()
            if not filename:
                continue
            rel_path = os.path.join('protocollo', 'uploads', filename)
            abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                if options['dry_run']:
                    self.stdout.write(f'AGGIORNA {d.pk}: {rel_path}')
                else:
                    d.document.name = rel_path
                    d.save(update_fields=['document'])
                    aggiornati += 1
            else:
                self.stdout.write(self.style.WARNING(f'File non trovato per {d.pk}: {abs_path}'))
            if count % 500 == 0 or count == totali:
                self.stdout.write(f'  {count}/{totali}')
        self.stdout.write(self.style.SUCCESS(f'Documenti aggiornati: {aggiornati}'))
