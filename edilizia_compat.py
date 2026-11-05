"""Supporto per le app opzionali dell'archivio storico.

Le app ``edilizia``, ``gest_edilizia`` e ``archivi`` non fanno parte del
repository pubblicato: sono strumenti interni per il recupero di dati
storici non normalizzati (vedi README).

Questo modulo espone gli stessi nomi usati dal resto del codice in due
modalita':

* **app installata** (ambiente interno, cartelle presenti): tutto viene
  reindirizzato alle implementazioni reali, con comportamento identico
  all'originale;
* **app assente** (replica pulita del repository): i modelli vengono
  sostituiti da oggetti vuoti che non interrogano mai il database, cosi'
  il progetto resta avviabile e le ricerche sull'archivio restituiscono
  zero risultati invece di generare errori.
"""
import re

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist


def app_installata(nome):
    """True se l'app ``nome`` e' presente in INSTALLED_APPS."""
    return any(
        voce == nome or voce.startswith(nome + '.')
        for voce in settings.INSTALLED_APPS
    )


EDILIZIA_AVAILABLE = app_installata('edilizia')
GEST_EDILIZIA_AVAILABLE = app_installata('gest_edilizia')
ARCHIVIO_AVAILABLE = app_installata('archivi')


if EDILIZIA_AVAILABLE:
    from edilizia.models import (  # noqa: F401
        Origine,
        ParticellaUnivoca,
        Pratica as EdiliziaPratica,
        PraticaParticella,
    )
    from edilizia.utils import extract_mappali, normalize_foglio  # noqa: F401
else:
    # ------------------------------------------------------------------
    # Sostituti vuoti: nessuna query, nessun accesso al database.
    # ------------------------------------------------------------------
    class _QuerySetVuota:
        """Queryset vuoto che ignora ogni filtro.

        Permette alle view di costruire le catene di filtri dell'archivio
        senza errori: le operazioni di trasformazione restituiscono se
        stesso, quelle di lettura (iterazione, conteggio, slice)
        restituiscono sempre un risultato vuoto.
        """

        def clone(self):
            return self

        def all(self):
            return self

        def none(self):
            return self

        def filter(self, *args, **kwargs):
            return self

        def exclude(self, *args, **kwargs):
            return self

        def distinct(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def values(self, *args, **kwargs):
            return self

        def values_list(self, *args, **kwargs):
            return self

        def only(self, *args, **kwargs):
            return self

        def defer(self, *args, **kwargs):
            return self

        def select_related(self, *args, **kwargs):
            return self

        def prefetch_related(self, *args, **kwargs):
            return self

        def annotate(self, *args, **kwargs):
            return self

        def union(self, *others):
            return self

        def exists(self):
            return False

        def count(self):
            return 0

        def first(self):
            return None

        def last(self):
            return None

        def __iter__(self):
            return iter(())

        def __len__(self):
            return 0

        def __bool__(self):
            return False

        def __getitem__(self, item):
            return self

        def __or__(self, other):
            return self

        def __and__(self, other):
            return self

        def __repr__(self):
            return '<QuerySetVuota>'

    class _ManagerVuoto:
        """Manager che restituisce sempre queryset vuote."""

        def get_queryset(self):
            return _QuerySetVuota()

        def all(self):
            return _QuerySetVuota()

        def none(self):
            return _QuerySetVuota()

        def filter(self, *args, **kwargs):
            return _QuerySetVuota()

        def exclude(self, *args, **kwargs):
            return _QuerySetVuota()

        def count(self):
            return 0

        def get(self, *args, **kwargs):
            raise self.model.DoesNotExist(
                "Archivio edilizia non disponibile in questa installazione."
            )

    class _ModelloAssente:
        """Sostituto di un modello dell'archivio edilizia.

        Espone la stessa interfaccia minima usata dal resto del codice
        (``objects``, ``DoesNotExist``): le query restituiscono sempre
        risultati vuoti senza toccare il database.
        """

        DoesNotExist = type(
            'DoesNotExist', (ObjectDoesNotExist,), {'__module__': __name__}
        )
        MultipleObjectsReturned = type(
            'MultipleObjectsReturned', (Exception,), {'__module__': __name__}
        )
        objects = _ManagerVuoto()
        _default_manager = objects

    _ManagerVuoto.model = _ModelloAssente

    class EdiliziaPratica(_ModelloAssente):
        """Sostituto di edilizia.Pratica."""

    class ParticellaUnivoca(_ModelloAssente):
        """Sostituto di edilizia.ParticellaUnivoca."""

    class Origine(_ModelloAssente):
        """Sostituto di edilizia.Origine."""

    class PraticaParticella(_ModelloAssente):
        """Sostituto di edilizia.PraticaParticella (tavola di incrocio)."""

    # Funzioni di parsing dei campi catastali: copie identiche a quelle
    # di edilizia/utils.py (codice puro, nessuna dipendenza dall'app).
    def normalize_foglio(fg):
        if not fg:
            return None
        fg = str(fg).strip()
        if not fg:
            return None
        # Allinea il foglio a 4 cifre (zero-padding) per combaciare
        # con catasto_particelle.foglio (es. '104' -> '0104').
        if fg.isdigit():
            fg = fg.zfill(4)
        return fg

    def extract_mappali(mapp):
        if not mapp:
            return []
        mapp = str(mapp).strip()
        if not mapp:
            return []

        main_part = re.split(r'[/]|sub\.', mapp, flags=re.IGNORECASE)[0]
        numbers = re.findall(r'\d+', main_part)
        if not numbers:
            return []
        return list(dict.fromkeys(numbers))
