"""Esportazione e importazione CSV dei dati iniziali da caricare al primo avvio.

Sono previsti due file, entrambi con:

* separatore di campo ``;``
* encoding UTF-8 con BOM (apribile direttamente con Excel)
* valori multivalore separati da ``|``

``tipo_pratica.csv``
    Colonne: ``id_orig, name, description, settore, servizio, u_o,
    visibile_solo_uo, uo_visibili, user``.

    ``settore`` e' il codice del Settore, ``servizio`` il codice dello
    StoricoServizio, ``u_o`` il nome dello StoricoAttivitaUO e ``user`` lo
    username: sono chiavi naturali, all'importazione vengono solo risolte.
    Se il riferimento non esiste ancora sul DB nuovo il campo resta vuoto
    e viene emesso un avviso (nulla viene creato al posto suo).

``gruppi.csv``
    Colonne: ``name, permessi``. I permessi sono in formato
    ``app_label.codename`` separati da ``|`` e vengono risolti sui content
    type generati dalle migration.
"""
import csv
import os

ENCODING = 'utf-8-sig'
DELIMITER = ';'
SEP_MULTIVALORE = '|'

FILE_TIPO_PRATICA = 'tipo_pratica.csv'
FILE_GRUPPI = 'gruppi.csv'

COLONNE_TIPO_PRATICA = [
    'id_orig',
    'name',
    'description',
    'settore',
    'servizio',
    'u_o',
    'visibile_solo_uo',
    'uo_visibili',
    'user',
]
COLONNE_GRUPPI = ['name', 'permessi']


# ---------------------------------------------------------------------------
# utility
# ---------------------------------------------------------------------------

def _report():
    """Contatore dei risultati di un caricamento."""
    return {'creati': 0, 'presenti': 0, 'aggiornati': 0, 'avvisi': []}


def _crea_cartella(percorso):
    cartella = os.path.dirname(os.path.abspath(percorso))
    os.makedirs(cartella, exist_ok=True)


def _leggi(percorso):
    """Legge un CSV e ritorna la lista delle righe (dizionari)."""
    with open(percorso, 'r', newline='', encoding=ENCODING) as f:
        reader = csv.DictReader(f, delimiter=DELIMITER)
        return [dict(riga) for riga in reader]


def _valore(riga, chiave):
    return (riga.get(chiave) or '').strip()


def _multi(valore):
    """Divide un campo multivalore (separato da ``|``)."""
    return [v.strip() for v in (valore or '').split(SEP_MULTIVALORE) if v.strip()]


def _booleano(valore):
    return (valore or '').strip().lower() in ('1', 'true', 'yes', 'si', 'sì')


def _intero(valore):
    try:
        return int((valore or '').strip())
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

def esporta_tipo_pratica(percorso):
    """Scrive i tipi di pratica nel CSV. Ritorna il numero di righe scritte."""
    from protocollo.models import TipoPratica

    _crea_cartella(percorso)
    qs = (
        TipoPratica.objects
        .select_related('user', 'settore', 'servizio', 'u_o')
        .prefetch_related('uo_visibili')
        .order_by('name')
    )
    righe = 0
    with open(percorso, 'w', newline='', encoding=ENCODING) as f:
        writer = csv.DictWriter(f, fieldnames=COLONNE_TIPO_PRATICA, delimiter=DELIMITER)
        writer.writeheader()
        for tp in qs:
            writer.writerow({
                'id_orig': tp.id,
                'name': tp.name,
                'description': tp.description or '',
                'settore': tp.settore.codice if tp.settore_id else '',
                'servizio': tp.servizio.codice if tp.servizio_id else '',
                'u_o': tp.u_o.nome if tp.u_o_id else '',
                'visibile_solo_uo': '1' if tp.visibile_solo_uo else '0',
                'uo_visibili': SEP_MULTIVALORE.join(
                    uo.nome for uo in tp.uo_visibili.all()
                ),
                'user': tp.user.username if tp.user_id else '',
            })
            righe += 1
    return righe


def esporta_gruppi(percorso):
    """Scrive i gruppi con i relativi permessi. Ritorna il numero di righe."""
    from django.contrib.auth.models import Group

    _crea_cartella(percorso)
    qs = Group.objects.prefetch_related('permissions__content_type').order_by('name')
    righe = 0
    with open(percorso, 'w', newline='', encoding=ENCODING) as f:
        writer = csv.DictWriter(f, fieldnames=COLONNE_GRUPPI, delimiter=DELIMITER)
        writer.writeheader()
        for gruppo in qs:
            permessi = sorted(
                f'{p.content_type.app_label}.{p.codename}'
                for p in gruppo.permissions.all()
            )
            writer.writerow({
                'name': gruppo.name,
                'permessi': SEP_MULTIVALORE.join(permessi),
            })
            righe += 1
    return righe


# ---------------------------------------------------------------------------
# import - gruppi
# ---------------------------------------------------------------------------

def carica_gruppi(percorso, force=False, dry_run=False):
    """Crea/aggiorna i gruppi (e i loro permessi) dal CSV.

    Un gruppo gia' presente con permessi diversi viene lasciato invariato e
    segnalato, a meno che non sia impostato ``force``.
    """
    from django.contrib.auth.models import Group, Permission
    from django.db import transaction

    report = _report()
    for riga in _leggi(percorso):
        nome = _valore(riga, 'name')
        if not nome:
            report['avvisi'].append('riga senza "name" saltata')
            continue

        permessi = []
        for codice in _multi(_valore(riga, 'permessi')):
            if '.' not in codice:
                report['avvisi'].append(
                    f'{nome}: permesso "{codice}" non valido (atteso app_label.codename)'
                )
                continue
            app_label, codename = codice.split('.', 1)
            permesso = Permission.objects.filter(
                content_type__app_label=app_label, codename=codename
            ).first()
            if permesso is None:
                report['avvisi'].append(
                    f'{nome}: permesso "{codice}" non trovato (migration eseguita?)'
                )
                continue
            permessi.append(permesso)

        gruppo = Group.objects.filter(name=nome).first()
        if gruppo is None:
            report['creati'] += 1
            if dry_run:
                continue
            gruppo = None
            with transaction.atomic():
                gruppo = Group.objects.create(name=nome)
                gruppo.permissions.set(permessi)
            continue

        report['presenti'] += 1
        attuali = set(gruppo.permissions.all())
        nuovi = set(permessi)
        if attuali == nuovi:
            continue
        if not attuali:
            # gruppo creato da un segnale (es. sync_settore_groups) ma vuoto:
            # basta completarlo.
            report['aggiornati'] += 1
            if not dry_run:
                gruppo.permissions.set(nuovi)
        elif force:
            report['aggiornati'] += 1
            if not dry_run:
                gruppo.permissions.set(nuovi)
        else:
            report['avvisi'].append(
                f'{nome}: gia presente con {len(attuali)} permessi '
                f'(nel CSV {len(nuovi)}) - invariato, usa --force per sovrascrivere'
            )
    report['avvisi'] = list(dict.fromkeys(report['avvisi']))
    return report


# ---------------------------------------------------------------------------
# import - tipi di pratica
# ---------------------------------------------------------------------------

def carica_tipo_pratica(percorso, force=False, keep_ids=False, dry_run=False):
    """Crea/aggiorna i tipi di pratica dal CSV.

    I riferimenti (settore, servizio, u.o., uo_visibili, user) vengono
    risolti per chiave naturale: se mancano restano vuoti e viene aggiunto
    un avviso al report. Con ``keep_ids`` vengono mantenuti gli id originali
    (``id_orig``) e la sequenza del DB viene riallineata.
    """
    from django.contrib.auth import get_user_model
    from django.db import IntegrityError, transaction
    from protocollo.models import TipoPratica
    from struttura_ente.models import Settore, StoricoServizio, StoricoAttivitaUO

    User = get_user_model()
    report = _report()
    inseriti = False

    def _settore(codice, nome_tp):
        if not codice:
            return None
        obj = Settore.objects.filter(codice=codice).first()
        if obj is None:
            report['avvisi'].append(
                f'{nome_tp}: settore "{codice}" non trovato - campo lasciato vuoto'
            )
        return obj

    def _servizio(codice, nome_tp):
        if not codice:
            return None
        qs = StoricoServizio.objects.filter(codice=codice)
        obj = qs.filter(data_fine__isnull=True).first() or qs.first()
        if obj is None:
            report['avvisi'].append(
                f'{nome_tp}: servizio "{codice}" non trovato - campo lasciato vuoto'
            )
        return obj

    def _unita(nome_uo, nome_tp):
        if not nome_uo:
            return None
        qs = StoricoAttivitaUO.objects.filter(nome=nome_uo)
        obj = qs.filter(data_fine__isnull=True).first() or qs.first()
        if obj is None:
            report['avvisi'].append(
                f'{nome_tp}: unita operativa "{nome_uo}" non trovata - campo lasciato vuoto'
            )
        return obj

    def _utente(username, nome_tp):
        if not username:
            return None
        obj = User.objects.filter(username=username).first()
        if obj is None:
            report['avvisi'].append(
                f'{nome_tp}: utente "{username}" non trovato - campo lasciato vuoto'
            )
        return obj

    for riga in _leggi(percorso):
        nome = _valore(riga, 'name')
        if not nome:
            report['avvisi'].append('riga senza "name" saltata')
            continue

        campi = {
            'description': _valore(riga, 'description') or None,
            'settore': _settore(_valore(riga, 'settore'), nome),
            'servizio': _servizio(_valore(riga, 'servizio'), nome),
            'u_o': _unita(_valore(riga, 'u_o'), nome),
            'visibile_solo_uo': _booleano(_valore(riga, 'visibile_solo_uo')),
            'user': _utente(_valore(riga, 'user'), nome),
        }
        uo_visibili = [
            uo for uo in (
                _unita(nome_uo, nome) for nome_uo in _multi(_valore(riga, 'uo_visibili'))
            ) if uo is not None
        ]

        esistente = TipoPratica.objects.filter(name=nome).first()
        if esistente is None:
            report['creati'] += 1
            if dry_run:
                continue
            valori = dict(campi, name=nome)
            id_orig = _intero(_valore(riga, 'id_orig'))
            if keep_ids and id_orig:
                valori['id'] = id_orig
            try:
                with transaction.atomic():
                    tp = TipoPratica.objects.create(**valori)
                    tp.uo_visibili.set(uo_visibili)
            except IntegrityError as err:
                report['creati'] -= 1
                report['avvisi'].append(f'{nome}: non creato ({err})')
                continue
            inseriti = True
            continue

        report['presenti'] += 1
        if force:
            report['aggiornati'] += 1
            if not dry_run:
                for campo, valore in campi.items():
                    setattr(esistente, campo, valore)
                esistente.save()
                esistente.uo_visibili.set(uo_visibili)

    if inseriti and keep_ids:
        _riallinea_sequenza(TipoPratica)
    report['avvisi'] = list(dict.fromkeys(report['avvisi']))
    return report


def _riallinea_sequenza(model):
    """Porta la sequenza Postgres al massimo id (dopo un import con --keep-ids)."""
    from django.core.management.color import no_style
    from django.db import connection

    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), [model]):
            cursor.execute(sql)
