import os
import sys
import django

# Configurazione dell'ambiente Django
# Assicurati che 'carrara.settings' sia il percorso corretto per il tuo progetto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carrara.settings')
django.setup()

from protocollo.models import Pratica

def run():
    """
    Sincronizza il campo 'mpoly_pratica' per tutti i record Pratica.
    La geometria viene generata unendo (Union) le geometrie 'mpoly' delle 
    particelle associate nel modulo protocollo.
    """
    print("Avvio della sincronizzazione delle geometrie per le Pratiche...")
    
    # Recuperiamo tutte le pratiche presenti
    pratiche = Pratica.objects.all()
    total_count = pratiche.count()

    if total_count == 0:
        print("Nessuna pratica trovata nel database.")
        return

    print(f"Trovate {total_count} pratiche da elaborare.")
    print("Ricalcolo in corso...")

    updated_count = 0
    error_count = 0

    # Iteriamo su ogni pratica per aggiornare la geometria unificata
    for i, pratica in enumerate(pratiche, 1):
        try:
            # Utilizziamo il metodo interno al modello che gestisce l'aggregazione Union
            # e la conversione corretta da Polygon a MultiPolygon
            pratica.update_mpoly_pratica()
            updated_count += 1
        except Exception as e:
            error_count += 1
            sys.stdout.write(f"\nErrore sulla Pratica ID {pratica.pk}: {e}\n")
        
        # Feedback sull'avanzamento
        if i % 10 == 0 or i == total_count:
            sys.stdout.write(f"\rProcessate: {i} / {total_count} ({(i / total_count * 100):.2f}%)")
            sys.stdout.flush()

    print("\n\n--- Riepilogo Aggiornamento Geometrie Pratiche ---")
    print(f"Pratiche elaborate: {total_count}")
    print(f"Aggiornate correttamente: {updated_count}")
    print(f"Errori riscontrati: {error_count}")

if __name__ == "__main__":
    run()