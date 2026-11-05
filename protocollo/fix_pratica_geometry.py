import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carrara.settings')
django.setup()

from protocollo.models import Pratica

def run():
    qs = Pratica.objects.filter(mpoly_pratica__isnull=True).order_by('id')
    totale = qs.count()
    if totale == 0:
        print("Nessuna pratica da aggiornare.")
        return

    print(f"Trovate {totale} pratiche con mpoly_pratica nullo.")

    updated = 0
    errors = 0
    for i, pratica in enumerate(qs.iterator(chunk_size=1000), 1):
        try:
            pratica.update_mpoly_pratica()
            updated += 1
        except Exception as e:
            errors += 1
            sys.stdout.write(f"\nErrore su Pratica ID {pratica.pk}: {e}\n")
        if i % 100 == 0 or i == totale:
            sys.stdout.write(f"\rProcessate: {i} / {totale} - aggiornate: {updated} - errori: {errors}")
            sys.stdout.flush()

    sys.stdout.write(f"\rProcessate: {totale} / {totale} - aggiornate: {updated} - errori: {errors}")
    sys.stdout.flush()
    print(f"\nCompletato. Aggiornate: {updated}, errori: {errors}, totale: {totale}")

if __name__ == '__main__':
    run()
