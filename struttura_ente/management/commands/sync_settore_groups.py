from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from struttura_ente.models import Settore
from struttura_ente.signals import _crea_gruppi_per_settore


class Command(BaseCommand):
    help = 'Crea/aggiorna i gruppi user_settore_N e editor_settore_N per tutti i Settori presenti.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sovrascrive i permessi dei gruppi esistenti con quelli del template.',
        )

    def handle(self, *args, **options):
        force = options['force']
        for s in Settore.objects.all().order_by('codice'):
            res = _crea_gruppi_per_settore(s.codice, force=force)
            if res is None:
                self.stdout.write(self.style.WARNING(f'  {s.codice}: saltato (non è un settore numerico o è il 6)'))
            else:
                ug, eg = res
                self.stdout.write(self.style.SUCCESS(
                    f'  {s.codice}: user={ug.name} (perms={ug.permissions.count()}), '
                    f'editor={eg.name} (perms={eg.permissions.count()})'
                ))

        existing = Group.objects.filter(name__regex=r'^(user|editor)_settore_\d+$').order_by('name')
        self.stdout.write(self.style.SUCCESS(f'\nGruppi totali: {existing.count()}'))
        for g in existing:
            self.stdout.write(f'  {g.name} - perms={g.permissions.count()}')