from django.core.management.base import BaseCommand
from grandi_lavori.models import RegistroGrandiLavori

PERIODS = {
    '1922-1948': ['A','B','C','D','E','F','G','I','L','M','N','O','P','Q','R','S','T','U','W-Z'],
    '1949-1955': ['A','B','C','D','E','F','G','H','I','L','M','N','O','P','Q','R','S','T','U','V','Z'],
    '1956-1964': ['A','B','C','D','E','F','G','I','L','M','N','O','P','Q','R','S','T','U','V','Z'],
    '1965-1970': ['A','B','C','D','E','F','G','I','L','M','N','O','P','Q','R','S','T','U','V','Z'],
    '1971-1976': ['A','B','C','D','E','F','G','I','L','M','N','O','P','Q','R','S','T','U','VW','Z'],
    '1977-1981': ['A','B','C','D','E','F','G','K','I','L','M','N','O','P','Q','R','S','T','U','V','Z'],
    '1982-1986': ['A','B','C','D','E','F','G','K','I','J','L','M','N','O','P','R','S','T','U','V','Z','VARIE'],
    '1987-1990': ['A','B','C','D','E','F','G','K','I','L','M','N','O','P','Q','R','S','T','U','V','Z'],
    '1991-1992': ['A','B','C','D','E','F','G','I','L','M','N','O','P','R','S','T','U','V'],
}

PERIOD_SEP = {
    '1922-1948': '_',
    '1949-1955': '_',
    '1956-1964': '_',
    '1965-1970': '_',
    '1971-1976': '_',
    '1977-1981': '_',
    '1982-1986': '_',
    '1987-1990': '_',
    '1991-1992': '_',
}

LETTERA_SUFFIX = {
    'W-Z': 'wz',
    'VW': 'vw',
    'VARIE': 'varie',
}


class Command(BaseCommand):
    help = 'Popola i registri Grandi Lavori'

    def handle(self, *args, **options):
        for periodo, lettere in PERIODS.items():
            sep = PERIOD_SEP[periodo]
            for lettera in lettere:
                suffix = LETTERA_SUFFIX.get(lettera, lettera.lower())
                filename = f"GRANDI_LAVORI{sep}{periodo.replace('-', sep)}_{suffix}.pdf"
                titolo = lettera
                obj, created = RegistroGrandiLavori.objects.get_or_create(
                    periodo=periodo,
                    lettera=lettera,
                    defaults={'titolo': titolo, 'filename': filename}
                )
                if created:
                    self.stdout.write(f"Creato {periodo} - {titolo}")
        self.stdout.write("Popolamento completato.")
