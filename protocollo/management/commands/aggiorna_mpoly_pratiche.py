from django.core.management.base import BaseCommand
from protocollo.models import Pratica


class Command(BaseCommand):
    help = 'Ricalcola mpoly_pratica per tutte le pratiche che hanno particelle associate'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra solo cosa verrebbe aggiornato, senza modifiche',
        )

    def handle(self, *args, **options):
        pratiche = Pratica.objects.filter(particella_pratica__isnull=False).distinct()
        totali = pratiche.count()
        self.stdout.write(f'Pratiche con particelle: {totali}')

        aggiornate = 0
        for idx, pratica in enumerate(pratiche.iterator(), start=1):
            if options['dry_run']:
                self.stdout.write(
                    f'  {idx}/{totali} AGGIORNA pratica id={pratica.id}'
                )
            else:
                try:
                    pratica.update_mpoly_pratica()
                    aggiornate += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'  {idx}/{totali} ERRORE pratica id={pratica.id}: {e}'
                        )
                    )

            if idx % 500 == 0 or idx == totali:
                self.stdout.write(f'  Elaborate {idx}/{totali}')

        if not options['dry-run']:
            self.stdout.write(
                self.style.SUCCESS(f'Pratiche aggiornate: {aggiornate}')
            )
