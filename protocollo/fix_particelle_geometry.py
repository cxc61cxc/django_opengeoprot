import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carrara.settings')
django.setup()

from protocollo.models import Particella as ProtParticella
from catasto.models import Particelle as CatastoParticelle
from django.db import transaction
from django.contrib.gis.geos import MultiPolygon

def run():
    qs = ProtParticella.objects.filter(mpoly__isnull=True).order_by('id').only('id', 'foglio', 'mappale')
    totale = qs.count()
    if totale == 0:
        print("Nessuna particella protocollo da aggiornare.")
        return

    print(f"Trovate {totale} particelle protocollo con mpoly nullo.")

    batch_size = 1000
    processed = 0
    updated = 0
    skipped = 0
    batch = []

    for p in qs.iterator(chunk_size=batch_size):
        fg = str(p.foglio).zfill(4) if p.foglio else None
        mp = p.mappale
        if not fg or not mp:
            skipped += 1
            processed += 1
            continue
        batch.append((p.id, fg, mp))
        processed += 1

        if len(batch) >= batch_size:
            ups, sk = process_batch(batch)
            updated += ups
            skipped += sk
            batch = []
            sys.stdout.write(f"\rProcessate: {processed} / {totale} - aggiornate: {updated} - saltate: {skipped}")
            sys.stdout.flush()

    if batch:
        ups, sk = process_batch(batch)
        updated += ups
        skipped += sk

    sys.stdout.write(f"\rProcessate: {processed} / {totale} - aggiornate: {updated} - saltate: {skipped}")
    sys.stdout.flush()
    print(f"\nCompletato. Aggiornate: {updated}, saltate: {skipped}, totale: {totale}")


def process_batch(batch):
    fogli_set = {fg for _, fg, _ in batch}
    mappali_set = {mp for _, _, mp in batch}

    catasto_map = {}
    for cp in CatastoParticelle.objects.filter(foglio__in=fogli_set, mappale__in=mappali_set, mpoly__isnull=False).only('foglio', 'mappale', 'mpoly'):
        catasto_map[(cp.foglio, cp.mappale)] = cp.mpoly

    to_update = []
    skipped = 0
    for pid, fg, mp in batch:
        geom = catasto_map.get((fg, mp))
        if geom is not None:
            if geom.geom_type == 'Polygon':
                geom = MultiPolygon(geom)
            to_update.append((pid, geom))
        else:
            skipped += 1

    if to_update:
        with transaction.atomic():
            for pid, geom in to_update:
                ProtParticella.objects.filter(id=pid).update(mpoly=geom)

    return len(to_update), skipped


if __name__ == '__main__':
    run()
