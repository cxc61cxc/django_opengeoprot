from django.core.management.base import BaseCommand
from licenze_edilizie.models import RegistroLicenzeEdilizie

PERIODS = [
    ('1969-1975', 'LICENZE_EDILIZIE_1969-1975.pdf'),
    ('1976-1979', 'LICENZE_EDILIZIE_1976-1979.pdf'),
    ('1980-1984', 'LICENZE_EDILIZIE_1980-1984.pdf'),
    ('1985-1988', 'LICENZE_EDILIZIE_1985-1988.pdf'),
    ('1989-1992', 'LICENZE_EDILIZIE_1989-1992.pdf'),
]

class Command(BaseCommand):
    help = 'Popola i registri Licenze Edilizie'

    def handle(self, *args, **options):
        for periodo, filename in PERIODS:
            obj, created = RegistroLicenzeEdilizie.objects.get_or_create(
                periodo=periodo,
                defaults={'titolo': periodo, 'filename': filename}
            )
            if created:
                self.stdout.write(f"Creato {periodo}")
        self.stdout.write("Popolamento completato.")
