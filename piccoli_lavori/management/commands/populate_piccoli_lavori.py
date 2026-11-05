from django.core.management.base import BaseCommand
from piccoli_lavori.models import RegistroPiccoliLavori

PERIODS = {
    '1953-1957': ['A','B','C','D','E','F','G','I','L','M','N','O','P','Q','R','S','T','U','V','Z'],
    '1958-1967': ['A','B','C','D','E','F','G','H','I','L','M','N','O','P','Q','R','S','T','U','V-W','Z'],
    '1968-1976': ['A','B','C','D','E','F','G','I-J','L','M','N','O','P','Q','R','S','T','U','V-W','Z'],
    '1977-1981': ['A','B','C','D','F','G','I-K','L','M','N','O','P','R','S','T','U-V','W-Z'],
    '1982-1983': ['A','B','C','D','E','F','G','H-I-K','L','M','N','O','P-Q','R','S','T-U','V-W','Z'],
    '1984-1986': ['A','B','C','D','E','F','G','I-K','L','M','N','O','P-Q','R','S','T','U','V','Z'],
    '1987-1990': ['Indice'],
    '1991-1992': ['Indice'],
}

SUFFIX_MAP = {
    'I-J': 'I_J',
    'I-K': 'I_K',
    'U-V': 'U_V',
    'V-W': 'V_W',
    'H-I-K': 'H_I_K',
    'P-Q': 'P_Q',
    'T-U': 'T_U',
    'W-Z': 'W_Z',
    'Indice': '',
}


class Command(BaseCommand):
    help = 'Popola i registri Piccoli Lavori'

    def handle(self, *args, **options):
        for periodo, lettere in PERIODS.items():
            for lettera in lettere:
                suffix = SUFFIX_MAP.get(lettera, lettera)
                if suffix:
                    filename = f"PICCOLI_LAVORI_{periodo.replace('-', '_')}_{suffix}.pdf"
                else:
                    filename = f"PICCOLI_LAVORI_{periodo.replace('-', '_')}.pdf"
                titolo = lettera
                obj, created = RegistroPiccoliLavori.objects.get_or_create(
                    periodo=periodo,
                    lettera=lettera,
                    defaults={'titolo': titolo, 'filename': filename}
                )
                if created:
                    self.stdout.write(f"Creato {periodo} - {titolo}")
        self.stdout.write("Popolamento completato.")
