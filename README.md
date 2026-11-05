# OpenGeoProt

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

Applicazione web per la gestione integrata dei procedimenti amministrativi di un
ente comunale: protocollo generale, edilizia, catasto, anagrafe, viario e
moduli specializzati, con visualizzazione cartografica (PostGIS + Leaflet).

Pensata per il **Comune di Carrara**, ma replicabile su qualsiasi ente
configurando database, settori e struttura dell'ente.

---

## Funzionalità

### Moduli principali

| Modulo | Descrizione |
|---|---|
| **protocollo** | Cuore del sistema: tipi di pratica, pratiche, soggetti, particelle, documenti allegati, diario di pratica, ricerca avanzata, mappa delle pratiche, dashboard e report (riepiloghi CDU, accessi, grafici), storico modifiche con `django-simple-history`, indicizzazione documenti |
| **edilizia** / **gest_edilizia** | *App interne, non pubblicate nel repository* (vedi "App opzionali"): pratiche edilizie storiche, istruttorie, cartelline PDF, collegamento alle particelle catastali, planimetrie |
| **archivi** | *App interna, non pubblicata*: archivio storico delle pratiche con origine e dati anagrafici |
| **catasto** | Particelle catastali (foglio/mappale) su database dedicato con router dedicato (`catasto.db_router`) e geometrie PostGIS |
| **anagrafe** | Residenti / anagrafe civica su database dedicato (`AnagrafeCivica`) |
| **viario** | Civici e strade, con sincronizzazione da OpenStreetMap |
| **prg** | Piano regolatore: piani, destinazioni d'uso, istruttorie, marche |
| **paesaggio** | Commissioni paesaggistiche: composizione, iscritti, pareri |
| **coop** | Convenzioni edilizie cooperative: istruttorie convenzionali, scadenze, rateizzazioni, svincoli, accettazioni importi, millesimi |
| **ascensori** | Impianti e matricole ascensori, ordinanze, pratiche collegate |
| **suap** | PAU – Provvedimento Unico Autorizzativo (SUAP) |
| **pascar** | Passi carrabili |
| **idonall** | Idoneità: attestazioni, rinnovi, duplicati, cointestazioni |
| **fotovoltaico** | Impianti fotovoltaici |
| **grandi_lavori** / **piccoli_lavori** / **licenze_edilizie** / **autorizzazioni** | Registri con elenchi per periodo, allegati e operazioni PDF |
| **comunicazioni** | Modelli di comunicazione/lettere collegati ai tipi di pratica |
| **istruttoria_poc** | Istruttorie POC |
| **omissis_documents** | Oscuramento automatico "omissis" di documenti Office tramite LibreOffice |
| **osm_note** / **highway** | Note e geometrie stradali da OpenStreetMap |
| **qwen_map** | Mappa amministrativa (confini) con import da file |
| **mailer** | Invio email (SMTP) |
| **struttura_ente** | Settori/struttura dell'ente, sincronizzazione gruppi (`sync_settore_groups`) |
| **accounts** | Utenti, profili (settore, u.o.), gruppi e permessi, commissioni, richieste di accesso, gestione utenti, report accessi |
| **home** | Pagina iniziale, help/ manuale utente, riepiloghi |

### Aspetti trasversali

- **Cartografia**: PostGIS, `django.contrib.gis`, Leaflet, GeoJSON, widget mappa
  per particelle e pratiche.
- **Permessi granulari**: gruppi per settore (`editor_settore_*`, `user_settore_*`,
  `archivio_settore_*`), flag read-only per contesto, viste dedicate ai
  consiglieri/commissioni.
- **Storico modifiche**: `django-simple-history` su pratiche, documenti,
  diario, convenzioni, scadenze, ecc.
- **Auditing**: log azioni utente (`user_actions.log`) via middleware dedicato.
- **Sessioni**: scadenza alla chiusura del browser, timeout di sessione.
- **Documenti**: upload in `media/`, generazione PDF (reportlab/xhtml2pdf),
  conversione documenti (LibreOffice), ricerca full-text sui documenti.
- **Interfaccia**: Bootstrap 4, django-crispy-forms, django-autocomplete-light,
  django-select2, datepicker, tabelle filtrabili.

---

## Stack tecnologico

- **Python** 3.11 (consigliato; testato anche su 3.10)
- **Django** 4.1.x
- **PostgreSQL** ≥ 13 con estensione **PostGIS** (obbligatoria: GeoDjango)
- **GDAL/GEOS/PROJ** librerie di sistema (richieste da `django.contrib.gis`)
- **Redis** (opzionale, usato da django-select2/django-redis se configurato)
- **LibreOffice** (opzionale, per `omissis_documents`)
- Server: **gunicorn** + nginx (config di esempio: `gunicorn_config.py`,
  script in `deploy_utilities/`)

---

## Requisiti di sistema

```bash
# Debian/Ubuntu
sudo apt install python3.11 python3.11-venv python3-pip \
    postgresql postgresql-contrib postgis postgresql-15-postgis-3 \
    gdal-bin libgdal-dev libgeos-dev libproj-dev \
    libreoffice   # opzionale, per omissis
```

Verifica GDAL:

```bash
gdal-config --version   # deve rispondere (es. 3.6.x)
```

---

## Istruzioni per replicare il progetto

### 1. Clone e ambiente virtuale

```bash
git clone https://github.com/cxc61cxc/django_opengeoprot.git
cd django_opengeoprot

python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Database PostgreSQL/PostGIS

Creare utente e i due database (default + anagrafe):

```bash
sudo -u postgres psql
```

```sql
CREATE USER opengeo WITH PASSWORD 'scegli-una-password';
CREATE DATABASE carrara_prot_locale OWNER opengeo;
CREATE DATABASE AnagrafeCivica OWNER opengeo;
\c carrara_prot_locale
CREATE EXTENSION IF NOT EXISTS postgis;
\c AnagrafeCivica
CREATE EXTENSION IF NOT EXISTS postgis;
-- vista catasto usata dall'app (se non esiste gia'):
-- CREATE SCHEMA IF NOT EXISTS cxf_in;
-- CREATE VIEW cxf_in.vw_particelle AS ... (vedi nota sotto)
\q
```

> **Nota sul database anagrafe**: l'app `catasto` legge le particelle dalla
> vista `cxf_in.vw_particelle` del database `AnagrafeCivica` (instradate dal
> `DATABASE_ROUTERS`). Se la vista non esiste, creare una vista equivalente o
> adattare `catasto/db_router.py` e i modelli ai propri dati.

### 3. Configurazione

```bash
cp .env.example .env
cp carrara/settings.example.py carrara/settings.py
```

Poi compilare `.env`:

```ini
DJANGO_SECRET_KEY=<genera-un-secret-key>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_DB_NAME=carrara_prot_locale
DJANGO_DB_USER=opengeo
DJANGO_DB_PASSWORD=<password-db>
DJANGO_DB_HOST=localhost
DJANGO_DB_PORT=5432
DJANGO_ANAGRAFE_DB_NAME=AnagrafeCivica
DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Generare la secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> `carrara/settings.py` e `.env` **non vengono versionati** (vedi `.gitignore`).
> `carrara/settings.example.py` è la versione sanificata da cui partire.

### 4. Migrazioni e utente admin

```bash
python manage.py migrate
python manage.py createsuperuser
```

> Le app `catasto` (modello `Particelle`) e `anagrafe` migrano sui database
> rispettivi grazie al router: eseguire `migrate` una volta sola.

### 5. Dati iniziali (opzionale)

Per popolare i dati di base:

- **Residenti** (`anagrafe.Residenti`): inserire i dati dall'ufficio anagrafe.
- **Particelle** (`catasto.Particelle`): da SISTER — in alternativa i progetti
  [opencatamap](https://github.com/marcobra/opencatamap) o
  [opencatamap-php](https://github.com/cxc61cxc/opencatamap-php).
- **Civici/strade** (`viario.Civici`): da OpenStreetMap.
- **Gruppi/permessi**:

  ```bash
  python manage.py sync_settore_groups
  ```

- **Popolamenti di esempio**:

  ```bash
  python manage.py populate_grandi_lavori
  python manage.py populate_piccoli_lavori
  python manage.py populate_licenze_edilizie
  python manage.py populate_autorizzazioni
  python manage.py import_highways
  ```

Tramite vista PGSQL è possibile georeferenziare le pratiche in ambiente GIS.

### 6. Avvio in sviluppo

```bash
python manage.py runserver
```

Aprire `http://127.0.0.1:8000/` e accedere con l'utente creato.

### 7. Static files e produzione

```bash
python manage.py collectstatic --noinput
```

Esempio con gunicorn (vedi `gunicorn_config.py`):

```bash
gunicorn carrara.wsgi:application -c gunicorn_config.py
```

In produzione: nginx che serve `/static/` da `STATIC_ROOT`
(`/var/www/django_opengeoprot/staticfiles/`) e `/media/` da `media/`,
con `DJANGO_DEBUG=False` e `DJANGO_ALLOWED_HOSTS` valorizzato.
Script di deploy di esempio in `deploy_utilities/`.

---

### App opzionali non pubblicate (archivio storico)

Tre app interne **non fanno parte di questo repository**: servono solo al
recupero di dati storici non normalizzati e contengono archivi
documentali pesanti:

- `edilizia/` — archivio storico delle pratiche edilizie;
- `gest_edilizia/` — interfacce di gestione dell'archivio edilizia;
- `archivi/` — archivio storico generico.

Il progetto le tratta come **opzionali**, quindi la replica funziona
completa anche senza di esse:

- `carrara/settings.example.py` le inserisce in `INSTALLED_APPS` e nel
  `MIDDLEWARE` **solo se le cartelle esistono** nell'installazione;
- `carrara/urls.py` registra le rotte solo per le app installate;
- `edilizia_compat.py` espone gli stessi nomi usati dal codice
  (modelli, funzioni di parsing dei campi catastali) e, se l'app manca,
  fornisce sostituti vuoti che non interrogano il database: le ricerche
  nell'archivio restituiscono zero risultati, la navbar nasconde il
  pulsante "Archivio" e nessuna pagina va in errore.

Per riavere le app in locale basta ripristinare le cartelle: restano nel
`.gitignore` e vengono rilevate automaticamente al successivo avvio.

---

## Struttura del progetto

```
django_opengeoprot/
├── carrara/            # progetto Django (settings, urls, wsgi)
├── accounts/           # utenti, profili, permessi, commissioni
├── protocollo/         # protocollo e pratiche (modulo centrale)
├── edilizia_compat.py  # supporto per le app opzionali dell'archivio storico
├── catasto/            # particelle catastali (DB anagrafe, router)
├── anagrafe/           # residenti (DB dedicato)
├── viario/             # civici e strade (OSM)
├── prg/                # piano regolatore
├── paesaggio/          # commissioni paesaggistiche
├── coop/               # convenzioni cooperative
├── ascensori/          # impianti ascensori
├── suap/ pascar/ idonall/ fotovoltaico/
├── istruttoria_poc/ omissis_documents/
├── grandi_lavori/ piccoli_lavori/ licenze_edilizie/ autorizzazioni/
├── comunicazioni/ mailer/ struttura_ente/ istat/
├── osm_note/ highway/ qwen_map/
├── home/               # homepage e help
├── templates/          # template globali (base, navbar)
├── static/             # CSS/JS/immagini (in sorgente)
├── docs/               # documentazione
├── deploy_utilities/   # script di deploy
├── utility_scripts/    # script di servizio
├── manage.py
├── requirements.txt
├── .env.example
└── carrara/settings.example.py
```

> `media/` (documenti caricati), `staticfiles/` (collectstatic), database e
> log non sono versionati.

---

## Comandi di management utili

| Comando | Descrizione |
|---|---|
| `sync_settore_groups` | Crea/aggiorna i gruppi di permessi per settore |
| `import_particelle` / `renumber_particelle_id` | Import/rinumerazione particelle |
| `importa_dati_php` / `importa_da_db_php` / `importa_documenti` | Migrazione dati da vecchio sistema PHP |
| `indicizza_documenti` | Indice di ricerca documenti |
| `aggiorna_mpoly_pratiche` / `carica_geometrie_particelle` | Aggiornamento geometrie |
| `collega_documenti` / `fix_ubicazioni` / `show_ubicazioni` | Risanamenti dati |
| `import_highways` / `import_carrara` | Import dati OSM/geometrie |
| `populate_*` | Popolamento registri di esempio |

---

## Variabili d'ambiente

Tutte le variabili sono elencate in `.env.example`. Le più importanti:

| Variabile | Descrizione |
|---|---|
| `DJANGO_SECRET_KEY` | Obbligatoria. Chiave segreta Django |
| `DJANGO_DEBUG` | `True` in sviluppo, `False` in produzione |
| `DJANGO_ALLOWED_HOSTS` | Host consentiti, separati da virgola |
| `DJANGO_DB_*` | Connessione al database principale |
| `DJANGO_ANAGRAFE_DB_NAME` | Database anagrafe/catasto |
| `DJANGO_EMAIL_*` | Configurazione SMTP (o console backend in sviluppo |

---

## Licenza

Questo progetto è rilasciato sotto **[CC BY-NC-SA 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/)**
(testo integrale nel file [`LICENSE`](LICENSE)):

- **Attribuzione (BY)** — ogni copia e ogni fork devono citare l'autore:
  **cxc61cxc — https://github.com/cxc61cxc**.
- **NonCommercial (NC)** — è **vietato l'uso commerciale**: nessuna vendita,
  nessuna erogazione a fini di lucro, nessun riutilizzo in prodotti o servizi
  a pagamento.
- **ShareAlike (SA)** — chi modifica e **distribuisce** il codice derivato deve
  pubblicarlo sotto la **stessa licenza** (CC BY-NC-SA 4.0), mantenendo
  attribuzione e avvertenze.

> **Nota sul tipo di licenza:** essendo una licenza con clausola
> NonCommercial, non è approvata dalla OSI: tecnicamente il progetto è
> *source-available* con obblighi di condivisione, non "open source" secondo
> la definizione stretta. Lo ShareAlike scatta alla **distribuzione** del
> codice (una modifica usata internamente o resa disponibile solo come servizio
> senza diffondere i sorgenti non attiva l'obbligo di pubblicazione).

### Componenti di terze parti

Bootstrap, jQuery, Leaflet, Django e le altre librerie incluse in `static/`
restano sotto le rispettive licenze originali (MIT/GPL/Apache ecc.): la
licenza del progetto si applica al codice sorgente di OpenGeoProt.
