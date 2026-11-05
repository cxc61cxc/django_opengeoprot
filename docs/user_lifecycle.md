# Ciclo di vita dell'utente: registrazione, operazioni e clean‑up

Questo documento descrive il ciclo di vita di un utente nel sistema
OpenGeoProt, daLLA registrazione all'eliminazione, con particolare
attenzione ai comportamenti dei campi FK rispetto alla cancellazione.

---

## 1. Registrazione di un nuovo utente

### 1.1 Punto di ingresso

- **URL:** `/accounts/signup/`
- **View:** `accounts.views.signup` (`accounts/views.py:67`)
- **Form:** `SignUpForm` (`accounts/forms.py:169`), estende `UserCreationForm`

L'utente fornisce:
- Username
- Nome e cognome
- Email (deve essere `@comune.carrara.ms.it`)
- **Settore** (obbligatorio se non è consigliere)
- **Servizio** e **U.O.** (facoltativi, dipendono dal settore)
- Eventuale spunta **"Consigliere di una commissione"** con selezione di
  una o più commissioni

### 1.2 Assegnazione dei gruppi

Il form salva l'utente, lo logga in e assegna i gruppi in base al ruolo:

| Ruolo | Gruppi assegnati | Note |
|---|---|---|
| **User (settore)** | `user_<settore>`, `readonly` | Clona i permessi da `user_settore_6` |
| **Consigliere** | `consiglieri` + gruppo del TipoCommissione | Nessun settore sul Profile; accesso read‑only |

- `sync_user_group_by_settore()` (`accounts/forms.py:74`): assegna
  `user_<settore>` o `user_settore_<N>` + `readonly`
- `_assegna_gruppo_consigliere()` (`accounts/forms.py:132`): assegna il
  gruppo della commissione + `consiglieri`
- `Profile` (`accounts/models.py:22`): creato con `settore`/`u_o` vuoti
  per i consiglieri, oppure popolato con gli snapshot StoricoSettore/
  StoricoAttivitaUO per gli user

### 1.3 Redirect post‑registrazione

- **Destinazione:** `protocollo:search_protocollo_url`
  (`protocollo/urls.py:63`)
- **Motivo:** accessibile a tutti gli utenti autenticati, evita loop di
  redirect per utenti senza accesso alla home page
  (decisione registrata in `project.md → signup_redirect_to_search_protocollo`)

---

## 2. Operazioni disponibili al nuovo utente

### 2.1 Accesso comune (tutti gli utenti autenticati)

| Operazione | URL | Note |
|---|---|---|
| Ricerca pratiche | `/protocollo/search/protocollo/` (`SearchProt`) | Punto di ingresso principale |
| Visualizza dettaglio pratica | `/protocollo/pratica/<id>/` | Dipende dal settore/permessi |
| Visualizza profilo | `/accounts/profile/` (`profile_view`) | Read‑only per i consiglieri |
| Cambio password | `/accounts/password_change/` | |

### 2.2 User settore (gruppi `user_settore_N` / `editor_settore_N`)

| Operazione | Permessi richiesti | Note |
|---|---|---|
| Aggiungi pratica | `editor_required` | Gruppi `editor_settore_N` |
| Modifica pratica | `editor_required` | |
| Aggiungi documento | `editor_required` | |
| Richiedi accesso pratica | Tutti gli utenti autenticati | Per accedere a pratiche di altri settori |
| Visualizza archivi | `archivio_edilizia_required` | Gruppi `archivio_settore_6`, `user_settore_6`, `editor_settore_*` |

I gruppi `user_settore_*` hanno **64 permessi** (accesso in sola
lettura + funzioni base); i gruppi `editor_settore_*` hanno **41
permessi** (scrittura limitata alle proprie pratiche).

### 2.3 Consiglieri (gruppo `consiglieri`)

| Operazione | Note |
|---|---|
| Visualizza le sue commissioni | `/accounts/consiglieri/` |
| Visualizza solo le pratiche delle sue commissioni | Filtrato server‑side per settore |
| **Nessun accesso** a soggetti / particelle | (vincolo registrato in `project.md`) |

---

## 3. Relazione FK con il modello User — comportamento alla cancellazione

### 3.1 Stato attuale (dopo le modifiche)

Le FK verso `User` sono state normalizzate con il pattern **snapshot name**:
il record non viene mai cancellato ( `SET_NULL` ) e il nome dell'utente
viene **perso nella tabella** in un campo `CharField` separato, in modo
che rimanga visibile anche dopo la cancellazione dell'account.

| Modello | FK verso User | on_delete | Campo snapshot | Property display |
|---|---|---|---|---|
| `Pratica` (`protocollo`) | `user` | `SET_NULL` | `user_name` | `user_display` |
| `Documento` (`protocollo`) | `username` | `SET_NULL` | `username_name` | `user_display` |
| `Commissione` (`accounts`) | `user` | `SET_NULL` (era `CASCADE`) | `user_name` | `user_display` |
| `TipoPratica` (`protocollo`) | `user` | `SET_NULL` | — | `str(self.user)` (FK puo' diventare NULL) |
| `Soggetto` (`protocollo`) | `user` | `SET_NULL` | — | come sopra |
| `Anaprat` (`protocollo`) | `user` | `SET_NULL` | — | come sopra |
| `Diario` (`protocollo`) | `user` | `SET_NULL` | — | come sopra |
| `TipoSoggetto` (`protocollo`) | `user` | `SET_NULL` | — | come sopra |
| `SostituzioneSoggetto` (`protocollo`) | `user` | `SET_NULL` | — | come sopra |
| `Cataprat` (`protocollo`) | `user` | `SET_NULL` | — | come sopra |
| `ImpFot` (`fotovoltaico`) | `user` | `SET_NULL` | — | come sopra |
| `Istruttoria` (`idonall`) | `user` | `SET_NULL` | — | come sopra |
| `Idonall` (`idonall`) | `user` | `SET_NULL` | — | come sopra |
| `Commissione` (`paesaggio`) | `user` | `SET_NULL` | — | come sopra |
| `Istruttoria` (`istruttoria_poc`) | `user` | `SET_NULL` | — | come sopra |

> `Profile.user` è un `OneToOneField` con `CASCADE`: il profilo viene
> cancellato insieme all'utente (comportamento corretto, è solo
> metadata collegato all'account).

### 3.2 Pattern "snapshot name" (implementato)

Il pattern consiste in tre elementi:

1. **Campo snapshot** (`user_name` / `username_name`): `CharField(max_length=255)`,
   popolato con `str(user)` al momento della creazione.
2. **Metodo `save()` override**: se il FK `user` è impostato e il campo
   snapshot è vuoto, lo popola.
   ```python
   def save(self, *args, **kwargs):
       if self.user and not self.user_name:
           self.user_name = str(self.user)
       super().save(*args, **kwargs)
   ```
3. **Property `user_display`**: restituisce sempre un nome leggibile,
   usando il FK se disponibile, altrimenti il campo snapshot, altrimenti
   `"sconosciuto"`.
   ```python
   @property
   def user_display(self):
       if self.user_id:
           return str(self.user) if self.user else self.user_name or "sconosciuto"
       return self.user_name or "sconosciuto"
   ```

### 3.3 Cosa succede alla cancellazione dell'utente

| Scenario | Comportamento |
|---|---|
| **L'utente ha creato pratiche** | Le pratiche **non vengono cancellate** ( `SET_NULL` ); il nome rimane visibile tramite `user_display` grazie al campo snapshot `user_name` |
| **L'utente ha caricato documenti** | I documenti **non vengono cancellati**; il nome rimane visibile tramite `user_display` su `Documento` |
| **L'utente è un consigliere con iscrizioni** | Le iscrizioni `Commissione` **non vengono cancellate** (prima `CASCADE`, ora `SET_NULL`); il nome del consigliere rimane visibile tramite `user_display` |
| **L'utente ha un Profile** | Il `Profile` viene cancellato con l'utente ( OneToOneField `CASCADE` ); le sue scelte di settore/uo sulle pratiche esistenti non sono colpite |
| **Migration di backfill** | Le migration `protocollo.0038` e `accounts.0016` includono un `RunPython` che backfilla in automatico il campo `user_name` per tutti i record esistenti con un utente associato |

### 3.4 Template — visualizzazione del nome utente

I template che mostrano il creatore della pratica usano ora `user_display`
invece di `user` direttamente:

| Template | Prima | Dopo |
|---|---|---|
| `protocollo/pratica_detail.html:64` | `{{ pratica.user }}` | `{{ pratica.user_display }}` |
| `protocollo/pratica_detail_last.html:50` | `{{ pratica.user }}` | `{{ pratica.user_display }}` |
| `protocollo/pratica_detail copy.html:53` | `{{ pratica.user }}` | `{{ pratica.user_display }}` |
| `protocollo/pratica_detail_ex.html:43` | `{{ pratica.user }}` | `{{ pratica.user_display }}` |
| `istruttoria_poc/istruttoria_detail.html:24` | `{{ pratica.user\|default:"sconosciuto" }}` | `{{ pratica.user_display }}` |

---

## 4. Migration — stato

| App | Migration | Operazioni |
|---|---|---|
| `protocollo` | `0038_documento_username_name_and_more` | Aggiunge `user_name` a `Pratica`/`HistoricalPratica`, `username_name` a `Documento`, backfill `RunPython` |
| `accounts` | `0016_commissione_user_name_alter_commissione_user` | Aggiunge `user_name` a `Commissione`, cambia FK `user` da `CASCADE` a `SET_NULL`, backfill `RunPython` |

Entrambe le migration sono incluse e applicate (verificabile con
`python manage.py showmigrations protocollo accounts`).

---

## 5. Best practice per la gestione utenti

- **Non cancellare mai** un utente che ha creato pratiche o documenti:
  con `SET_NULL` il record persiste, ma in ogni caso il nome è
  preservato dal campo snapshot.
- **Preferire la disattivazione** (`is_active=False`) alla cancellazione
  quando possibile: mantiene l'account intatto e il nome rimane sempre
  disponibile.
- **I nuovi record** popolano automaticamente il campo `user_name` tramite
  il metodo `save()` override; i record esistenti sono stati backfillati
  dalle migration.
