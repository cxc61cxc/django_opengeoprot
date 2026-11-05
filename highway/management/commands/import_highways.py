from django.core.management.base import BaseCommand

from highway.importer import import_highways, query_overpass


class Command(BaseCommand):
    help = "Importa o aggiorna le highway OpenStreetMap del comune di Carrara."

    def handle(self, *args, **options):
        self.stdout.write("Query Overpass in corso...")
        data = query_overpass()
        count = import_highways(data)
        self.stdout.write(
            self.style.SUCCESS(f"Importate o aggiornate {count} highway.")
        )
