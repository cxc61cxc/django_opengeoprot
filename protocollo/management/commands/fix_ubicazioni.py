import re
from django.core.management.base import BaseCommand
from protocollo.models import Pratica
from viario.models import Civici


def parse_ubicazione(value):
    if not value:
        return None, None
    value = str(value).strip()
    if not value:
        return None, None

    if ',' in value:
        parts = value.split(',', 1)
        via = parts[0].strip()
        civico = parts[1].strip()
        return via, civico[:50]

    m = re.search(r'(?:n\.?\s*)(\S+)\s*$', value, re.IGNORECASE)
    if m:
        civico = m.group(1)[:50]
        via = value[:m.start()].strip()
        return via, civico

    tokens = value.rsplit(' ', 1)
    if len(tokens) == 2 and len(tokens[1]) <= 5:
        return tokens[0].strip(), tokens[1].strip()[:50]

    return None, None


class Command(BaseCommand):
    help = 'Aggiorna street e housenumber delle Pratiche da annotazioni/ubicazione'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        pratiche = Pratica.objects.exclude(annotazioni__isnull=True).exclude(annotazioni__exact='')
        totali = pratiche.count()
        self.stdout.write(f'Pratiche con annotazioni: {totali}')
        count = 0
        aggiornati = 0
        for p in pratiche:
            via, civico = parse_ubicazione(p.annotazioni)
            street_obj = None
            if via:
                street_obj = Civici.objects.filter(street__iexact=via).first()
                if not street_obj:
                    street_obj = Civici.objects.filter(street__icontains=via).first()

            if options['dry_run']:
                self.stdout.write(f'{p.id}: via={via!r}, civico={civico!r}, street={street_obj}')
            else:
                if street_obj and p.street_id != street_obj.id:
                    p.street = street_obj
                if civico and p.housenumber != civico:
                    p.housenumber = civico
                if street_obj or civico:
                    p.save(update_fields=['street', 'housenumber', 'data_mod'])
                    aggiornati += 1
            count += 1
            if count % 500 == 0 or count == totali:
                self.stdout.write(f'  {count}/{totali}')

        if not options['dry-run']:
            self.stdout.write(self.style.SUCCESS(f'Aggiornate {aggiornati} pratiche'))
