import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carrara.settings')
django.setup()

from catasto.models import Particelle
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.db import transaction

def run():
    # Otteniamo il totale iniziale per il calcolo del progresso
    qs_da_aggiornare = Particelle.objects.filter(mpoly__isnull=True, geom__isnull=False)
    totale_iniziale = qs_da_aggiornare.count()

    if totale_iniziale == 0:
        print("Nessuna particella da aggiornare.")
        return

    print(f"Trovate {totale_iniziale} particelle da elaborare.")
    print("Elaborazione in corso (commit ogni 500 record)...")

    count = 0
    batch_size = 500

    # Usiamo un ciclo che recupera le particelle a blocchi finché ce ne sono da aggiornare
    while True:
        batch = Particelle.objects.filter(mpoly__isnull=True, geom__isnull=False)[:batch_size]
        if not batch:
            break

        with transaction.atomic():
            try:
                for p in batch:
                    # Trasformazione da HEXEWKT (3003) a GEOSGeometry
                    geom_obj = GEOSGeometry(p.geom, srid=3003)
                    # Trasformazione a 4326
                    geom_obj.transform(4326)
                    # Forza a MultiPolygon se è un Polygon semplice
                    p.mpoly = MultiPolygon(geom_obj) if geom_obj.geom_type == 'Polygon' else geom_obj
                    # Salva solo il campo mpoly
                    p.save(update_fields=['mpoly'])
                    count += 1
                    if count % 100 == 0:
                        sys.stdout.write(f"\rProcessate: {count} / {totale_iniziale} ({(count/totale_iniziale*100):.2f}%)")
                        sys.stdout.flush()
            except Exception as e:
                print(f"\nErrore critico durante il batch: {e}")
                # In caso di errore nel batch, usciamo o gestiamo il singolo record. 
                # Qui proseguiamo con il prossimo batch.
                break 

    print(f"\nAggiornamento completato: {count} particelle aggiornate correttamente.")

if __name__ == "__main__":
    run()
