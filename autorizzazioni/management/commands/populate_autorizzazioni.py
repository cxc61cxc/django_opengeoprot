from django.core.management.base import BaseCommand
from autorizzazioni.models import RegistroAutorizzazioni

PERIODS = [
    ('1985-1988', 'AUTORIZZAZIONI_1985-1988.pdf'),
]

class Command(BaseCommand):
    help = 'Popola i registri Autorizzazioni'

    def handle(self, *args, **options):
        for periodo, filename in PERIODS:
            obj, created = RegistroAutorizzazioni.objects.get_or_create(
                periodo=periodo,
                defaults={'titolo': periodo, 'filename': filename}
            )
            if created:
                self.stdout.write(f"Creato {periodo}")
        self.stdout.write("Popolamento completato.")
