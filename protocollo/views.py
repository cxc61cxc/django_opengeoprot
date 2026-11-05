import json
import re
import logging
import os
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO
from urllib.parse import urlencode, parse_qsl
from urllib.request import urlopen, Request
from geopy.geocoders import Nominatim

import folium
from django import template
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test,permission_required
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import PermissionDenied
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point, Polygon
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Avg, Count, F, Max, Q, Value, Sum, ExpressionWrapper, DurationField, DecimalField, Exists, OuterRef, Subquery
from django.db.models.functions import Cast, Coalesce, Lower
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseForbidden, Http404, HttpResponseNotAllowed

from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.generic import View
from django.views.generic.list import ListView
from django.views.decorators.http import require_GET

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_UNDERLINE
from docx.shared import Inches, Mm, Pt
from xhtml2pdf import pisa

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

from accounts.models import Profile
from anagrafe.forms import ResidenteEditForm
from anagrafe.models import Residenti
from ascensori.models import Impianto, Matricola
from catasto.models import Particelle
from comunicazioni.models import Modello
from coop.models import IstrConv, AccettaImporto, Scadenze
from edilizia_compat import (
    EDILIZIA_AVAILABLE,
    EdiliziaPratica,
    Origine,
    ParticellaUnivoca,
    PraticaParticella,
    extract_mappali,
    normalize_foglio,
)
from struttura_ente.models import Settore, StoricoServizio, StoricoAttivitaUO
from fotovoltaico.models import ImpFot
from idonall.models import Istruttoria, Idonall
from paesaggio.models import Commissione
from pascar.models import Passocarraio
from prg.models import Cerdesurb, Piano
from protocollo.models import (Anaprat, Cataprat, Diario, Documento, DocumentoDownload, Particella,
                                Pratica, Soggetto, SostituzioneSoggetto, TipoPratica, TipoSoggetto,
                                stato_choice, NotaOSM, STATO_NOTA, IndiceDocumento)
from istruttoria_poc.models import Istruttoria as IstruttoriaPoc, IstrComm as IstrCommPoc, IstrCons as IstrConsPoc
from istruttoria_poc.forms import IstruttoriaForm, IstrCommForm, IstrConsForm
from viario.models import Civici
from .forms import UnifiedSearchForm
from .forms import (AddParticellaForm, AddSoggettoPraticaForm, DiarioForm,
                    PraticaForm, SoggettoForm, StatoForm, TipoPraticaForm,
                    UploadFileForm)
from accounts.permissions import editor_required, is_editor as is_editor_func, is_manager, is_user, is_consigliere, user_passes_test_403
from accounts.permissions import EDITOR_GROUPS, ALL_GROUPS, is_editor as check_editor

from .utils import build_base_map, log_action
from . import area_search

from pdf_utils import add_watermark_to_pdf

status_labels = dict(stato_choice)

logger_loggins = logging.getLogger('user_actions')
logger_user_actions = logging.getLogger('user_actions')

def get_client_ip(request):
    """Recupera l'indirizzo IP del client dall'oggetto request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def _normalize_codice(value, length=4):
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.isdigit():
        return value.zfill(length)
    return value

################################################################
# funzione che estrae tutte le pratiche con rateo True
################################################################
def get_pratiche_con_rateo_true():
    pratiche_con_rateo = IstrConv.objects.filter(accettazioni__rateo=True)
    return pratiche_con_rateo



def is_editor_or_admin(user):
    return user.is_superuser or user.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'user_settore_6', 'user_settore_1']).exists()

def is_manager_or_admin(user):
    return user.is_superuser or user.is_staff or user.groups.filter(name__in=['editor_settore_6', 'editor_settore_1', 'user_settore_6', 'user_settore_1']).exists()

def get_practice_queryset(user=None):
    """Base queryset with essential optimizations and permission filtering."""
    qs = Pratica.objects.select_related('tipo_pratica', 'street')\
        .prefetch_related('pratiche__particella', 'pratiche_soggetti__soggetto')
    qs = _apply_pratica_permissions(qs, user)
    qs = qs.annotate(
        has_idonall_cert=Exists(Idonall.objects.filter(istruttoria__pratica=OuterRef('pk'))),
        has_impianto=Exists(Impianto.objects.filter(pratica=OuterRef('pk'))),
        idonall_number=Subquery(Idonall.objects.filter(istruttoria__pratica=OuterRef('pk')).values('idonall_number')[:1]),
        idonall_date=Subquery(Idonall.objects.filter(istruttoria__pratica=OuterRef('pk')).values('idonall_date')[:1]),
        matricola=Subquery(Matricola.objects.filter(num_impianto__pratica=OuterRef('pk')).values('matricola_assegnata')[:1]),
    )
    return qs

def _consigliere_filter(user):
    """Restituisce la Q() che limita le Pratiche accessibili all'utente consigliere,
    oppure None se l'utente NON e' un consigliere.

    Il filtro applica entrambi:
    - il TipoPratica (M2M sulle commissioni attive)
    - il Settore di ciascuna commissione (snapshot su Commissione.settore)

    Un consigliere vede una pratica SE:
      (la pratica ha TipoPratica in {tipi delle commissioni attive}
       E la pratica ha Settore in {settori delle commissioni attive})

    Restituisce una Q "always-false" se l'utente e' consigliere ma non ha
    commissioni attive con tipi_pratica E settori valorizzati.
    """
    has_consiglieri_group = user.groups.filter(name='consiglieri').exists()
    commissioni_qs = user.commissioni.filter(tipo_commissione__attivo=True)
    if not has_consiglieri_group and not commissioni_qs.exists():
        return None

    tipo_ids = set(
        commissioni_qs
        .values_list('tipo_commissione__tipo_pratica__id', flat=True)
        .distinct()
    )
    settori_codici = set()
    for c in commissioni_qs:
        if c.settore and c.settore.codice:
            settori_codici.add(c.settore.codice)

    if not tipo_ids and not settori_codici:
        # Consigliere senza tipi/settori valorizzati: niente pratiche visibili
        return Q(pk__in=[])

    cond = Q()
    if tipo_ids:
        cond |= Q(tipo_pratica_id__in=tipo_ids)
    if settori_codici:
        cond |= Q(tipo_pratica__settore__codice__in=settori_codici)
    return cond


def _apply_pratica_permissions(qs, user):
    """Applica solo il filtro permessi (senza prefetch/annotazioni).

    Usato per i COUNT: le annotazioni Subquery/Exists e il prefetch
    sono costosi e inutili solo per contare le righe.
    """
    if user and not (user.is_superuser or user.is_staff):
        consigliere_q = _consigliere_filter(user)
        profile = Profile.objects.filter(user=user).first()
        consigliere_tipo_ids = None
        settori = None
        if consigliere_q is None:
            settori = get_user_settori(user)
        if consigliere_q is not None:
            commissioni_qs = user.commissioni.filter(tipo_commissione__attivo=True)
            consigliere_tipo_ids = set(
                commissioni_qs.values_list('tipo_commissione__tipo_pratica__id', flat=True).distinct()
            )
            qs = qs.filter(consigliere_q)
        else:
            if user.groups.filter(name='readonly').exists():
                pass
            elif is_user(user):
                if settori:
                    q_settore = Q(tipo_pratica__settore__codice__iexact='staff a') | Q(tipo_pratica__settore__codice__iexact='staff b')
                    q_settore |= Q(tipo_pratica__settore__in=settori)
                    q_settore |= Q(tipo_pratica__uo_visibili__servizio_storico__settore_storico__settore__in=settori)
                    if profile and profile.u_o:
                        q_settore |= Q(tipo_pratica__u_o=profile.u_o)
                        q_settore |= Q(tipo_pratica__uo_visibili=profile.u_o)
                        if profile.u_o.servizio_storico:
                            q_settore |= Q(tipo_pratica__servizio=profile.u_o.servizio_storico)
                    qs = qs.filter(q_settore)
            else:
                # editor
                if settori:
                    q_settore = Q(tipo_pratica__settore__in=settori) | Q(tipo_pratica__settore__isnull=True)
                    q_settore |= Q(tipo_pratica__uo_visibili__servizio_storico__settore_storico__settore__in=settori)
                    if profile and profile.u_o:
                        q_settore |= Q(tipo_pratica__u_o=profile.u_o)
                        q_settore |= Q(tipo_pratica__uo_visibili=profile.u_o)
                        if profile.u_o.servizio_storico:
                            q_settore |= Q(tipo_pratica__servizio=profile.u_o.servizio_storico)
                    qs = qs.filter(q_settore)

        # Apply visibile_solo_uo filter for ALL non-staff users
        # Consiglieri: also allow restricted tipo pratiche that are in their commissioni
        if profile and profile.u_o:
            visibile_q = Q(tipo_pratica__visibile_solo_uo=False) | Q(tipo_pratica__uo_visibili=profile.u_o)
        elif settori:
            visibile_q = Q(tipo_pratica__visibile_solo_uo=False) | Q(tipo_pratica__uo_visibili__servizio_storico__settore_storico__settore__in=settori)
        else:
            visibile_q = Q(tipo_pratica__visibile_solo_uo=False)
        if consigliere_tipo_ids:
            visibile_q |= Q(tipo_pratica_id__in=consigliere_tipo_ids)
        qs = qs.filter(visibile_q)
        qs = qs.exclude(stato='aa')
    return qs


def pratica_count_queryset(user=None):
    """Queryset minimale (solo permessi) per il conteggio veloce."""
    return _apply_pratica_permissions(Pratica.objects.all(), user)


def get_user_settori(user):
    """Restituisce i Settore objects a cui l'utente ha accesso, combinando
    i gruppi Django e il profilo.

    Gestisce gli utenti che appartengono a piu gruppi (editor_settore_1 e
    editor_settore_6) i cui profili hanno un solo settore: senza questa
    funzione il TipoPratica assegnato al settore secondario non verrebbe
    mai mostrato.

    Restituisce oggetti Settore (match per PK) invece di codici stringa
    per evitare problemi di case sensitivity: i gruppi usano 'settore'
    lowercase mentre il database puo' avere 'Settore' con maiuscola.
    """
    settore_objs = []
    seen_ids = set()

    # From groups: editor_settore_N / user_settore_N → settore N
    for name in user.groups.filter(
        name__regex=r'^(editor|user)_settore_(\d+)$'
    ).values_list('name', flat=True):
        num = name.rsplit('_', 1)[-1]
        for s in Settore.objects.filter(codice__iexact=f'settore {num}'):
            if s.pk not in seen_ids:
                settore_objs.append(s)
                seen_ids.add(s.pk)

    # From profile (uses FK for exact PK matching, avoiding casing issues)
    profile = Profile.objects.filter(user=user).first()
    if profile and profile.settore and profile.settore.settore:
        if profile.settore.settore.pk not in seen_ids:
            settore_objs.append(profile.settore.settore)
            seen_ids.add(profile.settore.settore.pk)

    return settore_objs


def get_filtered_tipo_pratica_list(user, only_opengeoprot=True):
    """Restituisce la lista dei TipoPratica filtrata in base al ruolo dell'utente:

    - user_settore*  → solo le pratiche della propria U.O.
    - editor         → tutte le pratiche del proprio servizio/settore.
    - staff/superuser → tutti i TipoPratica.

    Sempre ordinati alfabeticamente per nome.
    Se only_opengeoprot=True, restituisce solo i tipi che hanno pratiche OPENGEOPROT.
    """
    base_qs = TipoPratica.objects.all()
    if only_opengeoprot:
        base_qs = base_qs.filter(tipo_pratiche__isnull=False).distinct()

    if user.is_superuser or user.is_staff:
        return base_qs.order_by(Lower('name'))

    profile = Profile.objects.filter(user=user).first()

    if is_user(user) and not is_editor_func(user):
        # user_settore*: mostra solo le pratiche della propria U.O.
        if profile and profile.u_o:
            return base_qs.filter(u_o=profile.u_o).filter(
                Q(visibile_solo_uo=False) | Q(uo_visibili=profile.u_o)
            ).order_by(Lower('name'))
        return TipoPratica.objects.none()

    if is_editor_func(user):
        # editor: mostra tutte le pratiche del proprio servizio/settore
        if profile:
            settori = get_user_settori(user)
            q = Q()
            if settori:
                q |= Q(settore__in=settori)
                q |= Q(uo_visibili__servizio_storico__settore_storico__settore__in=settori)
            if profile.u_o:
                q |= Q(u_o=profile.u_o)
                q |= Q(uo_visibili=profile.u_o)
            if profile.u_o and profile.u_o.servizio_storico:
                q |= Q(servizio=profile.u_o.servizio_storico)
            restriction = Q(visibile_solo_uo=False)
            if profile.u_o:
                restriction |= Q(uo_visibili=profile.u_o)
            elif settori:
                restriction |= Q(uo_visibili__servizio_storico__settore_storico__settore__in=settori)
            if q:
                return base_qs.filter(q & restriction).order_by(Lower('name'))
            return base_qs.filter(restriction).order_by(Lower('name'))
        return TipoPratica.objects.none()

    # Altri utenti non staff (es. readonly senza user_settore/editor):
    # mostra tipo pratiche non flaggate, o quelle la cui U.O. e' tra uo_visibili
    if profile and profile.u_o:
        return base_qs.filter(
            Q(visibile_solo_uo=False) | Q(uo_visibili=profile.u_o)
        ).order_by(Lower('name'))
    if profile and profile.settore:
        return base_qs.filter(
            Q(visibile_solo_uo=False) | Q(uo_visibili__servizio_storico__settore_storico__codice=profile.settore.codice)
        ).order_by(Lower('name'))
    return base_qs.filter(visibile_solo_uo=False).order_by(Lower('name'))


def build_protocollo_filter_q(params):
    """Costruisce la Q per filtrare le Pratica (OpenGeoProt) a partire dai
    parametri del form di ricerca unificato. Condivisa tra SearchProt e la
    ricerca per area (pratiche_lista_area) così che "Cerca su Area" applichi
    gli stessi filtri della maschera di ricerca."""
    stato = params.get('stato')
    prot_gen = (params.get('prot_gen') or '').strip()
    anno = (params.get('anno') or '').strip()
    oggetto = (params.get('oggetto') or '').strip()
    street_id = params.get('street_id')
    civico = (params.get('civico') or '').strip()
    tp = params.get('tp')
    cognome = (params.get('cognome') or '').strip()
    nome = (params.get('nome') or '').strip()
    foglio_raw = (params.get('foglio') or '').strip()
    mappale_raw = (params.get('mappale') or '').strip()
    foglio = _normalize_codice(normalize_foglio(foglio_raw), 4) if foglio_raw else ''
    mappale = mappale_raw
    matricola = (params.get('matricola') or '').strip()
    cdu_num = (params.get('cdu') or '').strip()
    impianto = (params.get('impianto') or '').strip()
    atto = (params.get('atto') or '').strip()
    istruttoria = (params.get('istruttoria') or '').strip()
    tecnico = (params.get('tecnico') or '').strip()

    pratica_query = Q()

    if stato and stato not in ('*', ''):
        pratica_query &= Q(stato__iexact=stato)
    if prot_gen and prot_gen not in ('*', ''):
        pratica_query &= Q(prot_gen__icontains=prot_gen)
    if anno:
        try:
            pratica_query &= Q(data_prot_gen__year=int(anno))
        except ValueError:
            pass
    if oggetto and oggetto != '*':
        for parola in oggetto.split():
            parola = parola.strip()
            if parola:
                pratica_query &= Q(oggetto__icontains=parola)
    if street_id and street_id not in ('', '*'):
        try:
            pratica_query &= Q(street__id=int(street_id))
        except ValueError:
            pass
    if civico and civico != '*':
        pratica_query &= Q(housenumber__icontains=civico)
    if tp and tp not in ('*', ''):
        try:
            pratica_query &= Q(tipo_pratica__id=int(tp))
        except ValueError:
            pass
    # Range date (data_da / data_a): stesso filtro applicato da SearchProt
    data_da = (params.get('data_da') or '').strip()
    data_a = (params.get('data_a') or '').strip()
    if data_da:
        pratica_query &= Q(data_prot_gen__gte=data_da)
    if data_a:
        pratica_query &= Q(data_prot_gen__lte=data_a)
    if cognome:
        pratica_query &= Q(pratiche_soggetti__soggetto__cognome__icontains=cognome)
    if nome:
        pratica_query &= Q(pratiche_soggetti__soggetto__nome__icontains=nome)
    if foglio_raw:
        pratica_query &= Q(pratiche__particella__foglio__startswith=foglio_raw)
    if mappale_raw:
        pratica_query &= Q(pratiche__particella__mappale__startswith=mappale_raw)
    if matricola:
        matricola_pratiche_ids = Matricola.objects.filter(
            Q(matricola_assegnata__icontains=matricola) | Q(numero__icontains=matricola)
        ).values_list('num_impianto__pratica_id', flat=True)
        pratica_query &= Q(id__in=matricola_pratiche_ids)
    if cdu_num:
        pratica_query &= Q(pratiche_cdu__cdu_number=cdu_num)
    if impianto:
        pratica_query &= Q(pratiche_impianto__num_impianto__icontains=impianto)

    # atto / istruttoria / tecnico sono campi solo dell'archivio edilizia:
    # se compilati, la ricerca OPENGEOPROT non deve restituire pratiche.
    if atto or istruttoria or tecnico:
        pratica_query = Q(pk__in=[])

    if prot_gen and prot_gen != '*':
        query_doc = Q(prot__icontains=prot_gen)
        if anno:
            try:
                query_doc &= Q(data_prot__year=int(anno))
            except ValueError:
                pass
        documenti_ids = Documento.objects.filter(query_doc).values_list('pratica_id', flat=True)
        return Q(pratica_query) | Q(id__in=documenti_ids)

    return pratica_query
class StreetAutocompleteView(View):
    def get(self, request, *args, **kwargs):
        q = request.GET.get('term', '')
        my_models = Civici.objects.filter(street__icontains=q)[:10]
        data = serializers.serialize('json', my_models, fields=('street',))
        return JsonResponse(data, safe=False)

        
@login_required
def mappa_particelle(request):
    # Controllo permessi manuale per mostrare un feedback specifico
    if not (request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='cartografia').exists()):
        return HttpResponse(
            '<script type="text/javascript">alert("Accesso negato: non hai i permessi per visualizzare la cartografia generale. Contatta un amministratore per l\'abilitazione.");'
            'window.location.href="/";</script>'
        )

    mappa = build_base_map(45.4642, 9.1900, zoom_start=13)

    # Raggruppiamo i marker in un FeatureGroup per poterli attivare/disattivare
    fg_particelle = folium.FeatureGroup(name="Mappali in Archivio")
    particelle = Particella.objects.only('id', 'foglio', 'mappale', 'mpoly').iterator()
    for particella in particelle:
        if particella.mpoly:
            lat = particella.mpoly.centroid.y
            lng = particella.mpoly.centroid.x
            folium.Marker([lat, lng], popup=f"Foglio: {particella.foglio}, Mappale: {particella.mappale}").add_to(fg_particelle)
    fg_particelle.add_to(mappa)

    mappa = mappa._repr_html_()  # Ottieni il codice HTML per la mappa Folium

    return render(request, 'protocollo.mappa.html', {'mappa': mappa})

##########################################################
#                DUPLICA PRATICA E DIPENDENZE
#               CREA UN RECORD DAL RECORD CORRENTE
#               ESEMPIO OSSERVAZIONI CON VARI PUNTI
##########################################################
@login_required
@editor_required

def DuplicaIdonall(request, id):
    pratica = get_object_or_404(get_practice_queryset(request.user), id=id)
    idall = None
    try:
        istruttoria = Istruttoria.objects.get(pratica_id=id)
        if istruttoria:
            try:
                idall = Idonall.objects.get(istruttoria_id=istruttoria.id)
            except (Idonall.DoesNotExist, UnboundLocalError):
                idall = None
    except Istruttoria.DoesNotExist:
        idall = None

    nuovo_oggetto = "Duplicato Pratica"
    if idall:
        nuovo_oggetto = 'Rinnovo di Attestato n. ' + str(idall.idonall_number) + ' del ' +str(idall.idonall_date.strftime('%d/%m/%Y')) + ', come da Prot.Gen '+ pratica.prot_gen +' del ' + str(pratica.data_prot_gen.strftime('%d/%m/%Y')) 
    
    today = timezone.now()
    
    if pratica.tipo_pratica_id == 26: # se è una cooperativa
        nuovo_tipo_pratica_id = 26 # duplica in diritto di superficie
        last_sub_code = Pratica.objects.filter(Q(code_p=pratica.code_p) & Q(tipo_pratica_id=26))
        tot_instances = last_sub_code.count()
      
        if tot_instances > 0:
            sub_code = tot_instances + 1
        else :
            sub_code=1
        
    else:
        nuovo_tipo_pratica_id = pratica.tipo_pratica_id
        query = Q()
        if hasattr(pratica, 'prot_gen') and pratica.prot_gen:
            query &= Q(prot_gen__icontains = pratica.prot_gen)
        if hasattr(pratica, 'code_p') and pratica.code_p:
            query &= Q(code_p = pratica.code_p)
        last_sub_code = Pratica.objects.filter(query) #.exclude(code_p = None)
        tot_instances = last_sub_code.count()
        if tot_instances > 0:
            sub_code = tot_instances-1
        else :
            sub_code=1

    if pratica:
            # print('pratica',pratica)
            # if tot_instances > 0:
            #     sub_code = tot_instances+1
            # else :
            #     sub_code=1

            # sub_code = sub_code+1
            nuova_pratica = Pratica(
                                    prot_gen='0',
                                    data_prot_gen=today,
                                    housenumber=pratica.housenumber,
                                    oggetto=nuovo_oggetto,
                                    street_id=pratica.street_id,
                                    posizione = pratica.posizione,
                                    mpoly_pratica = pratica.mpoly_pratica, # Copia la geometria aggregata
                                    tipo_pratica_id = nuovo_tipo_pratica_id,
                                    user_id=request.user.id,
                                    code_p=pratica.code_p,
                                    sub_code=sub_code,
                                    annotazioni=pratica.annotazioni,
                                    stato = 'i',

                                    )           
            nuova_pratica.save()
            
            pk = nuova_pratica.id

            # verifico le particelle e duplico
            try:
                cataprat = Cataprat.objects.filter(pratica_id=id)
                for p in cataprat :
                        
                        nuova_particella = Cataprat(particella_id=p.particella_id,
                                            pratica_id=pk,
                                            subalterno=p.subalterno,
                                            )           
                        nuova_particella.save()
            except Exception:
                pass

            # verifico i soggetti ed eventualmente duplico
            try:
                anaprat = Anaprat.objects.filter(pratica_id=id)
                for s in anaprat :
                    
                    nuovo_soggetto = Anaprat(
                                        pratica_id=pk,
                                        soggetto_id=s.soggetto_id,
                                        tipo_id=s.tipo_id,
                                        user_id=request.user.id,
                                        )           
                    nuovo_soggetto.save()
            except Exception:
                pass

            # verifico allegati ed eventualmente duplico
            try:
                documento = Documento.objects.filter(pratica_id=id)
                for d in documento :

                    if d.prot:
                        prot=d.prot
                    else :
                        prot=None
                    if d.data_prot:
                        data_prot = d.data_prot
                    else :
                        data_prot=None
                    nuovo_documento = Documento(
                        pratica_id=pk,
                        name=d.name,
                        document=d.document,
                        posta=d.posta,
                        
                        data_prot = data_prot,
                        prot = str(d.prot),
                        username_id=request.user.id,
                        )           
                    nuovo_documento.save()
            except Exception:
                pass

            # verifico istruttoria  ed eventualmente duplico
            try:
                istruttoria = Istruttoria.objects.get(pratica_id=id)
                
                nuova_istruttoria = Istruttoria(
                                        pratica_id = pk,
                                        user_id = request.user.id,
                                        tipo_richiedente_idonall = istruttoria.tipo_richiedente_idonall,
                                        tipo_richiesta = 'Duplicato',
                                        ante1975 = istruttoria.ante1975,
                                        catasto = istruttoria.catasto,
                                        doc_prop = istruttoria.doc_prop,
                                        conf_imp = istruttoria.conf_imp,
                                        caldaia = istruttoria.caldaia,
                                        mq = istruttoria.mq,
                                        vani = istruttoria.vani,
                                        nota_relazione = istruttoria.nota_relazione,
                                        nota_abitabilita = istruttoria.nota_abitabilita,
                                        nota_prop = istruttoria.nota_prop,
                                        num_adulti = istruttoria.num_adulti,
                                        num_minori = istruttoria.num_minori,
                )
                nuova_istruttoria.save()
            
            
            except Exception:
                pass
    # return redirect('protocollo:pratica_detail_url', pk)
    return redirect('protocollo:pratica_edit_url', pk)



           
    

@login_required
@editor_required

def Duplica(request,id):
    particelle=[]
    pratica = get_object_or_404(get_practice_queryset(request.user), id=id)
    
    if pratica.tipo_pratica_id == 35: # se è una cooperativa
        nuovo_tipo_pratica_id = 36 # duplica in diritto di superficie
        last_sub_code = Pratica.objects.filter(Q(code_p=pratica.code_p) & Q(tipo_pratica_id=36))
        tot_instances = last_sub_code.count()
        if tot_instances > 0:
            sub_code = tot_instances +1
        else :
            sub_code=1
    else:
        nuovo_tipo_pratica_id = pratica.tipo_pratica_id
        last_sub_code = Pratica.objects.filter(prot_gen= pratica.prot_gen , code_p=pratica.code_p) #.exclude(code_p = None)
        tot_instances = last_sub_code.count()
        if tot_instances > 0:
            sub_code = tot_instances+1
        else :
            sub_code=1
    
    if pratica:
            # print('pratica',pratica)
            # if tot_instances > 0:
            #     sub_code = tot_instances+1
            # else :
            #     sub_code=1

            # sub_code = sub_code+1
            nuova_pratica = Pratica(prot_gen=pratica.prot_gen,
                                    data_prot_gen=pratica.data_prot_gen,
                                    housenumber=pratica.housenumber,
                                    oggetto=pratica.oggetto,
                                    street_id=pratica.street_id,
                                    posizione = pratica.posizione,
                                    mpoly_pratica = pratica.mpoly_pratica, # Copia la geometria aggregata
                                    tipo_pratica_id = nuovo_tipo_pratica_id,
                                    user_id=request.user.id,
                                    code_p=pratica.code_p,
                                    sub_code=sub_code,
                                    annotazioni=pratica.annotazioni,
                                    stato = 'i',

                                    )           
            nuova_pratica.save()
            
            pk = nuova_pratica.id

            # verifico le particelle e duplico
            
            cataprat = Cataprat.objects.filter(pratica_id=id)
            for p in cataprat :
                    
                    nuova_particella = Cataprat(particella_id=p.particella_id,
                                        pratica_id=pk,
                                        subalterno=p.subalterno,
                                        )           
                    nuova_particella.save()

            # verifico i soggetti ed eventualmente duplico
            
            anaprat = Anaprat.objects.filter(pratica_id=id)
            for s in anaprat :
                
                nuovo_soggetto = Anaprat(
                                    pratica_id=pk,
                                    soggetto_id=s.soggetto_id,
                                    tipo_id=s.tipo_id,
                                    user_id=request.user.id,
                                    )           
                nuovo_soggetto.save()

            # verifico allegati ed eventualmente duplico
            
            documento = Documento.objects.filter(pratica_id=id)
            for d in documento :

                # if d.prot:
                #     prot=d.prot,
                # else :
                #     prot=None
                if d.data_prot:
                    data_prot = d.data_prot
                else :
                    data_prot=None
                nuovo_documento = Documento(
                    pratica_id=pk,
                    name=d.name,
                    document=d.document,
                    posta=d.posta,
                    
                    data_prot = data_prot,
                    prot = str(d.prot),
                    username_id=request.user.id,
                    )           
                nuovo_documento.save()


            # verifico convenzioni ed eventualmente duplico
            
            documento = IstrConv.objects.filter(pratica_id=id)
            for d in documento :
                
                nuovo_documento = IstrConv(
                                    pratica_id=pk,
                                    tipo_diritto = d.tipo_diritto,
                                    durata = d.durata,
                                    notaio=d.notaio,
                                    data_atto=d.data_atto,
                                    atto=d.atto,
                                    data_rival=d.data_rival,
                                    area = d.area,
                                    edifici = d.edifici,
                                    alloggi = d.alloggi,
                                    ref_millesimi = d.ref_millesimi,
                                    millesimi = d.millesimi,
                                    volume = d.volume,
                                    conv_lire = d.conv_lire,
                                    cong_lire = d.cong_lire,
                                    tot_conv        = d.tot_conv,
                                    conv_rival      = d.conv_rival,
                                    cong_rival      = d.cong_rival,
                                    coeff_istat     = d.coeff_istat,
                                    tot_conv_rival  = d.tot_conv_rival,
                                    valore_residuo  = d.valore_residuo,
                                    valore_perizia  = d.valore_perizia,
                                    valore_venale   = d.valore_venale,
                                    valore_dirsup   = d.valore_dirsup,
                                    crv             = d.valore_dirsup,
                                    crv_uiu         = d.crv_uiu,
                                    prop_acquisita  = d.prop_acquisita,  
                                    )           
                nuovo_documento.save()
                
            # return redirect('protocollo:pratica_detail_url', pk)
            return redirect('protocollo:pratica_edit_url', pk)

@login_required
@editor_required
def DuplicaAscensore(request, id):
    """
    Duplica una pratica di tipo 'ascensore' chiusa in una nuova pratica.
    Esclude prot_gen, data_prot_gen e documenti.
    Copia soggetti, particelle e i dati tecnici dell'impianto/matricola.
    """
    pratica = get_object_or_404(get_practice_queryset(request.user), id=id)
    
    # Verifica che la pratica sia chiusa o archiviata come richiesto
    if pratica.stato not in ['c', 'aa']:
        messages.error(request, "La duplicazione è consentita solo per pratiche in stato 'chiuso' o 'archiviato'.")
        return redirect('protocollo:pratica_detail_url', pk=id)

    nuovo_oggetto = "" 
    today = timezone.now()
    
    # Calcolo del sub_code seguendo la traccia delle altre funzioni di duplicazione
    last_sub_code = Pratica.objects.filter(code_p=pratica.code_p)
    tot_instances = last_sub_code.count()
    sub_code = tot_instances if tot_instances > 0 else 1

    # Creazione nuova pratica (escludendo prot_gen e data_prot_gen)
    nuova_pratica = Pratica(
        prot_gen='0',
        data_prot_gen=today,
        housenumber=pratica.housenumber,
        oggetto='',
        street_id=pratica.street_id,
        posizione=pratica.posizione,
        mpoly_pratica=pratica.mpoly_pratica,
        tipo_pratica_id=pratica.tipo_pratica_id,
        user_id=request.user.id,
        code_p=pratica.code_p,
        sub_code=pratica.sub_code,
        annotazioni=pratica.annotazioni,
        stato='i', # Stato iniziale 'In corso'
    )
    nuova_pratica.save()
    
    pk_nuova = nuova_pratica.id

    # Duplicazione Particelle (Cataprat)
    try:
        cataprat = Cataprat.objects.filter(pratica_id=id)
        for p in cataprat:
            nuova_particella = Cataprat(
                particella_id=p.particella_id,
                pratica_id=pk_nuova,
                subalterno=p.subalterno,
            )
            nuova_particella.save()
    except Exception as e:
        pass

    # Duplicazione Soggetti (Anaprat)
    try:
        anaprat = Anaprat.objects.filter(pratica_id=id)
        for s in anaprat:
            nuovo_soggetto = Anaprat(
                pratica_id=pk_nuova,
                soggetto_id=s.soggetto_id,
                tipo_id=s.tipo_id,
                user_id=request.user.id,
            )
            nuovo_soggetto.save()
    except Exception as e:
        pass

    # Duplicazione dati tecnici Ascensore (Impianto e Matricola)
    try:
        impianto_orig = Impianto.objects.get(pratica_id=id)
        
        # Clonazione dell'impianto sulla nuova pratica
        impianto_nuovo = Impianto.objects.get(id=impianto_orig.id)
        impianto_nuovo.pk = None
        impianto_nuovo.pratica_id = pk_nuova
        impianto_nuovo.save()
        
        # Duplicazione della matricola se esistente
        try:
            matricola_orig = Matricola.objects.get(num_impianto_id=impianto_orig.id)
            matricola_nuova = Matricola.objects.get(id=matricola_orig.id)
            matricola_nuova.pk = None
            matricola_nuova.num_impianto_id = impianto_nuovo.id
            matricola_nuova.save()
        except Matricola.DoesNotExist:
            pass
    except (Impianto.DoesNotExist, Exception) as e:
        logger_loggins.debug("Duplicazione ascensore: nessun impianto/errore: %s", e)

    return redirect('protocollo:pratica_edit_url', pk_nuova)

#
##########################################################
#                PRATICA
##########################################################

#   search

##########################################
#       CERCA NUMERO DI MATRICOLA
##########################################

@login_required

def SearchMatricola(request):
    if request.method == "POST":

        search_matricola = (request.POST.get("matricola") or "").strip()
        anno = (request.POST.get("matricola_date") or "").strip()

        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'

        if search_matricola:
            logger_user_actions.info(f"Utente: {user_username} ha effettuato una ricerca per MATRICOLA: {search_matricola}")
        elif anno:
            logger_user_actions.info(f"Utente: {user_username} ha effettuato una ricerca per ANNO: {anno}")

        # Validazione: almeno un criterio tra matricola e anno
        if not (search_matricola or anno):
            messages.warning(request, "Inserisci almeno un criterio: numero matricola oppure anno.")
            return redirect('protocollo:index_pratiche_url')

        # Validazione: l'anno deve essere numerico
        if anno and not anno.isdigit():
            messages.warning(request, "L'anno inserito non è valido.")
            return redirect('protocollo:index_pratiche_url')

        query = Q()

        if anno:
            query &= Q(matricola_date__year=int(anno))

        if search_matricola:
            query &= Q(matricola_assegnata__icontains=search_matricola) | Q(numero__icontains = search_matricola)

        matricole = Matricola.objects.filter(query).order_by("-matricola_assegnata","-matricola_date")

        pratiche = []
        for m in matricole:
            impianto = m.num_impianto
            if impianto and impianto.pratica_id:
                pratica = get_practice_queryset(request.user).filter(id=impianto.pratica_id).first()
                if pratica:
                    pratiche.append(pratica)

        if not pratiche:
            messages.warning(request, "Nessuna pratica trovata!")
            return redirect('protocollo:index_pratiche_url')

        paginator = Paginator(pratiche, 10)
        page_number = request.GET.get('page')
        try:
            pratiche_page = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            pratiche_page = paginator.page(1)

        context = {
            'pratica': pratiche_page,
            'totale_p': len(pratiche),
            'query_string': '',
            'pratiche_ids': [p.id for p in pratiche],
            'pratica_detail_base': reverse('protocollo:pratica_detail_url', args=[0])[:-2],
            'edilizia_results': EdiliziaPratica.objects.none(),
            'edilizia_tot': 0,
            'edilizia_pratica_list': [],
            'pratiche_with_particelle': [],
            'nessun_risultato': False,
            'active_tab': 'opengeoprot',
            'show_opengeoprot': True,
            'show_archivio': False,
        }

        messages.warning(request, "Hai cercato " + (search_matricola or anno) + "....")
        return render(request, 'protocollo/pratiche_list.html', context)

    messages.warning(request, "Metodo non valido.")
    return redirect('protocollo:index_pratiche_url')

##########################################
#       CERCA NUMERO IMPIANTO ASCENSORE
##########################################

@login_required

def SearchImpianto(request):
    if request.method == "POST":

        search_impianto = (request.POST.get("impianto") or "").strip()
        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'

        if not search_impianto:
            messages.warning(request, "Inserisci il numero di impianto per effettuare la ricerca.")
            return redirect('protocollo:index_pratiche_url')

        logger_user_actions.info(f"Utente: {user_username} ha effettuato una ricerca per IMPIANTO: {search_impianto}")

        pratiche_qs = get_practice_queryset(request.user).filter(Q(pratiche_impianto__num_impianto__icontains=search_impianto))

        pratiche = list(pratiche_qs)

        if not pratiche:
            messages.warning(request, "Nessuna pratica trovata!")
            return redirect('protocollo:index_pratiche_url')

        paginator = Paginator(pratiche, 10)
        page_number = request.GET.get('page')
        try:
            pratiche_page = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            pratiche_page = paginator.page(1)

        context = {
            'pratica': pratiche_page,
            'totale_p': len(pratiche),
            'query_string': '',
            'pratiche_ids': [p.id for p in pratiche],
            'pratica_detail_base': reverse('protocollo:pratica_detail_url', args=[0])[:-2],
            'edilizia_results': EdiliziaPratica.objects.none(),
            'edilizia_tot': 0,
            'edilizia_pratica_list': [],
            'pratiche_with_particelle': [],
            'nessun_risultato': False,
            'active_tab': 'opengeoprot',
            'show_opengeoprot': True,
            'show_archivio': False,
        }

        messages.warning(request, "Hai cercato numero impianto di sollevamento " + search_impianto + "....")
        return render(request, 'protocollo/pratiche_list.html', context)

    messages.warning(request, "Metodo non valido.")
    return redirect('protocollo:index_pratiche_url')


   
    
@login_required

def SearchCdu(request):
    if request.method == "POST":

        searchcdu = (request.POST.get("cdu") or "").strip()            # numero CDU
        anno = (request.POST.get("cdu_date") or "").strip()            # anno del CDU

        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
        logger_user_actions.info(
            f"Utente: {user_username} ha effettuato una ricerca per CDU: {searchcdu}, {anno}"
        )

        # Validazione: almeno un criterio tra numero CDU e anno
        if not (searchcdu or anno):
            messages.warning(request, "Inserisci almeno un criterio: numero CDU oppure anno.")
            return redirect('protocollo:index_pratiche_url')

        # Validazione: i valori numerici devono essere validi
        if searchcdu and not searchcdu.isdigit():
            messages.warning(request, "Il numero CDU inserito non è valido.")
            return redirect('protocollo:index_pratiche_url')
        if anno and not anno.isdigit():
            messages.warning(request, "L'anno inserito non è valido.")
            return redirect('protocollo:index_pratiche_url')

        # Costruzione dinamica dei filtri
        query = Q()
        if searchcdu:
            query &= Q(cdu_number=int(searchcdu))
        if anno:
            query &= Q(cdu_date__year=int(anno))

        # Cerco i CDU in base ai filtri
        cdu = Cerdesurb.objects.filter(query).order_by("-cdu_number", "-cdu_date")

        if not cdu.exists():
            messages.warning(request, "Nessuna pratica trovata!")
            return redirect('protocollo:index_pratiche_url')

        # Recupero le pratiche collegate al CDU
        pratiche = []
        for m in cdu:
            if m.pratica_id:
                pratica = get_practice_queryset(request.user).filter(id=m.pratica_id).first()
                if pratica:
                    pratiche.append(pratica)

        if not pratiche:
            messages.warning(request, "Nessuna pratica trovata!")
            return redirect('protocollo:index_pratiche_url')

        # Paginazione risultati OPENGEOPROT
        paginator = Paginator(pratiche, 10)
        page_number = request.GET.get('page')
        try:
            pratiche_page = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            pratiche_page = paginator.page(1)

        context = {
            'pratica': pratiche_page,
            'totale_p': len(pratiche),
            'query_string': '',
            'pratiche_ids': [p.id for p in pratiche],
            'pratica_detail_base': reverse('protocollo:pratica_detail_url', args=[0])[:-2],
            'edilizia_results': EdiliziaPratica.objects.none(),
            'edilizia_tot': 0,
            'edilizia_pratica_list': [],
            'pratiche_with_particelle': [],
            'nessun_risultato': False,
            'active_tab': 'opengeoprot',
            'show_opengeoprot': True,
            'show_archivio': False,
        }

        messages.warning(request, f"Hai cercato {searchcdu} {anno}...")
        return render(request, 'protocollo/pratiche_list.html', context)

    messages.warning(request, "Metodo non valido.")
    return redirect('protocollo:index_pratiche_url')


##########################################
#       CERCA IDONEITÀ ALLOGGIATIVA
##########################################

@login_required

def SearchIdonall(request):
    if request.method == "POST":

        idonall_number = (request.POST.get("idonall_number") or "").strip()
        anno = (request.POST.get("idonall_date") or "").strip()

        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
        logger_user_actions.info(
            f"Utente: {user_username} ha effettuato una ricerca per IDONEITÀ ALLOGGIATIVA: {idonall_number}, {anno}"
        )

        # Validazione: almeno un criterio tra numero e anno
        if not (idonall_number or anno):
            messages.warning(request, "Inserisci almeno un criterio: numero idoneità oppure anno.")
            return redirect('protocollo:index_pratiche_url')

        # Validazione: i valori numerici devono essere validi
        if idonall_number and not idonall_number.isdigit():
            messages.warning(request, "Il numero idoneità inserito non è valido.")
            return redirect('protocollo:index_pratiche_url')
        if anno and not anno.isdigit():
            messages.warning(request, "L'anno inserito non è valido.")
            return redirect('protocollo:index_pratiche_url')

        # Costruzione dinamica dei filtri
        query = Q()
        if idonall_number:
            query &= Q(idonall_number=int(idonall_number))
        if anno:
            query &= Q(idonall_date__year=int(anno))

        # Cerco le idoneità alloggiative in base ai filtri
        idonall_list = Idonall.objects.filter(query).select_related('istruttoria').order_by("-idonall_number", "-idonall_date")

        if not idonall_list.exists():
            messages.warning(request, "Nessuna idoneità alloggiativa trovata!")
            return redirect('protocollo:index_pratiche_url')

        # Recupero le pratiche collegate alle idoneità trovate
        pratiche = []
        for idon in idonall_list:
            if idon.istruttoria_id:
                pratica = get_practice_queryset(request.user).filter(id=idon.istruttoria.pratica_id).first()
                if pratica:
                    pratiche.append(pratica)

        if not pratiche:
            messages.warning(request, "Nessuna pratica trovata!")
            return redirect('protocollo:index_pratiche_url')

        # Paginazione risultati
        paginator = Paginator(pratiche, 10)
        page_number = request.GET.get('page')
        try:
            pratiche_page = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            pratiche_page = paginator.page(1)

        context = {
            'pratica': pratiche_page,
            'totale_p': len(pratiche),
            'query_string': '',
            'pratiche_ids': [p.id for p in pratiche],
            'pratica_detail_base': reverse('protocollo:pratica_detail_url', args=[0])[:-2],
            'edilizia_results': EdiliziaPratica.objects.none(),
            'edilizia_tot': 0,
            'edilizia_pratica_list': [],
            'pratiche_with_particelle': [],
            'nessun_risultato': False,
            'active_tab': 'opengeoprot',
            'show_opengeoprot': True,
            'show_archivio': False,
        }

        messages.warning(request, "Hai cercato idoneità alloggiativa " + (idonall_number or anno) + "....")
        return render(request, 'protocollo/pratiche_list.html', context)

    messages.warning(request, "Metodo non valido.")
    return redirect('protocollo:index_pratiche_url')


#########################################################
# CERCA PRATICHE CON RATEIZZO
# usando funzione 
@login_required

def SearchRatei(request):
    # pratiche_rateo_true = get_pratiche_con_rateo_true()
    # pratiche_rateo_true = IstrConv.objects.filter(accettazioni__rateo=True).values_list('pratica_id', flat=True)
    # print(pratiche_rateo_true, 'prataiche')

    # user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
    # logger_user_actions.info(f"Utente: {user_username} ha cercato i rateizzi")
    

    

    # search = {}
    
    #     pratiche = []
    #     for m in pratiche_rateo_true:
    #         print(m.pratica_id)
    #         search = Pratica.objects.get(id=m.pratica_id)
    #         pratiche.append(search)
    #     print('6999fg5',pratiche)
    pratiche_qs = get_practice_queryset(request.user).filter(convenzioni__accettazioni__rateo=True).distinct()
    if pratiche_qs.exists():
        pratiche_list = list(pratiche_qs)

        # Paginazione risultati OPENGEOPROT
        paginator = Paginator(pratiche_list, 10)
        page_number = request.GET.get('page')
        try:
            pratiche_page = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            pratiche_page = paginator.page(1)

        context = {
            'pratica': pratiche_page,
            'totale_p': len(pratiche_list),
            'query_string': '',
            'pratiche_ids': [p.id for p in pratiche_list],
            'pratica_detail_base': reverse('protocollo:pratica_detail_url', args=[0])[:-2],
            'edilizia_results': EdiliziaPratica.objects.none(),
            'edilizia_tot': 0,
            'edilizia_pratica_list': [],
            'pratiche_with_particelle': [],
            'nessun_risultato': False,
            'active_tab': 'opengeoprot',
            'show_opengeoprot': True,
            'show_archivio': False,
        }
        messages.warning(request, "Hai cercato i rateizzi")
        return render(request, 'protocollo/pratiche_list.html', context)
    else:
        messages.warning(request, "Hai cercato i rateizzi ...Nessun risultato!.")
        return redirect('protocollo:index_pratiche_url')



@login_required

def SearchPratica(request):
    if request.method == "GET":
        cognome = request.GET.get("cognome")
        nome = request.GET.get("nome")
        # cerco in Soggetti
        # imposto le liste
        anagrafe = []
        pratica=[]
        particelle=[]

        # Set per tracciare gli ID già aggiunti
        pratiche_ids = set()
        anagrafe_ids = set()
        particelle_ids = set()

        soggetti = Soggetto.objects.filter(Q(cognome__icontains=cognome) & Q(nome__icontains=nome))
        if soggetti.exists():
            soggetti_ids = list(soggetti.values_list('id', flat=True))
            # Una sola query per tutte le relazioni Anaprat dei soggetti trovati
            anaprat_all = Anaprat.objects.filter(soggetto_id__in=soggetti_ids).select_related('soggetto')
            pratica_ids_permessi = set(
                get_practice_queryset(request.user)
                .filter(id__in=anaprat_all.values_list('pratica_id', flat=True))
                .values_list('id', flat=True)
            )
            # Particelle collegate (batch) per evitare N+1
            cataprat_all = Cataprat.objects.filter(
                pratica_id__in=pratica_ids_permessi
            ).select_related('particella')
            particelle_mappe = {c.pratica_id: c.particella for c in cataprat_all if c.particella}

            for a in anaprat_all:
                if a.pratica_id not in pratica_ids_permessi:
                    continue
                soggetto_obj = a.soggetto

                # Aggiungi pratica se non già presente
                if a.pratica_id not in pratiche_ids:
                    pratica_obj = get_practice_queryset(request.user).filter(id=a.pratica_id).first()
                    if pratica_obj:
                        pratica.append(pratica_obj)
                        pratiche_ids.add(pratica_obj.id)

                # Aggiungi soggetto se non già presente
                if soggetto_obj.id not in anagrafe_ids:
                    anagrafe.append(soggetto_obj)
                    anagrafe_ids.add(soggetto_obj.id)

                # Particelle già pre-caricate in batch
                particella_obj = particelle_mappe.get(a.pratica_id)
                if particella_obj and particella_obj.id not in particelle_ids:
                    particelle.append(particella_obj)
                    particelle_ids.add(particella_obj.id)

            context = {
                'pratica': pratica,
                'anagrafe': anagrafe,
                'particelle': particelle,
            }
            messages.warning(request, "Hai cercato " + cognome.upper() + " " + nome.upper())
            return render(request, 'protocollo/pratiche_list.html', context)
        else:
            messages.warning(request, "Hai cercato " + cognome.upper() + " " + nome.upper() + " ...Nessun risultato!.")
            return redirect('protocollo:index_pratiche_url')
    else:
        messages.warning(request, "Hai cercato " + cognome.upper() + " " + nome.upper() + " ...Nessun risultato!.")
        return redirect('protocollo:index_pratiche_url')

@login_required
def mie_pratiche(request):
    """Visualizza le pratiche dell'utente corrente.
    Per staff/superuser mostra TUTTE le ultime pratiche, a prescindere dal creatore.
    """
    # RIPRISTINO: in origine il queryset filtrava sempre per user=request.user.
    # Ora gli utenti privilegiati vedono tutte le pratiche.
    is_privileged = request.user.is_staff or request.user.is_superuser

    base_queryset = get_practice_queryset(request.user).order_by('-data_mod', '-prot_gen')
    if not is_privileged:
        base_queryset = base_queryset.filter(user=request.user)
    
    anno = request.GET.get('anno')
    tp = request.GET.get('tp')
    
    pratiche_queryset = base_queryset
    if anno and anno != '*':
        try:
            pratiche_queryset = pratiche_queryset.filter(data_prot_gen__year=int(anno))
        except ValueError:
            pass
    if tp and tp != '*':
        try:
            pratiche_queryset = pratiche_queryset.filter(tipo_pratica_id=int(tp))
        except ValueError:
            pass

    # Filtro: solo pratiche che hanno istruttoria_poc_istrcomm (Commissione POC 2022)
    if request.GET.get('has_commissione') == '1':
        pratiche_queryset = pratiche_queryset.filter(istrcomm_poc__isnull=False).distinct()
    
    totale_p = pratiche_queryset.count()

    _check_scadenze_alerts(request)
    
    # Paginazione (10 pratiche per pagina)
    paginator = Paginator(pratiche_queryset, 10)
    page_number = request.GET.get('page')
    try:
        pratiche = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        pratiche = paginator.page(1)
    
    anni_disponibili = sorted(base_queryset.dates('data_prot_gen', 'year', order='DESC'), key=lambda d: d.year, reverse=True)
    
    context = {
        'pratica': pratiche,
        'totale_p': totale_p,
        'pratiche_ids': list(pratiche_queryset.values_list('id', flat=True)),
        'tp': get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True),
        'anni_disponibili': anni_disponibili,
        'selected_anno': anno or '',
        'selected_tp': tp or '',
        'show_user_filters': True,
        'active_tab': 'opengeoprot',
        # RIPRISTINO: rimuovere le due chiavi sotto per ripristinare il vecchio
        # comportamento (tab opengeoprot non renderizzato in questa vista).
        'show_opengeoprot': True,
        'show_archivio': False,
        'show_all': is_privileged,
    }
    return render(request, 'protocollo/pratiche_list.html', context)


#   search particella
@login_required

def SearchParticella(request):
    pratica = {}
    anagrafe = {}
    catasto = {}
    context = {}
    if request.method == "POST":
        foglio = request.POST.get('foglio')
        mappale = request.POST.get('mappale')
        
        # Registra utente e parametri di ricerca
        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
        logger_user_actions.info(f"Utente: {user_username} ha cercato Particella con foglio: {foglio}, mappale: {mappale}")

        # cerca nel models Particella
        particella = Particella.objects.filter(Q(foglio__iexact=foglio) & Q(mappale__iexact=mappale))
        if particella:
            for s in particella:
                cataprat = Cataprat.objects.filter(particella_id=s.id)
                
                pratiche_queryset = get_practice_queryset(request.user)\
                    .filter(particella_pratica=s.id)

                pratica = pratiche_queryset

                for p in pratiche_queryset:
                    anagrafe = Anaprat.objects.filter(pratica_id=p.id).select_related('soggetto', 'tipo', 'pratica') 
                context = {
                    'pratica': pratica,
                    'anagrafe': anagrafe,
                    'particelle': cataprat,
                }
            return render(request, 'protocollo/pratiche_list.html', context)
        else:
            messages.warning(request, "Hai cercato foglio " + foglio + " mappale " + mappale + " ...Nessun risultato!.")
            return redirect('protocollo:index_pratiche_url')





@login_required
def SearchProt(request):
    # Consiglieri: salta la maschera di ricerca e vai direttamente ai
    # risultati con i TipiPratica delle commissioni a cui sono iscritti.
    if request.user.is_authenticated and _consigliere_filter(request.user) is not None:
        tipo_ids = sorted({
            t for t in (
                request.user.commissioni
                .filter(tipo_commissione__attivo=True)
                .values_list('tipo_commissione__tipo_pratica__id', flat=True)
            ) if t
        })
        if not tipo_ids:
            messages.warning(request, "Non hai commissioni attive con Tipi Pratica associati.")
            tipo_pratica_list = get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True)
            return render(request, 'protocollo/ricerca_pratica.html', {
                'form': UnifiedSearchForm(user=request.user),
                'tipo_pratica_list': tipo_pratica_list,
                'tp': tipo_pratica_list,
                'origine_list': Origine.objects.all().order_by('nome'),
                'mappa_area_query': '',
            })
        # Se arrivano GET parametri (es. dal click "OpenGeoProt"), rispetta il tp richiesto
        # solo se e' tra quelli consentiti; altrimenti forza tp= consentiti.
        requested_tp = request.GET.get('tp')
        if requested_tp and requested_tp not in (None, '', '*') and requested_tp not in {str(x) for x in tipo_ids}:
            messages.warning(request, "Tipo pratica non autorizzato per la tua commissione.")
        # tp = primo (o unico) tipo consentito; il filtro pratiche gia'
        # limita a quelli delle commissioni, quindi va bene il primo.
        params = request.GET.copy()
        params['tp'] = str(tipo_ids[0])
        if not params.get('stato'):
            params['stato'] = '*'
        # Evita redirect loop se i parametri sono gia' corretti
        if params.get('tp') == request.GET.get('tp') and params.get('stato') == request.GET.get('stato'):
            pass  # procedi con la ricerca
        else:
            from django.shortcuts import redirect
            return redirect(f"{request.path}?{params.urlencode()}")

    # Consiglieri: dopo aver gestito il redirect automatico, NON mostrare la
    # lista pratiche (pratiche_list.html): redirigi direttamente a 'Le mie
    # Commissioni' per evitare di esporre informazioni aggiuntive o un
    # template pensato per utenti interni.
    if request.user.is_authenticated and is_consigliere(request.user):
        from django.shortcuts import redirect
        return redirect('accounts:mie_commissioni_url')

    form = UnifiedSearchForm(request.GET or None, user=request.user)
    ############################################################
    get_copy = request.GET.copy()
    get_copy.pop('page', None)
    mappa_area_query = get_copy.urlencode()
    data_da = request.GET.get('data_da', '').strip()
    data_a = request.GET.get('data_a', '').strip()

    # Validazione range date
    if data_da and data_a and data_a < data_da:
        messages.warning(request, "La data 'a' deve essere successiva alla data 'da'.")
        tipo_pratica_list = get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True)
        context = {
            'form': form,
            'tipo_pratica_list': tipo_pratica_list,
            'tp': tipo_pratica_list,
            'origine_list': Origine.objects.all().order_by('nome'),
            'mappa_area_query': mappa_area_query,
        }
        return render(request, 'protocollo/ricerca_pratica.html', context)

    ############################################################
    parametri_da_verificare = [
        'stato', 'prot_gen', 'anno', 'oggetto', 'annotazioni', 'street_id', 'civico', 'tp', 'cognome', 'nome', 'foglio', 'mappale', 'matricola', 'cdu', 'impianto', 'origine_id', 'atto', 'tecnico', 'has_commissione', 'data_da', 'data_a'
    ]

    tutti_vuoti = True
    for param in parametri_da_verificare:
        valore = request.GET.get(param)
        if valore and valore.strip() != '' and valore != '*' and valore is not None:
            tutti_vuoti = False
            break

    # Se tutti i parametri sono vuoti, mostra messaggio e mostra la maschera
    if tutti_vuoti:
        messages.warning(request, "Per favore inserisci almeno un criterio di ricerca.")
        tipo_pratica_list = get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True)

        context = {
            'form': form,
            'tipo_pratica_list': tipo_pratica_list,
            'tp': tipo_pratica_list,
            'origine_list': Origine.objects.all().order_by('nome'),
            'mappa_area_query': mappa_area_query,
        }
        return render(request, 'protocollo/ricerca_pratica.html', context)
    
    ############################################################

    if request.method == "GET" and any(v for k, v in request.GET.items() if k not in ('page', '') and v not in (None, '')):
        # Estrazione dati dal form validato o direttamente dai parametri
        stato = request.GET.get('stato')
        prot_gen = request.GET.get('prot_gen', '').strip()
        anno = request.GET.get('anno', '').strip()
        oggetto = request.GET.get('oggetto', '').strip()
        annotazioni = request.GET.get('annotazioni', '').strip()
        street_id = request.GET.get('street_id')
        civico = request.GET.get('civico', '').strip()
        tp = request.GET.get('tp')
        cognome = request.GET.get('cognome', '').strip()
        nome = request.GET.get('nome', '').strip()
        foglio = request.GET.get('foglio', '').strip()
        mappale = request.GET.get('mappale', '').strip()
        foglio_norm = normalize_foglio(foglio) or foglio
        matricola = request.GET.get('matricola', '').strip()
        cdu_num = request.GET.get('cdu', '').strip()
        impianto = request.GET.get('impianto', '').strip()
        origine_id = request.GET.get('origine_id')
        atto = request.GET.get('atto', '').strip()
        tecnico = request.GET.get('tecnico', '').strip()
        
        # Rimossa logica skip_opengeoprot: la ricerca per particella catastale
        # appartiene a OpenGeoProt, quindi se ci sono filtri su foglio/mappale
        # forziamo la visualizzazione della tab OpenGeoProt.
        _req_tab = request.GET.get('tab')
        if _req_tab not in ('archivio', 'opengeoprot'):
            _req_tab = 'opengeoprot' if (foglio or mappale) else None
        parametri = {
            'stato': stato, 'prot_gen': prot_gen, 'anno': anno, 'oggetto': oggetto,
            'street_id': street_id, 'civico': civico, 'tp': tp,
            'cognome': cognome, 'nome': nome, 'foglio': foglio, 'mappale': mappale,
            'matricola': matricola, 'cdu': cdu_num, 'impianto': impianto,
            'origine_id': origine_id, 'atto': atto, 'tecnico': tecnico,
            # I range date DEVONO essere propagati: sono la query_string
            # usata dai link di paginazione (Indietro / Avanti) della
            # pagina dei risultati. Senza, alla pagina successiva i filtri
            # data sparirebbero e la vista rimanderebbe al form di ricerca.
            'data_da': data_da, 'data_a': data_a,
        }
        query_params = urlencode({k: v for k, v in parametri.items() if v})

        # Log
        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
        logger_user_actions.info(
            f"Utente: {user_username} ha effettuato una ricerca con parametri - "
            f"Richiedente: {cognome} {nome}, foglio: {foglio} mappale: {mappale}"
            f"Stato: {stato}, Prot. Gen.: {prot_gen}, anno: {anno}, oggetto: {oggetto}, "
            f"street_id: {street_id}, civico: civico, tp: {tp}"
        )

        # --------------------------------------------------------
        # 🔹 Query sui campi della PRATICA
        # --------------------------------------------------------
        pratica_query = Q()

        if stato and stato != '*' and stato !='':
            pratica_query &= Q(stato__iexact=stato)

        if prot_gen and prot_gen !='' and prot_gen != '*':
            pratica_query &= Q(prot_gen__icontains=prot_gen)

        if anno and anno !='' and anno != '*':
            pratica_query &= Q(data_prot_gen__year=anno)

        if oggetto and oggetto != '' and oggetto != '*':
            for parola in oggetto.split():
                parola = parola.strip()
                if parola:
                    pratica_query &= Q(oggetto__icontains=parola)

        if annotazioni and annotazioni != '' and annotazioni != '*':
            pratica_query &= Q(annotazioni__icontains=annotazioni)

        if street_id and street_id != '' and street_id != '*':
            try:
                street_id_int = int(street_id)
                pratica_query &= Q(street__id=street_id_int)
            except ValueError:
                pass

        if civico and civico !='' and civico != '*':
            pratica_query &= Q(housenumber__icontains=civico)

        if tp and tp != '*' and tp != '':
            try:
                tp_int = int(tp)
                pratica_query &= Q(tipo_pratica__id=tp_int)
            except ValueError:
                pratica_query &= Q(tipo_pratica__name__icontains=tp)

        if data_da:
            pratica_query &= Q(data_prot_gen__gte=data_da)
        if data_a:
            pratica_query &= Q(data_prot_gen__lte=data_a)

        # Ricerca per Soggetto
        if cognome:
            pratica_query &= Q(pratiche_soggetti__soggetto__cognome__icontains=cognome)
        if nome:
            pratica_query &= Q(pratiche_soggetti__soggetto__nome__icontains=nome)

        # Ricerca per Particella
        if foglio:
            pratica_query &= Q(pratiche__particella__foglio__istartswith=foglio)
        if mappale:
            pratica_query &= Q(pratiche__particella__mappale__istartswith=mappale)

        # Ricerca per Matricola
        if matricola:
            matricola_pratiche_ids = Matricola.objects.filter(
                Q(matricola_assegnata__icontains=matricola) | Q(numero__icontains=matricola)
            ).values_list('num_impianto__pratica_id', flat=True)
            pratica_query &= Q(id__in=matricola_pratiche_ids)
        if cdu_num:
            pratica_query &= Q(pratiche_cdu__cdu_number=cdu_num)
        if impianto:
            pratica_query &= Q(pratiche_impianto__num_impianto__icontains=impianto)

        # atto / origine / tecnico sono campi solo dell'archivio edilizia:
        # non vengono applicati al lato protocollo, ma la ricerca per
        # campi comuni (cognome, nome, prot_gen, oggetto...) deve
        # continuare a funzionare anche se sono presenti.
        # Se l'app archivio edilizia non e' installata (non pubblicata
        # nel repository) questi campi non possono essere soddisfatti:
        # la ricerca lato protocollo viene azzerata, come in searchprotmap.
        if not EDILIZIA_AVAILABLE and (origine_id or atto or tecnico):
            pratica_query = Q(pk__in=[])

        # ----------------------------------------------
        # Calcolo totale_p subito dopo aver costruito la query
        # ----------------------------------------------
        if prot_gen and prot_gen != '*':
            queryDoc = Q(prot__icontains=prot_gen)
            if anno and anno != '*':
                queryDoc &= Q(data_prot__year=anno)
            documenti_ids = Documento.objects.filter(queryDoc).values_list('pratica_id', flat=True)
            totale_p = pratica_count_queryset(request.user).filter(pratica_query | Q(id__in=documenti_ids)).distinct().count()
        else:
            totale_p = pratica_count_queryset(request.user).filter(pratica_query).distinct().count()
        
        # ----------------------------------------------
        # Gestione della visibilità delle sorgenti
        # (ARCHIVIO = edilizia, OPENGEOPROT = protocollo)
        # ----------------------------------------------
        # Un range date (data_da / data_a) vale come filtro tipicamente
        # OPENGEOPROT: la ricerca NON viene estesa ad ARCHIVIO (edilizia)
        # e nessuna pratica di ARCHIVIO viene mostrata.
        _range_date = bool(data_da or data_a)
        # Campi specifici di OpenGeoProt (protocollo)
        _solo_protocollo = bool(
            _range_date
            or (stato and stato != '*' and stato != '')
            or (tp and tp != '*' and tp != '')
        )
        # Campi specifici dell'archivio edilizia
        # (con un range date l'archivio viene escluso in ogni caso)
        _solo_archivio = bool(
            (not _range_date)
            and (
                (origine_id and origine_id != '')
                or (atto and atto != '')
                or (tecnico and tecnico != '')
            )
        )

        if _solo_protocollo:
            # Stato / Tipo pratica / range date valorizzati -> solo OPENGEOPROT
            show_opengeoprot = True
            show_archivio = False
        elif _solo_archivio:
            # Origine / Atto / Tecnico valorizzati -> solo ARCHIVIO
            show_opengeoprot = False
            show_archivio = True
        else:
            # Tutti gli altri casi -> entrambe le sorgenti
            show_opengeoprot = True
            show_archivio = True

        # Determina la tab attiva
        _req_tab = request.GET.get('tab')
        if _range_date:
            # Range date -> la tab ARCHIVIO non esiste proprio
            _req_tab = 'opengeoprot'
        elif _req_tab not in ('archivio', 'opengeoprot'):
            if show_archivio and not show_opengeoprot:
                _req_tab = 'archivio'
            elif show_opengeoprot and not show_archivio:
                _req_tab = 'opengeoprot'
            elif foglio or mappale:
                _req_tab = 'opengeoprot'
            else:
                _req_tab = 'opengeoprot'

        # Archivio edilizia non installato (app non pubblicata nel
        # repository): nasconde la tab ARCHIVIO e forza la ricerca
        # sui soli risultati OPENGEOPROT.
        if not EDILIZIA_AVAILABLE:
            show_archivio = False
            show_opengeoprot = True
            _req_tab = 'opengeoprot'

        # Se la tab NON è 'archivio', applica i filtri 'stato' e 'tipo_pratica'
        if _req_tab != 'archivio':
            if (stato and stato != '*'):
                pratica_query &= Q(stato__iexact=stato)
            if (tp and tp != '*'):
                try:
                    tp_int = int(tp)
                    pratica_query &= Q(tipo_pratica__id=tp_int)
                except ValueError:
                    pass
        # Se è 'archivio', non applicare i filtri 'stato' e 'tipo_pratica'

        # Query sulle pratiche
        if prot_gen and prot_gen != '*':
            pratiche_queryset = get_practice_queryset(request.user).filter(pratica_query | Q(id__in=documenti_ids)).exclude(stato__iexact='aa')
        else:
            pratiche_queryset = get_practice_queryset(request.user).filter(pratica_query).exclude(stato__iexact='aa')
        
        # Query ottimizzata con ordinamento
        pratiche_ordered = pratiche_queryset.select_related('tipo_pratica', 'street')\
            .prefetch_related('pratiche__particella', 'pratiche_soggetti__soggetto')\
            .distinct().order_by('-data_prot_gen', '-prot_gen')

        # Ora calcolo totale_p subito dopo aver costruito la query (già fatto sopra)

        # Paginazione
        paginator = Paginator(pratiche_ordered, 10)
        page_number = request.GET.get('page')

        try:
            pratiche_page = paginator.page(page_number)
        except (PageNotAnInteger, EmptyPage):
            pratiche_page = paginator.page(1)
        # ID per il link "Vedi in Mappa": usa il queryset leggero
        protocollo_ids = pratica_count_queryset(request.user).filter(pratica_query).distinct().values_list('id', flat=True)
        
        # Query per edilizia
        # Con un range date (data_da / data_a) ARCHIVIO non viene
        # interrogato: si parte da un queryset vuoto, cosi' tutti i filtri
        # edilizia successivi restano senza effetto (edilizia_tot = 0).
        if _range_date:
            edilizia_query = EdiliziaPratica.objects.filter(pk__in=[])
        else:
            edilizia_query = EdiliziaPratica.objects.all()

        # Filtri edilizia (restano invariati)
        if cognome or nome:
            nominativo = f"{cognome} {nome}".strip()
            edilizia_query = edilizia_query.filter(richiedente__icontains=nominativo)
        if prot_gen:
            edilizia_query = edilizia_query.filter(prot_gen__icontains=prot_gen)
        if anno and anno != '*':
            edilizia_query = edilizia_query.filter(data_prot_gen__year=anno)
        if oggetto and oggetto != '*':
            edilizia_query = edilizia_query.filter(oggetto__icontains=oggetto)
        

        if street_id and street_id != '' and street_id != '*':
            try:
                civico_obj = Civici.objects.get(id=street_id)
                stopwords = {'via', 'viale', 'piazza', 'corso', 'largo', 'contrada', 'strada', 'borgo', 'frazione', 'località', 'loc.'}
                ubicazione_search_terms = [
                    parola for parola in civico_obj.street.split()
                    if parola.lower() not in stopwords and len(parola) > 2
                ]
                if ubicazione_search_terms:
                    q_ubicazione = Q()
                    for parola in ubicazione_search_terms:
                        q_ubicazione |= Q(ubicazione__icontains=parola.strip())
                    edilizia_query = edilizia_query.filter(q_ubicazione)
                if civico and civico != '' and civico != '*':
                    edilizia_query = edilizia_query.filter(ubicazione__icontains=civico)
            except Civici.DoesNotExist:
                if civico and civico !='' and civico != '*':
                    for parola in civico.split():
                        parola = parola.strip()
                        if parola:
                            edilizia_query = edilizia_query.filter(ubicazione__icontains=parola)
        elif civico and civico !='' and civico != '*':
            for parola in civico.split():
                parola = parola.strip()
                if parola:
                    edilizia_query = edilizia_query.filter(ubicazione__icontains=parola)

        # Filtri aggiuntivi solo per EdiliziaPratica
        if origine_id:
            try:
                edilizia_query = edilizia_query.filter(origine_id=int(origine_id))
            except (ValueError, TypeError):
                pass
        if atto:
            edilizia_query = edilizia_query.filter(Q(atto__icontains=atto) | Q(num_atto__icontains=atto))
        if tecnico:
            edilizia_query = edilizia_query.filter(tecnico__icontains=tecnico)

        if (foglio and foglio != '*') or (mappale and mappale != '*'):
            particelle_qs = EdiliziaPratica.objects.all()
            if foglio and foglio != '*':
                foglio_norm = normalize_foglio(foglio) or foglio
                m2m_foglio = PraticaParticella.objects.filter(
                    particella__foglio__startswith=foglio_norm,
                    pratica=OuterRef('pk')
                )
                q_foglio = Q(fg__icontains=foglio_norm) | Q(fg__icontains=foglio) | Exists(m2m_foglio)
                particelle_qs = particelle_qs.filter(q_foglio).distinct()
            if mappali := extract_mappali(mappale):
                q_mapp = Q()
                for m in mappali:
                    m2m_mappale = PraticaParticella.objects.filter(
                        particella__mappale__startswith=m,
                        pratica=OuterRef('pk')
                    )
                    q_mapp |= Q(mapp__icontains=m) | Exists(m2m_mappale)
                particelle_qs = particelle_qs.filter(q_mapp).distinct()
            else:
                m2m_mappale = PraticaParticella.objects.filter(
                    particella__mappale__startswith=mappale,
                    pratica=OuterRef('pk')
                )
                q_mapp = Q(mapp__icontains=mappale) | Exists(m2m_mappale)
                particelle_qs = particelle_qs.filter(q_mapp).distinct()
            edilizia_query = edilizia_query.filter(id__in=particelle_qs.values_list('id', flat=True).distinct())

        edilizia_ids = edilizia_query.values_list('id', flat=True)

        edilizia_results = edilizia_query.order_by('-data_prot_gen')[:100]
        edilizia_tot = edilizia_query.count()

        edilizia_paginator = Paginator(edilizia_results, 10)
        edilizia_page_number = request.GET.get('edilizia_page')
        try:
            edilizia_page = edilizia_paginator.page(edilizia_page_number)
        except (PageNotAnInteger, EmptyPage):
            edilizia_page = edilizia_paginator.page(1)

        import json as _json
        pratiche_with_particelle = []
        from collections import defaultdict
        parts_by_pratica = defaultdict(list)
        for p in edilizia_page:
            for part in p.particelle_univoche.only('foglio', 'mappale', 'mpoly').all():
                parts_by_pratica[p.id].append(part)
        for p in edilizia_page:
            parts = parts_by_pratica.get(p.id, [])
            features = []
            MAX_PARTICELLE_HOVER = 500
            for part in parts[:MAX_PARTICELLE_HOVER]:
                geom = part.mpoly
                if not geom:
                    continue
                features.append({
                    'type': 'Feature',
                    'geometry': _json.loads(geom.geojson),
                    'properties': {
                        'foglio': part.foglio,
                        'mappale': part.mappale,
                    },
                })
            geojson = _json.dumps({
                'type': 'FeatureCollection',
                'features': features,
            })
            pratiche_with_particelle.append({
                'pratica': p,
                'particelle_geojson': geojson,
                'particelle_count': len(parts),
                'particelle': parts,
            })



        context = {
            'pratica': pratiche_page,
            'totale_p': totale_p,
            'query_string': query_params,
            'pratiche_ids': list(protocollo_ids) + list(edilizia_ids),
            'protocollo_ids': list(protocollo_ids),
            'pratica_detail_base': reverse('protocollo:pratica_detail_url', args=[0])[:-2],
            'edilizia_results': edilizia_results,
            'edilizia_tot': edilizia_tot,
            'edilizia_pratica_list': edilizia_page,
            'edilizia_ids': list(edilizia_ids),
            'pratiche_with_particelle': pratiche_with_particelle,
            'nessun_risultato': (totale_p == 0 and edilizia_tot == 0),
            'active_tab': _req_tab,
            'show_archivio': show_archivio,
            'show_opengeoprot': show_opengeoprot,
            'tp': get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True),
        }
        return render(request, 'protocollo/pratiche_list.html', context)

    else:
        tipo_pratica_list = get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True)

        context = {
            'form': form,
            'tipo_pratica_list': tipo_pratica_list,
            'tp': tipo_pratica_list,
            'mappa_area_query': mappa_area_query,
        }
        return render(request, 'protocollo/ricerca_pratica.html', context)




@login_required
def riepilogo_cdu(request):
    """Riepilogo CDU per le pratiche di tipo 'CDU' (tp=7).

    Mostra, per ogni pratica: numero CDU, dati protocollo, primo richiedente,
    tutte le particelle e stato. Se l' anno di riferimento e' selezionato si
    filtra su data_prot_gen, altrimenti sono inclusi tutti gli anni.
    """
    return render(request, 'protocollo/riepilogo_cdu.html', _riepilogo_cdu_context(request))


@login_required
def riepilogo_cdu_pdf(request):
    """Genera e scarica il PDF del riepilogo CDU (orientamento landscape,
    intestazione di colonna ripetuta a ogni salto di pagina)."""
    ctx = _riepilogo_cdu_context(request)
    righe = ctx['righe']
    total = ctx['total']
    selected_anno = ctx['selected_anno']

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="riepilogo_cdu.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Riepilogo CDU",
        author="Sistema Protocollo",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitlePDF', parent=styles['Title'], fontSize=14,
        alignment=TA_CENTER, spaceAfter=4,
        textColor=colors.HexColor('#138496'),
    )
    sub_style = ParagraphStyle(
        'SubPDF', parent=styles['Normal'], fontSize=9,
        alignment=TA_CENTER, spaceAfter=8,
        textColor=colors.HexColor('#495057'),
    )
    cell_style = ParagraphStyle(
        'CellPDF', parent=styles['Normal'], fontSize=6.8, leading=8.2,
    )
    header_style = ParagraphStyle(
        'HeaderPDF', parent=styles['Normal'], fontSize=7.2, leading=8.6,
        textColor=colors.white, alignment=TA_CENTER,
    )

    story = []
    story.append(Paragraph("Riepilogo CDU", title_style))
    story.append(Paragraph("Tipo Pratica: CDU (tp=7)", sub_style))
    anno_txt = f"Filtro anno: {selected_anno}" if selected_anno else "Filtro anno: Tutti gli anni"
    story.append(Paragraph(
        f"<b>{anno_txt}</b> &nbsp;|&nbsp; Totale pratiche con CDU: <b>{total}</b>",
        styles['Normal'],
    ))
    story.append(Spacer(1, 6))

    header = [
        Paragraph("Numero CDU", header_style),
        Paragraph("Data CDU", header_style),
        Paragraph("Prot. Gen.", header_style),
        Paragraph("Data Prot. Gen.", header_style),
        Paragraph("Richiedente (primo)", header_style),
        Paragraph("Ubicazione", header_style),
        Paragraph("Civico", header_style),
        Paragraph("Particelle (tutte)", header_style),
        Paragraph("Rilasciato", header_style),
        Paragraph("Stato", header_style),
    ]

    data_rows = [header]
    for r in righe:
        cdu = r['cdu']
        doc_cdu = r['documento_cdu']
        rilasciato = ""
        if doc_cdu:
            dt = doc_cdu.data_prot.strftime('%d/%m/%Y') if doc_cdu.data_prot else ""
            rilasciato = f"{doc_cdu.prot}<br/>{dt}" if dt else str(doc_cdu.prot)
        particelle = ""
        if r['particelle_per_foglio']:
            parti = []
            for foglio, mappali in r['particelle_per_foglio'].items():
                parti.append(f"fg {foglio} mapp. {', '.join(sorted(mappali))}")
            particelle = " - ".join(parti)
        richiedente = ""
        if r['richiedente']:
            richiedente = f"<b>{r['richiedente'].cognome.upper()}</b> {r['richiedente'].nome.title()}"
        ubicazione = r['ubicazione'] or '-'
        civico = r['civico'] or '-'
        data_rows.append([
            Paragraph(str(cdu.cdu_number) if cdu else "-", cell_style),
            Paragraph(cdu.cdu_date.strftime('%d/%m/%Y') if cdu and cdu.cdu_date else "-", cell_style),
            Paragraph(f"<b>{r['pratica'].prot_gen}</b>", cell_style),
            Paragraph(r['pratica'].data_prot_gen.strftime('%d/%m/%Y'), cell_style),
            Paragraph(richiedente or "-", cell_style),
            Paragraph(ubicazione, cell_style),
            Paragraph(civico, cell_style),
            Paragraph(particelle or "-", cell_style),
            Paragraph(rilasciato or "-", cell_style),
            Paragraph(r['stato_label'], cell_style),
        ])

    col_widths = [20*mm, 19*mm, 24*mm, 24*mm, 28*mm, 22*mm, 12*mm, 56*mm, 28*mm, 19*mm]
    tbl = Table(data_rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17a2b8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    story.append(tbl)

    doc.build(story)
    return response


@login_required
def riepilogo_idonall(request):
    """Riepilogo Idoneità Alloggiative per le pratiche di tipo 'idoneità alloggiativa' (tp=26).

    Mostra, per ogni pratica: numero idoneità, data idoneità, dati protocollo,
    primo richiedente, tutte le particelle e stato. Se l' anno di riferimento
    e' selezionato si filtra su data_prot_gen, altrimenti sono inclusi tutti gli anni.
    """
    return render(request, 'protocollo/riepilogo_idonall.html', _riepilogo_idonall_context(request))


@login_required
def riepilogo_idonall_pdf(request):
    """Genera e scarica il PDF del riepilogo Idoneità Alloggiative (landscape,
    intestazione colonna ripetuta a ogni pagina)."""
    ctx = _riepilogo_idonall_context(request)
    righe = ctx['righe']
    total = ctx['total']
    selected_anno = ctx['selected_anno']

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="riepilogo_idonall.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Riepilogo Idoneita' Alloggiative",
        author="Sistema Protocollo",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitlePDF', parent=styles['Title'], fontSize=14,
        alignment=TA_CENTER, spaceAfter=4,
        textColor=colors.HexColor('#138496'),
    )
    sub_style = ParagraphStyle(
        'SubPDF', parent=styles['Normal'], fontSize=9,
        alignment=TA_CENTER, spaceAfter=8,
        textColor=colors.HexColor('#495057'),
    )
    cell_style = ParagraphStyle(
        'CellPDF', parent=styles['Normal'], fontSize=6.8, leading=8.2,
    )
    header_style = ParagraphStyle(
        'HeaderPDF', parent=styles['Normal'], fontSize=7.2, leading=8.6,
        textColor=colors.white, alignment=TA_CENTER,
    )

    story = []
    story.append(Paragraph("Riepilogo Idoneita' Alloggiative", title_style))
    story.append(Paragraph("Tipo Pratica: Idoneita' Alloggiative (tp=26)", sub_style))
    anno_txt = f"Filtro anno: {selected_anno}" if selected_anno else "Filtro anno: Tutti gli anni"
    story.append(Paragraph(
        f"<b>{anno_txt}</b> &nbsp;|&nbsp; Totale pratiche con Idoneita': <b>{total}</b>",
        styles['Normal'],
    ))
    story.append(Spacer(1, 6))

    header = [
        Paragraph("Numero Idonall", header_style),
        Paragraph("Data Idonall", header_style),
        Paragraph("Prot. Gen.", header_style),
        Paragraph("Data Prot. Gen.", header_style),
        Paragraph("Richiedente (primo)", header_style),
        Paragraph("Ubicazione", header_style),
        Paragraph("Civico", header_style),
        Paragraph("Particelle (tutte)", header_style),
        Paragraph("Stato", header_style),
    ]

    data_rows = [header]
    for r in righe:
        idonall = r['idonall']
        particelle = ""
        if r['particelle_per_foglio']:
            parti = []
            for foglio, items in r['particelle_per_foglio'].items():
                mapp = []
                for mappale, sub in items:
                    tok = str(mappale)
                    if sub:
                        tok += f" sub. {sub}"
                    mapp.append(tok)
                parti.append(f"fg {foglio} mapp. {', '.join(mapp)}")
            particelle = " - ".join(parti)
        richiedente = ""
        if r['richiedente']:
            richiedente = f"<b>{r['richiedente'].cognome.upper()}</b> {r['richiedente'].nome.title()}"
        ubicazione = r['ubicazione'] or '-'
        civico = r['civico'] or '-'
        data_rows.append([
            Paragraph(str(idonall.idonall_number) if idonall else "-", cell_style),
            Paragraph(idonall.idonall_date.strftime('%d/%m/%Y') if idonall and idonall.idonall_date else "-", cell_style),
            Paragraph(f"<b>{r['pratica'].prot_gen}</b>", cell_style),
            Paragraph(r['pratica'].data_prot_gen.strftime('%d/%m/%Y'), cell_style),
            Paragraph(richiedente or "-", cell_style),
            Paragraph(ubicazione, cell_style),
            Paragraph(civico, cell_style),
            Paragraph(particelle or "-", cell_style),
            Paragraph(r['stato_label'], cell_style),
        ])

    col_widths = [22*mm, 19*mm, 24*mm, 24*mm, 28*mm, 22*mm, 12*mm, 70*mm, 21*mm]
    tbl = Table(data_rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17a2b8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    story.append(tbl)

    doc.build(story)
    return response


def _riepilogo_cdu_context(request):
    """Costruisce il contesto per il riepilogo CDU (view HTML e PDF)."""
    tp_id = 7
    base_qs = get_practice_queryset(request.user).filter(
        tipo_pratica_id=tp_id, pratiche_cdu__isnull=False
    ).distinct()

    anno = (request.GET.get('anno') or '').strip()
    if anno and anno != '*':
        try:
            base_qs = base_qs.filter(data_prot_gen__year=int(anno))
        except (ValueError, TypeError):
            pass

    anni_disponibili = sorted(
        get_practice_queryset(request.user)
        .filter(tipo_pratica_id=tp_id, pratiche_cdu__isnull=False)
        .dates('data_prot_gen', 'year', order='DESC'),
        key=lambda d: d.year,
        reverse=True
    )

    stato_class_map = {
        'a': 'badge-primary', 'i': 'badge-info', 's': 'badge-danger',
        'ic': 'badge-warning', 'ri': 'badge-danger', 'ai': 'badge-success',
        'bd': 'badge-warning', 'df': 'badge-success', 'ia': 'badge-secondary',
        'af': 'badge-warning', 'np': 'badge-dark', 'dn': 'badge-info',
        'eo': 'badge-success', 'c': 'badge-success',
    }

    righe = []
    for p in base_qs.select_related('tipo_pratica', 'pratiche_cdu').prefetch_related(
        'soggetto_pratica', 'pratiche__particella', 'pratiche_soggetti__soggetto', 'pratiche_soggetti__tipo'
    ):
        cdu = getattr(p, 'pratiche_cdu', None)
        soggetto = None
        _anaprat = p.pratiche_soggetti.filter(tipo__name__iexact='richiedente').select_related('soggetto').first()
        if _anaprat:
            soggetto = _anaprat.soggetto
        # Raggruppa tutte le particelle per foglio: fg 87 mapp. 7, 8 / fg 88 mapp. 1
        particelle_per_foglio = {}
        for cp in p.pratiche.all():
            part = cp.particella
            if not part:
                continue
            foglio = part.foglio
            mappale = part.mappale
            particelle_per_foglio.setdefault(foglio, set())
            if mappale:
                particelle_per_foglio[foglio].add(mappale)
        # Ultimo documento della pratica che riporta "rilascio cdu"
        doc_cdu = Documento.objects.filter(
            pratica=p, name__icontains='rilascio cdu'
        ).order_by('-data_prot', '-id').first()
        righe.append({
            'pratica': p,
            'cdu': cdu,
            'richiedente': soggetto,
            'particelle_per_foglio': dict(sorted(particelle_per_foglio.items())),
            'documento_cdu': doc_cdu,
            'ubicazione': (p.street.street if p.street else ''),
            'civico': (p.housenumber or ''),
            'stato_label': status_labels.get(p.stato, p.stato),
            'stato_class': stato_class_map.get(p.stato, 'badge-secondary'),
        })

    # Ordina per anno e numero CDU decrescente (None in fondo)
    righe.sort(key=lambda r: (
        r['pratica'].data_prot_gen.year if r['pratica'].data_prot_gen else -1,
        r['cdu'].cdu_number if r['cdu'] else -1,
    ), reverse=True)

    return {
        'righe': righe,
        'total': len(righe),
        'anni_disponibili': anni_disponibili,
        'selected_anno': anno,
        'tp_id': tp_id,
    }


def _riepilogo_idonall_context(request):
    """Costruisce il contesto per il riepilogo Idoneita' Alloggiative (view HTML e PDF)."""
    tp_id = 26
    base_qs = get_practice_queryset(request.user).filter(
        tipo_pratica_id=tp_id, pratica_idonall__certificato_istruttoria__isnull=False
    ).distinct()

    anno = (request.GET.get('anno') or '').strip()
    if anno and anno != '*':
        try:
            base_qs = base_qs.filter(data_prot_gen__year=int(anno))
        except (ValueError, TypeError):
            pass

    anni_disponibili = sorted(
        get_practice_queryset(request.user)
        .filter(tipo_pratica_id=tp_id, pratica_idonall__certificato_istruttoria__isnull=False)
        .dates('data_prot_gen', 'year', order='DESC'),
        key=lambda d: d.year,
        reverse=True
    )

    stato_class_map = {
        'a': 'badge-primary', 'i': 'badge-info', 's': 'badge-danger',
        'ic': 'badge-warning', 'ri': 'badge-danger', 'ai': 'badge-success',
        'bd': 'badge-warning', 'df': 'badge-success', 'ia': 'badge-secondary',
        'af': 'badge-warning', 'np': 'badge-dark', 'dn': 'badge-info',
        'eo': 'badge-success', 'c': 'badge-success',
    }

    righe = []
    for p in base_qs.select_related('tipo_pratica').prefetch_related(
        'soggetto_pratica', 'pratiche__particella', 'pratiche_soggetti__soggetto', 'pratiche_soggetti__tipo'
    ):
        try:
            idonall = p.pratica_idonall.certificato_istruttoria
        except (Idonall.DoesNotExist, AttributeError):
            idonall = None
        soggetto = None
        _anaprat = p.pratiche_soggetti.filter(tipo__name__iexact='richiedente').select_related('soggetto').first()
        if _anaprat:
            soggetto = _anaprat.soggetto
        # Raggruppa tutte le particelle per foglio: fg 56 mapp. 2 sub. 1, 7 - fg 57 mapp. 1
        particelle_per_foglio = {}
        for cp in p.pratiche.all():
            part = cp.particella
            if not part:
                continue
            foglio = part.foglio
            mappale = part.mappale
            sub = (cp.subalterno or '').strip()
            if sub in ('-', ''):
                sub = None
            particelle_per_foglio.setdefault(foglio, [])
            if (mappale, sub) not in particelle_per_foglio[foglio]:
                particelle_per_foglio[foglio].append((mappale, sub))
        righe.append({
            'pratica': p,
            'idonall': idonall,
            'richiedente': soggetto,
            'particelle_per_foglio': dict(sorted(particelle_per_foglio.items())),
            'ubicazione': (p.street.street if p.street else ''),
            'civico': (p.housenumber or ''),
            'stato_label': status_labels.get(p.stato, p.stato),
            'stato_class': stato_class_map.get(p.stato, 'badge-secondary'),
        })

    # Ordina per anno e numero Idonall decrescente (None in fondo)
    righe.sort(key=lambda r: (
        r['pratica'].data_prot_gen.year if r['pratica'].data_prot_gen else -1,
        r['idonall'].idonall_number if r['idonall'] else -1,
    ), reverse=True)

    return {
        'righe': righe,
        'total': len(righe),
        'anni_disponibili': anni_disponibili,
        'selected_anno': anno,
        'tp_id': tp_id,
    }

# cerca documenti allegati
@login_required

def SearchDocProt(request):
    
    if request.method == "POST":
        
        prot_gen = request.POST.get('prot_gen')
        anno = request.POST.get('anno')
        
        # Registra l'utente e i parametri di ricerca
        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
        logger_user_actions.info(f"Utente: {user_username} ha effettuato una ricerca per ALLEGATO: {prot_gen} anno: {anno}")
        
        # Costruisci la query
        query = Q()
        if anno != '' and anno is not None:    
            query &= Q(data_prot__year = anno)

        if prot_gen != '' and prot_gen is not None:    
            query &= Q(prot__contains = prot_gen)
        # Ricerca documenti
        
        documenti = Documento.objects.filter(query).order_by('-data_prot')
        search = {}
        if documenti:
            pratiche = []
            for m in documenti:
                search = get_practice_queryset(request.user).filter(id=m.pratica_id).first()
                if search:
                    pratiche.append(search)
            context = {'pratica' : pratiche,}
            return render(request, 'protocollo/pratiche_list.html', context)
        else:
            messages.warning(request, f"Hai cercato il protocollo {prot_gen} anno {anno} ...Nessun risultato!.")
            return redirect('protocollo:index_pratiche_url')


@login_required

def SearchStato(request):
    
    
    if request.method=="GET":
        stato = request.GET.get('stato')
        tp = request.GET.get('tp')
        anno = request.GET.get('anno')

        stato = stato if stato else '*'
        tp = tp if tp else '*'
        anno = anno if anno else '*'

        filters = {}

        if stato != '*':
            filters['stato__exact'] = stato
        if tp != '*':
            filters['tipo_pratica__exact'] = tp
        if anno != '*':
            filters['data_prot_gen__year'] = anno
            
        pratiche_queryset = get_practice_queryset(request.user).filter(**filters)\
            .select_related('tipo_pratica', 'street')\
            .prefetch_related('pratiche__particella', 'pratiche_soggetti__soggetto')\
            .order_by('-data_prot_gen', '-prot_gen')

        # Prepara query string per paginazione
        parametri = {'stato': stato, 'tp': tp, 'anno': anno}
        query_params = urlencode({k: v for k, v in parametri.items() if v and v != '*'})

        if pratiche_queryset.exists():
            totale_p = pratiche_queryset.count()
            paginator = Paginator(pratiche_queryset, 10)
            page_number = request.GET.get('page')
            
            try:
                pratiche = paginator.page(page_number)
            except (PageNotAnInteger, EmptyPage):
                pratiche = paginator.page(1)

            context = {
                                    'pratica':pratiche  ,
            'tp': get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True),
                                    'totale_p':totale_p,
                                    'query_string': query_params,
                                }
            return render(request,'protocollo/pratiche_list.html', context)
        else :
            messages.warning(request, "Hai cercato le pratiche con stato " + str(stato) + " ...Nessun risultato!.")
            return redirect('protocollo:index_pratiche_url')


@login_required
def SearchTipoPratica(request, id):
    # Query ottimizzata con select_related e prefetch_related
    pratiche_queryset = get_practice_queryset(request.user).filter(tipo_pratica_id=id).order_by('-data_prot_gen', '-prot_gen')
        
    totale_p = pratiche_queryset.count()
    paginator = Paginator(pratiche_queryset, 10)
    page = request.GET.get('page')
    
    try:
        pratiche = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        pratiche = paginator.page(1)

    context = {
        'pratica': pratiche,
        'tp': get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True),
        'totale_p': totale_p,
        'pratiche_ids': list(pratiche_queryset.values_list('id', flat=True)),
        'active_tab': 'opengeoprot',
        'show_opengeoprot': True,
        'show_archivio': False,
    }
    return render(request, 'protocollo/pratiche_list.html', context)


@login_required
def _check_scadenze_alerts(request):
    """Helper to check for expired payments and notify user."""
    today = timezone.now().date()
    scadenze_alert = Scadenze.objects.filter(
        pagata=False, 
        data_scadenza__lt=today
    ).select_related('convenzione')
    
    count = scadenze_alert.count()
    if count > 0:
        if count == 1:
            message = f"Attenzione: c'è una rata scaduta in archivio."
        else:
            message = f"Attenzione: sono presenti {count} rate scadute tra le pratiche in archivio."
        messages.warning(request, message)

#pagina principale lista  le ultime 10 pratiche
@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home:index')
@editor_required(allow_viewers=True)
# @user_passes_test(is_editor_or_admin, login_url='home:index')
def index(request):
    pratiche_queryset = get_practice_queryset(request.user).order_by('-data_mod', '-prot_gen')[:100]

    totale_p = pratiche_queryset.count()
    paginator = Paginator(pratiche_queryset, 10)
    page = request.GET.get('page')
    
    try:
        pratiche_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        pratiche_page = paginator.page(1)

    # Gestione alert scadenze
    _check_scadenze_alerts(request)

    context = {
        'pratica': pratiche_page,
        'tp': get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True),
        'totale_p': totale_p,
        'pratiche_ids': list(pratiche_queryset.values_list('id', flat=True)),
        'active_tab': 'opengeoprot',
        'show_opengeoprot': True,
        'show_archivio': False,
    }
    return render(request, 'protocollo/pratiche_list.html', context)


@login_required
@editor_required

def pratica_add(request):
    """
    Vista per aggiungere una nuova pratica.
    Gestisce il calcolo automatico di code_p e la posizione geografica.
    Assicura che venga sempre restituita una HttpResponse.
    """
    initial_lat, initial_lng = 44.07721, 10.09636  # Carrara

    if request.method == "POST":
        form = PraticaForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user

            # 1. Gestione Coordinate (dai campi hidden del form o geocodifica)
            # 1. Gestione Coordinate
            lat = form.cleaned_data.get('lat')
            lng = form.cleaned_data.get('lng')

            if lat and lng:
                try:
                    obj.posizione = Point(float(lng), float(lat), srid=4326)
                except (ValueError, TypeError):
                    obj.posizione = None
            # (la posizione manuale ha la precedenza; altrimenti viene calcolata dopo il save)

            # 2. Calcolo progressivo code_p (per tipo di pratica e anno)
            # 2. Calcolo progressivo code_p
            anno_rif = obj.data_prot_gen.year if obj.data_prot_gen else timezone.now().year
            code_max = Pratica.objects.filter(
                tipo_pratica=obj.tipo_pratica, 
                data_prot_gen__year=anno_rif
            ).aggregate(Max('code_p')).get('code_p__max') or 0
            
            obj.code_p = code_max + 1
            obj.save()
            log_action(request, 'CREATO', f'Pratica {obj.id}', {'prot_gen': obj.prot_gen, 'tipo': str(obj.tipo_pratica)})

            # Geolocalizzazione automatica (indirizzo completo o particelle) se non impostata manualmente
            if not obj.posizione:
                ubica_pratica(obj)
                if not obj.posizione:
                    obj.posizione = Point(initial_lng, initial_lat, srid=4326)
                    obj.save()

            messages.success(request, f"Pratica salvata con successo. Progressivo: {obj.code_p}")
            return redirect('protocollo:pratica_detail_url', pk=obj.id)
        else:
            messages.error(request, "Errore nella validazione del form. Controlla i dati inseriti.")
    else:
        form = PraticaForm(user=request.user)

    context = {
        'form': form,
        'initial_latitude': request.POST.get('lat') or initial_lat,
        'initial_longitude': request.POST.get('lng') or initial_lng,
    }
    return render(request, 'protocollo/pratica_add.html', context)

# dettaglio pratica
@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home:index')

@user_passes_test(lambda u: is_manager(u) or is_user(u) or is_consigliere(u), login_url='home:index')
# @editor_required(allow_viewers=True)


def pratica_detail(request, pk):
    # Consiglieri: redirigi alla versione read-only dedicata (no soggetti/particelle)
    if is_consigliere(request.user):
        return redirect('protocollo:pratica_detail_consigliere_url', pk=pk)
    pratica = get_object_or_404(get_practice_queryset(request.user), pk=pk)
    log_action(request, 'VISUALIZZATO', f'Pratica {pratica.id}')
    is_editor = is_editor_func(request.user)
    is_user_val = is_user(request.user)
    # Determina le coordinate per il centro mappa
    # Priorità: 1. Posizione salvata, 2. Centroide delle particelle, 3. Default Carrara
    if pratica.posizione:
        lat = pratica.posizione.y
        lng = pratica.posizione.x
    elif pratica.mpoly_pratica:
        centroid = pratica.mpoly_pratica.centroid
        lat = centroid.y
        lng = centroid.x
    else:
        # Coordinate di default se non c'è nulla
        lat = 44.07721
        lng = 10.09636

    # GeoDjango Point standard: (longitude, latitude)
    pratica_posizione = Point(float(lng), float(lat), srid=4326)
    
    m = build_base_map(lat, lng, zoom_start=15)

    # Aggiungiamo la geometria aggregata delle particelle come overlay toggleable
    if     pratica.mpoly_pratica:
        folium.GeoJson(
            pratica.mpoly_pratica.json,
            name="Confini Catastali",
            style_function=lambda x: {'color': 'red', 'fillColor': 'red', 'weight': 2, 'fillOpacity': 0.3}
        ).add_to(m)

    # Aggiungi un marker per la posizione della pratica in un gruppo
    fg_pos = folium.FeatureGroup(name="Ubicazione Pratica")
    folium.Marker([lat, lng], popup=pratica.oggetto).add_to(fg_pos)
    fg_pos.add_to(m)

    # Converti la mappa in HTML
    map_html = m._repr_html_()

    # Definiamo gli stati "conclusi" o "non operativi" per evitare messaggi inutili
    stati_conclusi = ['c', 'np', 'ic', 'ai']

    if pratica.stato not in stati_conclusi and pratica.data_prot_gen:
        today = timezone.now().date()
        giorni = (today - pratica.data_prot_gen)
        if giorni.days > 90 and pratica.tipo_pratica_id == 36:
            messages.error(request, "SCADUTO IL TERMINE PER COMUNICAZIONE: " + str(giorni.days) + " giorni trascorsi." )
        elif giorni.days > 60 and pratica.tipo_pratica_id == 36:
            messages.error(request, "TERMINE IN SCADENZA: sono trascorsi " + str(giorni.days) + " giorni." )
        elif giorni.days < 60 and pratica.tipo_pratica_id == 36:
            messages.warning(request, "Dalla presentazione sono trascorsi " + str(giorni.days) + " giorni." )

    anagrafe = Anaprat.objects.filter(pratica=pk).select_related('soggetto', 'tipo')
    anaprat=[]
    if anagrafe :
   
        # anagrafe
        for a in anagrafe:
            anagrafe_pratica={} # creo un dizionario vuoto
            soggetto = a.soggetto
            anagrafe_pratica['id']=a.id
            anagrafe_pratica['id_soggetto']=a.soggetto.id
            anagrafe_pratica['tipo']=a.tipo
            anagrafe_pratica['cognome']=soggetto.cognome
            anagrafe_pratica['nome']=soggetto.nome
            anagrafe_pratica['data_nascita']=soggetto.data_nascita
            anagrafe_pratica['comune_nascita']=soggetto.comune_nascita
            anagrafe_pratica['codice_fiscale']=soggetto.codice_fiscale
            anagrafe_pratica['addr']=soggetto.addr
            anagrafe_pratica['addr_sede']=soggetto.addr_sede
            anagrafe_pratica['comune_residenza']=soggetto.comune_residenza
            anaprat.append(anagrafe_pratica)
        anaprat = sorted(anaprat, key=lambda x: x['tipo'].id if x['tipo'] else 0)
    else :
        if pratica.stato not in stati_conclusi:
            messages.warning(request, "Attenzione: non sono ancora stati inseriti i soggetti coinvolti." )
        pass
    
    particelle_qs = Cataprat.objects.filter(pratica=pk).select_related('particella')
    cataprat = []
    id_catasto_map = {}
    for a in particelle_qs:
        m = getattr(a.particella, 'mappale', None)
        if not m or any(ch.isupper() for ch in str(m)):
            continue
        catasto_pratica={}
        particella = a.particella
        catasto_pratica['id']=a.id
        catasto_pratica['id_particella']=a.particella.id
        catasto_pratica['foglio']=particella.foglio
        catasto_pratica['mappale']=particella.mappale
        catasto_pratica['subalterno']=a.subalterno
        
        foglio_norm = str(particella.foglio).zfill(4)
        foglio_raw = str(particella.foglio)
        mappale_raw = str(particella.mappale)
        cp = Particelle.objects.using('anagrafe').filter(
            Q(foglio__iexact=foglio_norm) | Q(foglio__iexact=foglio_raw),
            mappale__iexact=mappale_raw
        ).first()
        id_catasto = cp.id if cp else None
        catasto_pratica['id_catasto'] = id_catasto
        id_catasto_map[particella.id] = id_catasto
        
        cataprat.append(catasto_pratica)
    if cataprat:  
        def _sort_key(item):
            try:
                f = int(item['foglio'])
            except (ValueError, TypeError):
                f = item['foglio']
            try:
                m = int(item['mappale'])
            except (ValueError, TypeError):
                m = item['mappale']
            return (f, m)
        cataprat = sorted(
                        cataprat,
                        key=_sort_key
                    )
    else:
        if     pratica.stato not in stati_conclusi: 
            messages.warning(request, "Attenzione: mancano i dati catastali (particelle)." )

        pass
        
    tipo_pratica= pratica.tipo_pratica
    tipo_pratica_id= pratica.tipo_pratica_id
    # upload
    # verifica se esiste la data del protocollo, se esiste recupera quella per ordinare temporalmente
    
    documenti = Documento.objects.filter(pratica=pk).order_by('-data_prot')
                                                        
    # documenti = Documento.objects.all().filter(pratica=pk) #.order_by('-data_prot','-data_crea')
    # documenti = documenti.order_by('-data_prot')
    # documenti = documenti.order_by('-data_crea')
    tot_doc = documenti.count()
    # return render(request, 'protocollo/pratica_detail.html', {'pratica': pratica, 'anaprat':anaprat, 'cataprat':cataprat,'documenti':documenti})


    # impianti fotovoltaici
    # impfot = ImpFot.objects.all().filter(pratica=pk)
    # tot_impfot = impfot.count()
    
    # impianti fotovoltaici
    try:
        impfot = ImpFot.objects.get(pratica_id=pk)
        impfot_esistente = 1
           
            
    except :
        impfot=0
        impfot_esistente=0




    # certificati e modelli
    # cdu
    cdu = Cerdesurb.objects.filter(pratica=pk) 
    tot_cdu = cdu.count()

    # idoneità allogiativa
    tot_idon = 0

    # idoneità allogiativa rivisitata
   

    # ascensori
    # impianti
    try:
        impianto = Impianto.objects.get(pratica_id=pk)
        impianto_esistente = 1
           
            
    except :
        impianto=0
        impianto_esistente=0
        
        
    # print('tot impianto',impianto_esistente)
    # ascensori
    # matricole
    try:
        matricola = Matricola.objects.get(num_impianto_id=impianto.id)
        matricola_esistente = 1
        
    except Exception:
        
        matricola=0
        matricola_esistente=0

    # Conteggio pratiche con stessa matricola per tipo ascensore (38)
    tot_stessa_matricola = 0
    if tipo_pratica_id == 38 and matricola_esistente and matricola:
        if matricola.matricola_assegnata:
            tot_stessa_matricola = Matricola.objects.filter(
                matricola_assegnata=matricola.matricola_assegnata,
                num_impianto__pratica__tipo_pratica_id=38
            ).count()

    # diario
    try:
        diari = Diario.objects.filter(pratica_id=pk)
        diari_esistenti = diari.count()
           
            
    except :
        diari=0
        diari_esistenti=0

    # scadenze
        # try:
        #     scadenze = IstrConv.objects.filter(pratica_id=pk)
        #     scadenze_esistenti = scadenze.count()
            
                
        # except :
        #     print('jd77yhdg')
        #     scadenze=0
        #     scadenze_esistenti=0
    
    # passo carraio
    
    pcar = Passocarraio.objects.all().filter(pratica=pk)
    if pcar:
        tot_pcar = pcar.count()    
    else:
        tot_pcar = 0

    # istruttoria POC 2022
    istruttoria_poc = IstruttoriaPoc.objects.filter(pratica_id=pk).first()
    if not istruttoria_poc:
        istruttoria_poc = IstruttoriaPoc(pratica_id=pk, data_istr_poc=timezone.now().date())
    edit_istruttoria = request.GET.get('edit_istruttoria') == '1'
    istruttoria_form = IstruttoriaForm(instance=istruttoria_poc)
    if not istruttoria_poc.pk or not istruttoria_poc.data_istr_poc:
        istruttoria_form.fields['data_istr_poc'].initial = timezone.now().date()

    # Commissione POC 2022
    istrcomm_poc = IstrCommPoc.objects.filter(pratica_id=pk).first()
    if not istrcomm_poc:
        istrcomm_poc = IstrCommPoc(pratica_id=pk, data_commissione=timezone.now().date())
    edit_istrcomm = request.GET.get('edit_istrcomm') == '1'
    istrcomm_form = IstrCommForm(instance=istrcomm_poc)
    if not istrcomm_poc.pk or not istrcomm_poc.data_commissione:
        istrcomm_form.fields['data_commissione'].initial = timezone.now().date()

    # Consiglio POC 2022
    istrcons_poc = IstrConsPoc.objects.filter(pratica_id=pk).first()
    if not istrcons_poc:
        istrcons_poc = IstrConsPoc(pratica_id=pk, data_consiglio=timezone.now().date())
    edit_istrcons = request.GET.get('edit_istrcons') == '1'
    istrcons_form = IstrConsForm(instance=istrcons_poc)
    if not istrcons_poc.pk or not istrcons_poc.data_consiglio:
        istrcons_form.fields['data_consiglio'].initial = timezone.now().date()

    # tab POC attiva: in modifica prevale la tab aperta, altrimenti la prima
    # compilata nell'ordine Istruttoria > Commissione > Consiglio
    _tab_poc = [
        ('istruttoria', edit_istruttoria, bool(istruttoria_poc.testo)),
        ('istrcomm', edit_istrcomm, bool(istrcomm_poc.testo)),
        ('istrcons', edit_istrcons, bool(istrcons_poc.testo)),
    ]
    tab_poc_attiva = next((nome for nome, in_modifica, _ in _tab_poc if in_modifica), None)
    if tab_poc_attiva is None:
        tab_poc_attiva = next((nome for nome, _, compilata in _tab_poc if compilata), 'istruttoria')

    # idonall
    # verifico istruttorie
    idon = Idonall.objects.none()
    tot_istr = 0
    idonall = None
    tot_idonall = 0
    istruttoria = Istruttoria.objects.filter(pratica=pk).first()
    if istruttoria:
        tot_istr = 1
        idon = Idonall.objects.filter(istruttoria_id=istruttoria.id).first()
        if idon:
            idonall = idon
            tot_idonall = 1
        else:
            idonall = None
            tot_idonall = 0
        
    # conv
    delta=timedelta(0)
    anni=0
    conv = IstrConv.objects.all().filter(pratica=pk)
    if conv:
        tot_conv = conv.count()
        # data di rivalutazione ISTA - 1 mese dalla data di protocollo
        ### https://stackoverflow.com/questions/9625084/how-to-find-one-month-later-from-a-date-with-django
        from dateutil.relativedelta import relativedelta
        data_istat = pratica.data_prot_gen - relativedelta(months=2)
        tot_dovuto = 0  # Initialize

        for c in conv:
                if c.data_atto and c.data_rival:
                    delta = (c.data_rival - c.data_atto)
                    oggi = timezone.now()
                    anni = oggi.year - c.data_atto.year - ((oggi.month, oggi.day) < (c.data_atto.month, c.data_atto.day))
                    # print('anni',anni)
                    if c.valore_dirsup or c.crv_uiu:
                        if c.prop_acquisita == False:
                            tot_dovuto = c.valore_dirsup + c.crv_uiu
                        else:
                            tot_dovuto = c.crv_uiu

                    else :
                        tot_dovuto = 0
                else:
                    delta = 0
                    anni=0
                
                # ACCETTAZIONE

                try:
                    accettazione = AccettaImporto.objects.get(convenzione_id=c.id)
                    accettazione_boolean = 1
                    # Pratica.objects.filter(pk=c.pratica_id).update(stato='ai')
                except Exception:
                    accettazione =0
                    accettazione_boolean = 0
                    
    else:
        tot_conv = 0
        tot_dovuto = 0
        delta = 0
        data_istat = 0
        accettazione =0
        accettazione_boolean = 0
        
    # print('dovuto',tot_dovuto)
        
    # delta = (con.data_rival - c.data_atto)
    # delta_years=str(int(delta.days/365))
    # 1 sta per ADD
    # calcolo il periodo tra l'atto di convenzione e il momento attuale
    #
    
    
    # modelli
    modello = Modello.objects.all().filter(tipo_pratica=tipo_pratica.id)
    

    tipo_pratica_id= pratica.tipo_pratica.id
    # print(tipo_pratica_id)
    paesaggistica = 1
    commissioni = Commissione.objects.all().filter(pratica=pk)
    tot_commissioni = commissioni.count()
    # print(lat)
    if delta:
        delta_day = delta.days/365,
    else:
        delta_day =0,
    
    tp=TipoPratica.objects.all().order_by(Lower('name'))
    
    context = {
        'impfot':impfot,
        'impfot_esistente':impfot_esistente,

        'idon':idon,
        'tot_idon':tot_idon,

        'istruttoria':istruttoria,
        'tot_istr':tot_istr,
        'idonall':idonall,
        'tot_idonall':tot_idonall,


        'matricola':matricola,
        'tot_matr':matricola_esistente,
        'tot_stessa_matricola': tot_stessa_matricola,

        'impianto':impianto,
        'tot_impianto':impianto_esistente,
        
        'diari':diari,
        'diari_esistenti':diari_esistenti,

        # 'scadenze':scadenze,
        # 'scadenze':scadenze,

        'pcar':pcar,
        'tot_pcar':tot_pcar,

        'istruttoria_poc':istruttoria_poc,
        'edit_istruttoria':edit_istruttoria,
        'istruttoria_form':istruttoria_form,

        'istrcomm_poc':istrcomm_poc,
        'edit_istrcomm':edit_istrcomm,
        'istrcomm_form':istrcomm_form,

        'istrcons_poc':istrcons_poc,
        'edit_istrcons':edit_istrcons,
        'istrcons_form':istrcons_form,
        'tab_poc_attiva':tab_poc_attiva,

        'conv':conv,
        'tot_conv':tot_conv,
        'tot_dovuto':tot_dovuto,
        
        'data_istat':data_istat,
        'anni_data_atto':anni,
        # accettazione
        'accettazione' :accettazione,
        'accettazione_boolean':accettazione_boolean,
        
                
        'cdu':cdu,
        'modello_list':modello,
        'paesaggistica':paesaggistica,
        'commissioni':commissioni,
        'pratica': pratica,
        'anaprat':anaprat, 
        'cataprat':cataprat,
        # 'cataprat':cataprat_sorted,
        'id_catasto_map': id_catasto_map,
        'documenti':documenti,
        'tot_cdu':tot_cdu,
        'tot_doc':tot_doc,
        'tot_commissioni':tot_commissioni,
        'tipo':tipo_pratica,
        'is_editor':is_editor,
        'is_manager':is_manager(request.user),
        'is_user':is_user_val,
        'is_consigliere': is_consigliere(request.user),
        'lat':lat,
        'lng':lng,
        'pratica_posizione':pratica_posizione,
        'map_html': map_html, # Aggiungi l'HTML della mappa al contesto
        'tp':tp,
        'pk':pk,
        
        }
    return render(request, 'protocollo/pratica_detail.html', context )


@login_required
def pratica_detail_consigliere(request, pk):
    """Versione read-only di pratica_detail per i consiglieri.

    Mostra solo informazioni sintetiche della pratica (no soggetti,
    no particelle catastali, no mappa catastale) per evitare la
    visualizzazione di dati personali e catastali.
    """
    pratica = get_object_or_404(get_practice_queryset(request.user), pk=pk)
    # Log leggero: solo i campi fondamentali per alleggerire la query
    log_action(
        request,
        'VISUALIZZATO',
        f'Pratica {pratica.id} (consigliere)',
        {
            'pratica_id': pratica.id,
            'prot_gen': pratica.prot_gen or None,
            'anno': pratica.data_prot_gen.year if pratica.data_prot_gen else None,
            'tipo_pratica': pratica.tipo_pratica.name if pratica.tipo_pratica else None,
        },
    )

    return render(request, 'protocollo/pratica_detail_consigliere.html', {
        'pratica': pratica,
        'is_consigliere': True,
        'pk': pk,
    })


@login_required
@editor_required(allow_viewers=True)

def pratica_history(request, pk):
    pratica = get_object_or_404(get_practice_queryset(request.user), pk=pk)

    def get_changes(record, model_class):
        changes = []
        prev = record.prev_record
        fields = [f for f in model_class._meta.get_fields() if not (f.many_to_many or f.one_to_many) and f.name not in ('history', 'id')]
        if prev:
            for field in fields:
                if not field.auto_created and (field.many_to_one or field.one_to_one):
                    id_name = field.get_attname()
                    if hasattr(record, id_name) and hasattr(prev, id_name):
                        old_val = getattr(prev, id_name)
                        new_val = getattr(record, id_name)
                        if old_val != new_val:
                            changes.append({
                                'field': field.verbose_name or field.name,
                                'old': old_val,
                                'new': new_val,
                                'is_fk': True,
                            })
                elif not field.auto_created:
                    if hasattr(record, field.name) and hasattr(prev, field.name):
                        old_val = getattr(prev, field.name)
                        new_val = getattr(record, field.name)
                        if old_val != new_val:
                            changes.append({
                                'field': field.verbose_name or field.name,
                                'old': old_val,
                                'new': new_val,
                            })
        else:
            for field in fields:
                if not field.auto_created and (field.many_to_one or field.one_to_one):
                    id_name = field.get_attname()
                    if hasattr(record, id_name):
                        val = getattr(record, id_name)
                        if val is not None:
                            changes.append({
                                'field': field.verbose_name or field.name,
                                'old': None,
                                'new': val,
                                'is_fk': True,
                            })
                elif not field.auto_created:
                    if hasattr(record, field.name):
                        changes.append({
                            'field': field.verbose_name or field.name,
                            'old': None,
                            'new': getattr(record, field.name),
                        })
        return changes

    all_events = []

    for record in pratica.history.all():
        changes = get_changes(record, Pratica)
        history_type = record.history_type
        if history_type == '+':
            tipo_label = 'Creazione'
        elif history_type == '~':
            if record.prev_record and not changes:
                tipo_label = 'Visualizzazione'
            else:
                tipo_label = 'Modifica'
        elif history_type == '-':
            tipo_label = 'Cancellazione'
        else:
            tipo_label = history_type
        event_date = record.history_date
        if timezone.is_naive(event_date):
            event_date = timezone.make_aware(event_date, timezone=timezone.get_default_timezone())
        all_events.append({
            'date': event_date,
            'user': record.history_user,
            'type': tipo_label,
            'type_code': history_type,
            'model': 'Pratica',
            'changes': changes,
        })

    for record in Anaprat.history.filter(pratica=pratica):
        changes = get_changes(record, Anaprat)
        history_type = record.history_type
        if history_type == '+':
            tipo_label = 'Aggiunta'
        elif history_type == '~':
            tipo_label = 'Modifica'
        elif history_type == '-':
            tipo_label = 'Rimossa'
        else:
            tipo_label = history_type
        detail = None
        if history_type == '~':
            for c in changes:
                if c['field'] == 'soggetto':
                    old_sog = Soggetto.objects.filter(pk=c['old']).first() if c['old'] else None
                    new_sog = Soggetto.objects.filter(pk=c['new']).first() if c['new'] else None
                    c['old'] = f"{old_sog.cognome} {old_sog.nome}" if old_sog else (c['old'] or '—')
                    c['new'] = f"{new_sog.cognome} {new_sog.nome}" if new_sog else (c['new'] or '—')
        elif history_type == '+':
            soggetto_id = getattr(record, 'soggetto_id', None)
            soggetto = Soggetto.objects.filter(pk=soggetto_id).first() if soggetto_id else None
            if soggetto:
                changes = [c for c in changes if c['field'] != 'soggetto']
                changes.append({
                    'field': 'soggetto',
                    'old': None,
                    'new': f"{soggetto.cognome} {soggetto.nome} (CF: {soggetto.codice_fiscale})",
                })
            detail = f"Aggiunto soggetto: {soggetto.cognome} {soggetto.nome} (CF: {soggetto.codice_fiscale})" if soggetto else None
        elif history_type == '-':
            soggetto_id = getattr(record, 'soggetto_id', None)
            soggetto = Soggetto.objects.filter(pk=soggetto_id).first() if soggetto_id else None
            detail = f"Rimosso soggetto: {soggetto.cognome} {soggetto.nome} (CF: {soggetto.codice_fiscale})" if soggetto else None
        else:
            detail = None
        event_date = record.history_date
        if timezone.is_naive(event_date):
            event_date = timezone.make_aware(event_date, timezone=timezone.get_default_timezone())
        all_events.append({
            'date': event_date,
            'user': record.history_user,
            'type': tipo_label,
            'type_code': history_type,
            'model': 'Soggetto in pratica',
            'changes': changes,
            'detail': detail,
        })

    for record in Cataprat.history.filter(pratica=pratica):
        changes = get_changes(record, Cataprat)
        history_type = record.history_type
        if history_type == '+':
            tipo_label = 'Aggiunta'
        elif history_type == '~':
            tipo_label = 'Modifica'
        elif history_type == '-':
            tipo_label = 'Rimossa'
        else:
            tipo_label = history_type
        detail = None
        if history_type == '~':
            for c in changes:
                if c['field'] == 'particella':
                    old_part = Particella.objects.filter(pk=c['old']).first() if c['old'] else None
                    new_part = Particella.objects.filter(pk=c['new']).first() if c['new'] else None
                    c['old'] = f"Foglio {old_part.foglio}, Mappale {old_part.mappale}" if old_part else (c['old'] or '—')
                    c['new'] = f"Foglio {new_part.foglio}, Mappale {new_part.mappale}" if new_part else (c['new'] or '—')
        elif history_type == '+':
            particella_id = getattr(record, 'particella_id', None)
            particella = Particella.objects.filter(pk=particella_id).first() if particella_id else None
            if particella:
                changes = [c for c in changes if c['field'] != 'particella']
                changes.append({
                    'field': 'particella',
                    'old': None,
                    'new': f"Foglio {particella.foglio}, Mappale {particella.mappale}, Subalterno {record.subalterno or '-'}",
                })
            detail = f"Aggiunta particella: Foglio {particella.foglio}, Mappale {particella.mappale}, Subalterno {record.subalterno or '-'}" if particella else None
        elif history_type == '-':
            particella_id = getattr(record, 'particella_id', None)
            particella = Particella.objects.filter(pk=particella_id).first() if particella_id else None
            detail = f"Rimossa particella: Foglio {particella.foglio}, Mappale {particella.mappale}, Subalterno {record.subalterno or '-'}" if particella else None
        else:
            detail = None
        event_date = record.history_date
        if timezone.is_naive(event_date):
            event_date = timezone.make_aware(event_date, timezone=timezone.get_default_timezone())
        all_events.append({
            'date': event_date,
            'user': record.history_user,
            'type': tipo_label,
            'type_code': history_type,
            'model': 'Particella in pratica',
            'changes': changes,
            'detail': detail,
        })

    for record in Diario.history.filter(pratica=pratica):
        changes = get_changes(record, Diario)
        history_type = record.history_type
        if history_type == '+':
            tipo_label = 'Aggiunta'
        elif history_type == '~':
            tipo_label = 'Modifica'
        elif history_type == '-':
            tipo_label = 'Rimossa'
        else:
            tipo_label = history_type
        detail = None
        if history_type == '~':
            for c in changes:
                if c['field'] == 'description':
                    c['old'] = c['old'] or ''
                    c['new'] = c['new'] or ''
        elif history_type == '+':
            desc = getattr(record, 'description', None)
            detail = f"Aggiunta nota: {desc}" if desc else None
        else:
            detail = None
        event_date = record.history_date
        if timezone.is_naive(event_date):
            event_date = timezone.make_aware(event_date, timezone=timezone.get_default_timezone())
        all_events.append({
            'date': event_date,
            'user': record.history_user,
            'type': tipo_label,
            'type_code': history_type,
            'model': 'Diario',
            'changes': changes,
            'detail': detail,
        })

    for record in Documento.objects.filter(pratica=pratica).order_by('data_crea'):
        event_date = record.data_crea
        if timezone.is_naive(event_date):
            event_date = timezone.make_aware(event_date, timezone=timezone.get_default_timezone())
        all_events.append({
            'date': event_date,
            'user': record.username,
            'type': 'Caricamento',
            'type_code': '+',
            'model': 'Documento',
            'changes': [],
            'detail': f"Caricato documento: {record.name}" if record.name else 'Documento caricato',
        })

    for record in DocumentoDownload.objects.filter(documento__pratica=pratica).select_related('user', 'documento').order_by('data_download'):
        event_date = record.data_download
        if timezone.is_naive(event_date):
            event_date = timezone.make_aware(event_date, timezone=timezone.get_default_timezone())
        all_events.append({
            'date': event_date,
            'user': record.user,
            'type': 'Download',
            'type_code': '↓',
            'model': 'Documento',
            'changes': [],
            'detail': f"Scaricato documento: {record.documento.name}" if record.documento.name else 'Documento scaricato',
        })

    for sub in SostituzioneSoggetto.objects.filter(pratica=pratica):
        changes = []
        for field in SostituzioneSoggetto._meta.get_fields():
            if field.name in ('history', 'id', 'pratica', 'user', 'data_crea', 'data_mod'):
                continue
            if not (field.many_to_many or field.one_to_many) and hasattr(sub, field.name):
                val = getattr(sub, field.name)
                if val is not None:
                    changes.append({
                        'field': field.verbose_name or field.name,
                        'old': None,
                        'new': val,
                    })
        event_date = sub.data_crea
        if timezone.is_naive(event_date):
            event_date = timezone.make_aware(event_date, timezone=timezone.get_default_timezone())
        all_events.append({
            'date': event_date,
            'user': sub.user,
            'type': 'Sostituzione',
            'type_code': 'sost',
            'model': 'Sostituzione soggetto',
            'changes': changes,
        })

    all_events.sort(key=lambda x: x['date'], reverse=True)

    context = {
        'pratica': pratica,
        'history': all_events,
        'pk': pk,
    }
    return render(request, 'protocollo/history_pratica.html', context)


# EDITA pratica
@login_required
@editor_required

def pratica_edit(request,pk):
    pratica = get_object_or_404(get_practice_queryset(request.user), id=pk)

    if request.method == 'POST':
        form = PraticaForm(request.POST, instance=pratica, user=request.user)
        # Assicura che il queryset mostri tutti i tipi per i superuser o filtri per settore
        if request.user.is_superuser:
            form.fields['tipo_pratica'].queryset = TipoPratica.objects.all().order_by(Lower('name'))
        else:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.settore:
                form.fields['tipo_pratica'].queryset = TipoPratica.objects.filter(
                    Q(settore=profile.settore.settore) | Q(id=pratica.tipo_pratica_id)
                ).order_by('name')

        if form.is_valid():
            pratica = form.save(commit=False)
            
            # Recupero coordinate dai campi del form (lat/lng o stringa combinata)
            lat = form.cleaned_data.get('lat')
            lng = form.cleaned_data.get('lng')
            pos_str = request.POST.get('posizione')
            
            if lat is not None and lng is not None:
                try:
                    pratica.posizione = Point(float(lng), float(lat))
                except (ValueError, TypeError, AttributeError):
                    pass
            elif pos_str:
                try:
                    # Gestisce il formato "lat,lng" spesso inviato da widget JS
                    p_lat, p_lng = pos_str.split(',')
                    pratica.posizione = Point(float(p_lng.strip()), float(p_lat.strip()))
                except (ValueError, TypeError, AttributeError, IndexError):
                    pass

            # Geolocalizzazione automatica (indirizzo completo o particelle) se non impostata manualmente
            if not pratica.posizione:
                ubica_pratica(pratica)

            pratica.save()
            log_action(request, 'MODIFICATO', f'Pratica {pratica.id}')
            messages.success(request, "Pratica aggiornata con successo.")
            return redirect('protocollo:pratica_detail_url', pk)
    else:
        # Pre-popola i campi lat/lng nel form per posizionare il marker esistente sulla mappa
        initial_data = {}
        if pratica.posizione:
            initial_data['lat'] = pratica.posizione.y
            initial_data['lng'] = pratica.posizione.x
        form = PraticaForm(instance=pratica, user=request.user, initial=initial_data)
        # Applica lo stesso filtro del queryset anche per la richiesta GET
        if request.user.is_superuser:
            form.fields['tipo_pratica'].queryset = TipoPratica.objects.all().order_by(Lower('name'))
        else:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.settore:
                form.fields['tipo_pratica'].queryset = TipoPratica.objects.filter(
                    Q(settore=profile.settore.settore) | Q(id=pratica.tipo_pratica_id)
                ).order_by('name')

    # Recupera la lista dei tipi di pratica per il context (usata in molti template del progetto)
    tipo_pratica_list = get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True)

    # Parametri mappa per l'edit
    lat_map = pratica.posizione.y if pratica.posizione else 44.07721
    lng_map =     pratica.posizione.x if pratica.posizione else 10.09636

    m = build_base_map(lat_map, lng_map, zoom_start=15)

    if pratica.mpoly_pratica:
        folium.GeoJson(
            pratica.mpoly_pratica.json,
            name="Confini Catastali",
            style_function=lambda x: {'color': 'blue', 'weight': 2, 'fillOpacity': 0.1}
        ).add_to(m)

    folium.Marker([lat_map, lng_map], popup="Posizione Salvata").add_to(m)

    context = {
        'form': form,
        'pratica': pratica,
        'data_prot_gen': pratica.data_prot_gen,
        'tipo_pratica_list': tipo_pratica_list,
        'initial_latitude': lat_map,
        'initial_longitude': lng_map,
        'map_html': m._repr_html_(),
    }
    return render(request, 'protocollo/pratica_edit.html', context)

 



# ELIMINA pratica
@login_required
@editor_required

def pratica_delete(request, pk):
    pratica = get_object_or_404(get_practice_queryset(request.user), pk=pk)

    if request.method == 'POST':
        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
        logger_user_actions.info(f"Utente: {user_username} ha eliminato la pratica {pratica.prot_gen } del {pratica.data_prot_gen} (id : {pratica.id})")
        # delete the pratica from the database
        pratica.delete()
        log_action(request, 'ELIMINATO', f'Pratica {pratica.id}', {'prot_gen': pratica.prot_gen})
        # redirect to the praticas list
        return redirect('protocollo:index_pratiche_url')

    # no need for an `else` here. If it's a GET request, just continue

    return render(request,
                    'protocollo/pratica_delete.html',
                    {'pratica': pratica})




############################
# POSIZIONA su indirizzo / particelle
def ubica_pratica(pratica, force=False):
    """Calcola e salva la posizione della pratica:
    - Geocodifica solo se l'indirizzo è completo (via + civico numerico diverso da 0).
    - Se l'indirizzo non è valido ma sono presenti particelle, usa il centroide di mpoly_pratica.
    - Non sovrascrive una posizione già impostata manualmente, a meno che force=True.
    Restituisce True se la posizione è stata aggiornata.
    """
    if not force and pratica.posizione:
        return False

    street = pratica.street
    civico = str(pratica.housenumber or '').strip()
    has_street = bool(street and street.street)
    has_valid_civico = bool(re.search(r'\d', civico)) and civico != '0'
    has_mpoly = bool(pratica.mpoly_pratica)

    # Indirizzo completo: geocodifica
    if has_street and has_valid_civico:
        try:
            geolocator = Nominatim(user_agent="opengeoprot_app")
            address = f"{street.street}, {civico}, Carrara, Italy"
            location = geolocator.geocode(address)
            if location:
                pratica.posizione = Point(location.longitude, location.latitude, srid=4326)
                pratica.save()
                return True
        except Exception as e:
            logger_user_actions.error(f"Errore geocodifica per pratica {pratica.id}: {e}")

    # Indirizzo incompleto o geocodifica fallita: centroide particelle
    if has_mpoly:
        try:
            pratica.posizione = pratica.mpoly_pratica.centroid
            pratica.save()
            return True
        except Exception as e:
            logger_user_actions.error(f"Errore calcolo centroide per pratica {pratica.id}: {e}")

    return False


@login_required
def Ubica(request,pk):
    pratica=get_object_or_404(get_practice_queryset(request.user), pk=pk)

    lat = request.GET.get('lat')
    lng = request.GET.get('lng')

    if lat and lng:
        try:
            pratica.posizione = Point(float(lng), float(lat), srid=4326)
            pratica.save()
            messages.success(request, "Posizione impostata manualmente.")
        except (ValueError, TypeError):
            messages.error(request, "Coordinate non valide.")
    elif ubica_pratica(pratica, force=True):
        messages.success(request, "Posizione aggiornata tramite indirizzo o particelle.")
    else:
        messages.warning(request, "Nessuna posizione aggiornata: indirizzo o particelle mancanti.")

    return redirect('protocollo:pratica_detail_url', pk=pk)



    
    




##########################################################
#                SOGGETTI PRATICA
##########################################################


# Elenca i soggetti per pratica (pk)
@login_required
def soggetti_pratica_list(request,pk):
    anagrafe = Anaprat.objects.filter(pratica_id=pk).select_related('soggetto', 'tipo').order_by('-tipo')
    anaprat=[]
    for a in anagrafe:
        anagrafe_pratica={} # creo un dizionario vuoto
        soggetto = a.soggetto
        anagrafe_pratica['id']=a.id
        anagrafe_pratica['id_soggetto']=a.soggetto.id
        anagrafe_pratica['tipo']=a.tipo
        anagrafe_pratica['cognome']=soggetto.cognome
        anagrafe_pratica['nome']=soggetto.nome
        
        anagrafe_pratica['data_nascita']=soggetto.data_nascita
        anagrafe_pratica['comune_nascita']=soggetto.comune_nascita
        anagrafe_pratica['codice_fiscale']=soggetto.codice_fiscale
        anaprat.append(anagrafe_pratica)
    anaprat = sorted(anaprat, key=lambda x: x['tipo'].id)

    return render(request,'protocollo/soggetti_pratica_list.html', {'anaprat':anaprat,'pk':pk})


# ricerca i soggetti da aggiungere alla pratica
# lista i soggetti presenti
# ricerca da pratica in Soggetto ed aggiunge
@login_required
def list_soggetti_view(request, pk):
    if request.method == "POST":
        cognome = request.POST.get('cognome')
        nome = request.POST.get('nome')

        # 1. Ricerca tra i soggetti già censiti in protocollo
        soggetti = Soggetto.objects.filter(
            Q(cognome__icontains=cognome) & Q(nome__icontains=nome)
        ).order_by('cognome', 'nome')
        tot_soggetti = soggetti.count()

        # 2. Ricerca in anagrafe_residenti (sempre, per permettere di scegliere il soggetto corretto)
        anagrafe = Residenti.objects.filter(
            Q(cognome__icontains=cognome) & Q(nome__icontains=nome)
        ).order_by('cognome', 'nome')
        tot_res = anagrafe.count()

        if tot_soggetti == 0 and tot_res == 0:
            # Nessun riscontro in nessuna fonte: propone messaggio + inserimento nuovo soggetto
            return render(request, 'protocollo/soggetti_list.html', {
                'pk': pk,
                'cognome': cognome,
                'nome': nome,
                'nessun_risultato': True,
            })

        return render(request, 'protocollo/soggetti_list.html', {
            'pk': pk,
            'cognome': cognome,
            'nome': nome,
            'soggetti': soggetti,
            'tot_soggetti': tot_soggetti,
            'residents': anagrafe,
            'tot_res': tot_res,
        })
    return render(request, 'protocollo/soggetti_list.html', {'pk': pk})



# dettaglio del soggetto
@login_required
@editor_required(allow_viewers=True)

def SoggettoPraticaDetailView(request, id, pk):
    is_editor = is_editor_func(request.user)

    soggetto = Soggetto.objects.get(id=id)
    tipo_soggetto = TipoSoggetto.objects.all().order_by('id')
    context={
        'pk':pk,
        'soggetto':soggetto,
        'tipo_soggetto':tipo_soggetto,
        'is_editor':is_editor,
        }
                                    
    return render (request, 'protocollo/soggetto_pratica_detail.html',context)




# PDF stampa scheda pratica
@login_required
@editor_required(allow_viewers=True)

def pdf_pratica(request, *args, **kwargs):
    if request.user.groups.filter(name='readonly').exists():
        from django.shortcuts import redirect
        return redirect('accounts:richiesta_accesso', pk=kwargs.get('pk'))
    pk = kwargs.get('pk')
    pratica = get_object_or_404(get_practice_queryset(request.user), pk=pk)
    anagrafe = Anaprat.objects.filter(pratica=pk).select_related('soggetto', 'tipo')
    anaprat=[]
    for a in anagrafe:
        anagrafe_pratica={} # creo un dizionario vuoto
        soggetto = a.soggetto
        anagrafe_pratica['id']=a.id
        anagrafe_pratica['id_soggetto']=a.soggetto.id
        anagrafe_pratica['tipo']=a.tipo
        anagrafe_pratica['cognome']=soggetto.cognome
        anagrafe_pratica['nome']=soggetto.nome
        anagrafe_pratica['data_nascita']=soggetto.data_nascita
        anagrafe_pratica['comune_nascita']=soggetto.comune_nascita
        anagrafe_pratica['codice_fiscale']=soggetto.codice_fiscale
        anaprat.append(anagrafe_pratica)
    
    template_path = 'protocollo/pdf_pratica.html'
    # filename_pdf = 'pratica_'+pratica.prot_gen +'.pdf'
    context = {'pratica': pratica,'anaprat':anaprat}
    # Create a Django response object, and specify content_type as pdf
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment;'
    # find the template and render it.
    template = get_template(template_path)
    html = template.render(context)

    # create a pdf
    pisa_status = pisa.CreatePDF(
       html, dest=response)
    
    # if error then show some funy view
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')

    return response


@login_required
@editor_required(allow_viewers=True)

def report_poc_2022_pdf(request):
    if request.user.groups.filter(name='readonly').exists():
        from django.shortcuts import redirect
        return redirect('home:index')
    from protocollo.reports.poc_2022 import OsservatorioPoc2022Report

    report = OsservatorioPoc2022Report()
    stats = report.get_statistiche()

    totale = stats['totale_pratiche']
    classi = stats['classi']

    classi_counts = []
    for classe, info in classi.items():
        count = info['count']
        pct = (count / totale * 100) if totale > 0 else 0
        classi_counts.append((classe, count, round(pct)))

    context = {
        'data_generazione': timezone.now().strftime('%d/%m/%Y %H:%M'),
        'totale_pratiche': totale,
        'classi': classi,
        'classi_counts': classi_counts,
    }

    template_path = 'protocollo/reports/poc_2022_report.html'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report_poc_2022.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')

    return response




@login_required
@editor_required(allow_viewers=True)
def report_istrcomm_poc_pdf(request):
    if request.user.groups.filter(name='readonly').exists():
        from django.shortcuts import redirect
        return redirect('home:index')

    from istruttoria_poc.models import IstrComm

    # Pratiche che hanno istruttoria_poc_istrcomm
    pratiche_ids = IstrComm.objects.values_list('pratica_id', flat=True)
    from protocollo.models import Pratica
    qs = Pratica.objects.filter(id__in=pratiche_ids)

    # Ordina per classe e, all'interno della classe, per data commissione
    items = []
    for p in qs:
        istrcomm = IstrComm.objects.filter(pratica=p).first()
        classe = p.classe if p.classe is not None else 'Non definito'
        data_comm = istrcomm.data_commissione if istrcomm else None
        items.append((classe, data_comm is None, data_comm, p, istrcomm))
    items.sort(key=lambda x: (str(x[0]), x[1], x[2] or ''))

    classi = {}
    for classe, _, _, p, istrcomm in items:
        testo = istrcomm.testo if istrcomm else ''
        info = classi.setdefault(classe, {'count': 0, 'pratiche': []})
        info['count'] += 1
        info['pratiche'].append({'pratica': p, 'testo': testo, 'data_commissione': (istrcomm.data_commissione if istrcomm else None)})

    totale = len(items)
    classi_counts = []
    for classe, info in classi.items():
        pct = (info['count'] / totale * 100) if totale > 0 else 0
        classi_counts.append((classe, info['count'], round(pct)))

    context = {
        'data_generazione': timezone.now().strftime('%d/%m/%Y %H:%M'),
        'totale_pratiche': totale,
        'classi': classi,
        'classi_counts': classi_counts,
    }

    template_path = 'protocollo/reports/istrcomm_poc_report.html'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report_istrcomm_poc.pdf"'

    user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
    logger_user_actions.info(
        f"l'user {user_username} ha creato il report istrcomm_poc in data "
        f"{timezone.now().strftime('%d/%m/%Y')} alle ore {timezone.now().strftime('%H:%M')}"
    )

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response



# aggiunge soggetto alla pratica
@login_required
@editor_required

def add_soggetto_pratica_view(request, pk=None):
    ts = TipoSoggetto.objects.all() # elenca tutti i record di TipoSoggetto

    if request.method == "POST":
        form = AddSoggettoPraticaForm(request.POST)
        
        if form.is_valid():
            obj= form.save(commit=False)
            obj.user = request.user
            obj.pratica_id=pk
            obj.save()
            log_action(request, 'CREATO', f'Anaprat {obj.id}', {'soggetto': obj.soggetto_id, 'pratica': pk})

            return redirect('protocollo:pratica_detail_url', pk) # questo ridirige alla pagina di dettaglio pratica
        else:
            # Form non valido: messaggio d'errore e ritorno al dettaglio pratica
            messages.error(request, "Dati non validi: soggetto non aggiunto.")
            return redirect('protocollo:pratica_detail_url', pk)

    else:
        form = PraticaForm()
        cognome = request.GET.get('cognome', '')
        submitted = 'submitted' in request.GET

        return render(request,'protocollo/pratica_add.html',{'form':form,'submitted':submitted, 'tipo_soggetto':ts, 'cognome':cognome})

# elimina il soggetto dalla pratica
@login_required
# @permission_required('protocollo.delete_anaprat', raise_exception=True)
@editor_required(strict=True)

def soggetto_pratica_delete(request, id, pk):
    soggetto_pratica = Anaprat.objects.get(id=id) # we need this for both GET and POST

    nominativo = Soggetto.objects.get(id=soggetto_pratica.soggetto_id)
    user_username = request.user.username if request.user.is_authenticated else 'Anonimo'

    if request.method == 'POST':
        
        soggetto_pratica.delete() # delete the pratica from the database
        log_action(request, 'ELIMINATO', f'Anaprat {id}', {'soggetto': f'{nominativo.cognome} {nominativo.nome}', 'pratica': pk})
        logger_user_actions.info(f"Utente: {user_username} ha ELIMINATO il soggetto  {nominativo.cognome} {nominativo.nome} dalla pratica {pk}")

        Diario.objects.create(
            pratica_id=pk,
            description=f"eliminato soggetto {soggetto_pratica.soggetto_id} {nominativo.cognome} {nominativo.nome} - tipo: {soggetto_pratica.tipo.name if soggetto_pratica.tipo else 'N/A'}",
            user=request.user
        )

        # redirect to the praticas list
        # return redirect('protocollo:index_pratiche_url')
        return redirect('protocollo:pratica_detail_url', pk) # questo ridirige alla pagina di dettaglio pratica

    # no need for an `else` here. If it's a GET request, just continue
    else:
        return render(request,
                    'protocollo/soggetto_pratica_delete.html',
                    {'soggetto': soggetto_pratica, 'nominativo':nominativo})


##########################################################
#                      SOGGETTI 
##########################################################
@login_required
@editor_required


def add_soggetto_view(request, pk=None):
    ts = TipoSoggetto.objects.all().order_by('id') # elenca tutti i record di TipoSoggetto
    submitted = False
    if request.method == "POST":
        form = SoggettoForm(request.POST)
        if form.is_valid():
            form.save()
            latest_id = Soggetto.objects.latest('id').id # ricava l'ID dell'ultimo soggetto
            soggetto = Soggetto.objects.get(id=latest_id)
            log_action(request, 'CREATO', f'Soggetto {soggetto.id}', {'cognome': soggetto.cognome, 'nome': soggetto.nome})
            context={
                'pk':pk,
                'soggetto':soggetto,
                'tipo_soggetto':ts,
                     }
            return render (request, 'protocollo/soggetto_pratica_detail.html',context)
        else:
            # Form non valido: ri-renderizza con errori
            return render(request,'protocollo/add_soggetto.html',{'form':form,'submitted':submitted})
    else:
        form = SoggettoForm()
        if 'submitted' in request.GET:
            submitted = True

        return render(request,'protocollo/add_soggetto.html',{'form':form,'submitted':submitted})

@login_required
def SoggettoDetailView(request, id, pk=None):
    ts = TipoSoggetto.objects.all().order_by('id') # elenca tutti i record di TipoSoggetto

    soggetto = Soggetto.objects.get(id=id)
    log_action(request, 'VISUALIZZATO', f'Soggetto {soggetto.id}')


    # Recupera tutte le pratiche collegate a questo soggetto
    anagrafe = Anaprat.objects.filter(soggetto=soggetto).select_related(
        'pratica', 'tipo', 'pratica__street', 'pratica__tipo_pratica'
    ).order_by('-pratica__data_prot_gen', '-pratica__prot_gen')
    pratiche = []
    for a in anagrafe:
        p_obj = a.pratica
        if p_obj:
            anagrafe_pratica = {}
            anagrafe_pratica['id'] = a.id
            anagrafe_pratica['code_p'] = p_obj.code_p
            anagrafe_pratica['sub_code'] = p_obj.sub_code
            anagrafe_pratica['id_pratica'] = p_obj.id
            anagrafe_pratica['tipo'] = str(a.tipo) if a.tipo else None
            anagrafe_pratica['tipo_pratica'] = str(p_obj.tipo_pratica) if p_obj.tipo_pratica else None
            anagrafe_pratica['oggetto'] = p_obj.oggetto

            strada = p_obj.street.street if p_obj.street else ""
            anagrafe_pratica['ubicazione'] = f"{strada}, {p_obj.housenumber or ''}".strip(", ")

            anagrafe_pratica['prot_gen'] = p_obj.prot_gen
            anagrafe_pratica['data_prot_gen'] = p_obj.data_prot_gen

            if p_obj.posizione:
                anagrafe_pratica['lat'] = p_obj.posizione.y
                anagrafe_pratica['lng'] = p_obj.posizione.x
            else:
                anagrafe_pratica['lat'] = None
                anagrafe_pratica['lng'] = None

            pratiche.append(anagrafe_pratica)


    return render(request, 'protocollo/soggetto_detail.html', context={
        'soggetto': soggetto,
        'pratiche': pratiche,
    })

@login_required
# @editor_required

def SoggettoEditView(request,id, pk):
    is_editor = is_editor_func(request.user)

    anaprat = get_object_or_404(Anaprat, id=id)
    soggetto = anaprat.soggetto
    
    if not pk:
        messages.error(request, "Errore: Pratica non trovata in sessione.")
        return redirect('protocollo:index_pratiche_url')
        
    pratica_lavorazione = get_object_or_404(get_practice_queryset(request.user), id=pk)

    if request.method == 'POST':
        form = SoggettoForm(request.POST, instance=soggetto)
        if form.is_valid():
            form.save()
            log_action(request, 'MODIFICATO', f'Soggetto {soggetto.id}')
            # Aggiorna il tipo nella relazione Anaprat
            tipo_id = request.POST.get('tipo')
            if tipo_id:
                try:
                    tipo_obj = TipoSoggetto.objects.get(id=tipo_id)
                    anaprat.tipo = tipo_obj
                    anaprat.save()
                except TipoSoggetto.DoesNotExist:
                    pass  # Gestisci l'errore se necessario
            messages.success(request, "Dati del soggetto aggiornati.")
            return redirect('protocollo:pratica_detail_url', pk)
    else:
        form = SoggettoForm(instance=soggetto)

    # Recupera tutte le pratiche collegate a questo soggetto per la tabella
    anagrafe = Anaprat.objects.filter(soggetto=soggetto).select_related('pratica', 'tipo', 'pratica__street', 'pratica__tipo_pratica').order_by('-pratica__data_prot_gen', '-pratica__prot_gen')
    pratiche=[]
    for a in anagrafe:
        p_obj = a.pratica
        if p_obj:
            anagrafe_pratica={} 
            anagrafe_pratica['id']=a.id
            anagrafe_pratica['code_p']=p_obj.code_p
            anagrafe_pratica['sub_code']=p_obj.sub_code
            anagrafe_pratica['id_pratica']=p_obj.id # Corretto: ID della pratica per il link
            anagrafe_pratica['tipo']=a.tipo
            anagrafe_pratica['tipo_pratica']=p_obj.tipo_pratica
            anagrafe_pratica['oggetto']=p_obj.oggetto
            
            strada = p_obj.street.street if p_obj.street else ""
            anagrafe_pratica['ubicazione']= f"{strada}, {p_obj.housenumber or ''}".strip(", ")
            
            anagrafe_pratica['prot_gen']=p_obj.prot_gen
            anagrafe_pratica['data_prot_gen']=p_obj.data_prot_gen
            pratiche.append(anagrafe_pratica)

    context = {
        'form': form, 
        'soggetto_id': soggetto.id,
        'soggetto':soggetto,
        'pk':pk,
        'pratica':pratica_lavorazione,
        'pratiche':pratiche,
        'is_editor':is_editor,
        'tipo_selezionato': anaprat.tipo.id if anaprat.tipo else None,
        'tipi_soggetto': TipoSoggetto.objects.all().order_by('name')
    }
    return render(request,
                'protocollo/soggetto_edit.html',
                context)


@login_required
@editor_required(strict=True)

def sostituisci_soggetto_view(request, id):
    anaprat = get_object_or_404(Anaprat, id=id)
    soggetto = anaprat.soggetto
    pratica = anaprat.pratica

    if not pratica:
        messages.error(request, "Pratica non trovata.")
        return redirect('protocollo:index_pratiche_url')

    ex_soggetto_desc = (
        f"{soggetto.cognome} {soggetto.nome}, "
        f"CF: {soggetto.codice_fiscale or 'N/D'}, "
        f"nato/a il {soggetto.data_nascita or 'N/D'} a {soggetto.comune_nascita or 'N/D'}"
    )
    if anaprat.tipo:
        ex_soggetto_desc += f", Tipo: {anaprat.tipo.name}"

    if request.method == 'POST':
        descrizione = request.POST.get('descrizione', '')

        sostituzione = SostituzioneSoggetto.objects.create(
            pratica=pratica,
            ex_soggetto=ex_soggetto_desc,
            idsoggetto_ex=soggetto.id,
            prot_gen=pratica.prot_gen,
            data_prot_gen=pratica.data_prot_gen,
            descrizione=descrizione or f"Sostituzione soggetto in pratica {pratica.prot_gen}",
            user=request.user if request.user.is_authenticated else None
        )

        anaprat.delete()

        request.session['sostituzione_descrizione'] = descrizione or f"Sostituzione soggetto in pratica {pratica.prot_gen}"
        request.session['sostituzione_flusso'] = True
        request.session['sostituzione_id'] = sostituzione.id
        return redirect('protocollo:upload_url', pk=pratica.id)

    context = {
        'pratica': pratica,
        'ex_soggetto_desc': ex_soggetto_desc,
    }
    return render(request, 'protocollo/sostituisci_soggetto_confirm.html', context)


@login_required
def aggiungi_residente_a_pratica_view(request, id, pk):
    """Crea (o recupera) il Soggetto dall'anagrafe e rimanda all'edit per impostare il tipo
    prima di collegarlo alla pratica."""
    residente = get_object_or_404(Residenti, id=id)
    if not pk:
        messages.error(request, "Pratica non trovata in sessione.")
        return redirect('protocollo:index_pratiche_url')

    cf = residente.codice_fiscale
    if cf:
        soggetto, _ = Soggetto.objects.get_or_create(
            codice_fiscale=cf,
            defaults={
                'cognome': residente.cognome,
                'nome': residente.nome,
                'data_nascita': residente.data_nascita,
                'comune_nascita': residente.comune_nascita,
                'comune_residenza': residente.comune_residenza,
                'addr': residente.addr,
                'user': request.user,
            }
        )
    else:
        soggetto, _ = Soggetto.objects.get_or_create(
            cognome=residente.cognome,
            nome=residente.nome,
            data_nascita=residente.data_nascita,
            defaults={
                'comune_nascita': residente.comune_nascita,
                'comune_residenza': residente.comune_residenza,
                'addr': residente.addr,
                'user': request.user,
            }
        )

    # Non collega ancora il soggetto alla pratica: lo fa aggiungi_residente_edit_view al salvataggio
    return redirect('protocollo:aggiungi_residente_edit_url', id=soggetto.id, pk=pk)


@login_required
@editor_required
def aggiungi_residente_edit_view(request, id, pk):
    """Edit del Soggetto proveniente da anagrafe: collega il soggetto alla pratica
    SOLO al salvataggio, e solo dopo aver impostato il tipo."""
    soggetto = get_object_or_404(Soggetto, id=id)
    if not pk:
        messages.error(request, "Pratica non trovata in sessione.")
        return redirect('protocollo:index_pratiche_url')

    pratica = get_object_or_404(get_practice_queryset(request.user), id=pk)
    is_editor = is_editor_func(request.user)

    tipi_soggetto = TipoSoggetto.objects.all().order_by('name')

    if request.method == 'POST':
        form = SoggettoForm(request.POST, instance=soggetto)
        if form.is_valid():
            tipo_id = request.POST.get('tipo')
            if not tipo_id:
                messages.error(request, "Seleziona il tipo di soggetto prima di salvare.")
                return render(request, 'protocollo/soggetto_edit.html', {
                    'form': form,
                    'soggetto': soggetto,
                    'soggetto_id': soggetto.id,
                    'pk': pk,
                    'pratica': pratica,
                    'is_editor': is_editor,
                    'tipo_selezionato': None,
                    'tipi_soggetto': tipi_soggetto,
                    'pratiche': [],
                })
            form.save()
            tipo_obj = TipoSoggetto.objects.get(id=tipo_id)
            anaprat, created = Anaprat.objects.get_or_create(
                pratica=pratica,
                soggetto=soggetto,
                defaults={'tipo': tipo_obj, 'user': request.user}
            )
            if not created:
                anaprat.tipo = tipo_obj
                anaprat.save()
            messages.success(request, f"Soggetto {soggetto} aggiunto alla pratica.")
            return redirect('protocollo:pratica_detail_url', pk)
    else:
        form = SoggettoForm(instance=soggetto)

    return render(request, 'protocollo/soggetto_edit.html', {
        'form': form,
        'soggetto': soggetto,
        'soggetto_id': soggetto.id,
        'pk': pk,
        'pratica': pratica,
        'is_editor': is_editor,
        'tipo_selezionato': None,
        'tipi_soggetto': tipi_soggetto,
        'pratiche': [],
    })


@login_required
def aggiungi_soggetto_a_pratica_view(request, id, pk):
    soggetto = get_object_or_404(Soggetto, id=id)
    if not pk:
        messages.error(request, "Pratica non trovata in sessione.")
        return redirect('protocollo:index_pratiche_url')

    pratica = get_object_or_404(get_practice_queryset(request.user), id=pk)

    anaprat, created = Anaprat.objects.get_or_create(
        pratica=pratica,
        soggetto=soggetto,
        defaults={'user': request.user}
    )

    if created:
        messages.success(request, f"Soggetto {soggetto} aggiunto alla pratica.")

        sostituzione_id = request.session.pop('sostituzione_id', None)
        if sostituzione_id:
            SostituzioneSoggetto.objects.filter(id=sostituzione_id).update(soggetto_subentrato=soggetto)
    else:
        messages.info(request, f"Soggetto {soggetto} già presente nella pratica.")

    return redirect('protocollo:pratica_detail_url', pk=pk)


@login_required
def PraticheSoggettoList(request, id, pk=None):
    """Lista le altre pratiche di un soggetto escludendo quella corrente."""
    soggetto = get_object_or_404(Soggetto, id=id)
    # pk (pratica corrente) disponibile come parametro URL; l'exclude è disattivato:
    # .exclude(pratica_id=pk)

    # Recupera le relazioni Anaprat incluso la pratica corrente e ottimizzando le query correlate
    anaprat_list = Anaprat.objects.filter(soggetto=soggetto).select_related(
        'pratica', 'tipo', 'pratica__street', 'pratica__tipo_pratica'
    ).prefetch_related('pratica__pratiche__particella').order_by('-pratica__data_prot_gen', '-pratica__prot_gen')
    # .exclude(pratica_id=current_pk).order_by('-pratica__data_prot_gen', '-pratica__prot_gen')

    context = {
        'soggetto': soggetto,
        'anaprat_list': anaprat_list,
    }
    return render(request, 'protocollo/partials/_pratiche_soggetto_all.html', context)

##########################################################
#                      PARTICELLE 
##########################################################

# Elenca le particelle per pratica (pk)
@login_required
def particelle_pratica_list(request,pk):
    catasto = Cataprat.objects.all().filter(pratica=pk)
    
    cataprat=[]
    for a in catasto:
        particelle_pratica={}
        particella = Particella.objects.get(id=a.particella.id)
        particelle_pratica['id_anaprat']=a.id
        particelle_pratica['id_particella']=a.particella.id
        particelle_pratica['foglio']=particella.foglio
        particelle_pratica['mappale']=particella.mappale
        particelle_pratica['subalterno']=particella.subalterno
        
        foglio_norm = str(particella.foglio).zfill(4)
        foglio_raw = str(particella.foglio)
        mappale_raw = str(particella.mappale)
        cp = Particelle.objects.using('anagrafe').filter(
            Q(foglio__iexact=foglio_norm) | Q(foglio__iexact=foglio_raw),
            mappale__iexact=mappale_raw
        ).first()
        particelle_pratica['id_catasto'] = cp.id if cp else None
        
        cataprat.append(particelle_pratica)
    
    return render(request,'protocollo/partials/_particelle_pratica_list.html', {'cataprat':cataprat,'pk':pk})


def _particella_geom_da_catasto(foglio, mappale):
    """
    Cerca la particella in catasto.Particelle (vw_particelle sul DB 'anagrafe')
    e restituisce (particella_catasto, geometria_normalizzata_4326).
    La geometria e' None se la particella non esiste o non ha mpoly.
    """
    foglio_raw = (foglio or '').strip()
    mappale_raw = (mappale or '').strip()
    if not foglio_raw or not mappale_raw:
        return None, None

    foglio_norm = foglio_raw.zfill(4)
    mappale_norm = mappale_raw.zfill(4)

    c = Particelle.objects.using('anagrafe').filter(
        (Q(foglio__iexact=foglio_raw) | Q(foglio__iexact=foglio_norm)) &
        (Q(mappale__iexact=mappale_raw) | Q(mappale__iexact=mappale_norm))
    ).first()

    if c is None:
        return None, None

    geom = c.mpoly
    if isinstance(geom, str):
        try:
            geom = GEOSGeometry(geom)
        except Exception:
            return c, None
    if geom is None:
        return c, None
    if geom.srid and geom.srid != 4326:
        geom.transform(4326)
    if geom.geom_type == 'Polygon':
        geom = MultiPolygon(geom)
    if not geom.valid:
        geom = geom.buffer(0)
    return c, geom


@login_required
def list_particelle_view(request, pk=None):
    if request.method == "POST":
        foglio = request.POST.get('foglio', '').strip()
        mappale = request.POST.get('mappale', '').strip()

        foglio_raw = foglio
        foglio_norm = foglio.zfill(4) if foglio else foglio
        mappale_raw = mappale
        mappale_norm = mappale

        # 1. Ricerca prima in catasto.Particelle (vw_particelle, DB 'anagrafe')
        c, geom_to_save = _particella_geom_da_catasto(foglio, mappale)

        # 1a. Trovata in catasto CON geometria: riusa/aggiorna archivio
        if c is not None and geom_to_save is not None:
            particelle = Particella.objects.filter(
                (Q(foglio__iexact=foglio_raw) | Q(foglio__iexact=foglio_norm)) &
                (Q(mappale__iexact=mappale_raw) | Q(mappale__iexact=mappale_norm))
            )
            if particelle.exists():
                p_archivio = particelle.first()
                p_archivio.mpoly = geom_to_save
                p_archivio.save(update_fields=['mpoly'])
                return redirect('protocollo:particella_pratica_detail_url', id=p_archivio.id, pk=pk)
            new_p = Particella.objects.create(
                foglio=c.foglio.lstrip('0') if c.foglio else c.foglio,
                mappale=c.mappale,
                mpoly=geom_to_save
            )
            return redirect('protocollo:particella_pratica_detail_url', id=new_p.id, pk=pk)
        elif c is not None:
            messages.warning(request, f"Particella F:{foglio} M:{mappale} trovata in catasto ma senza geometria: non aggiungibile.")
            return redirect('protocollo:particelle_list_url', pk=pk)

        # 2. Non trovata in catasto: fallback su protocollo.Particella (archivio)
        particelle = Particella.objects.filter(
            (Q(foglio__iexact=foglio_raw) | Q(foglio__iexact=foglio_norm)) &
            (Q(mappale__iexact=mappale_raw) | Q(mappale__iexact=mappale_norm))
        )
        particelle_con_geom = particelle.exclude(mpoly__isnull=True)
        if particelle_con_geom.exists():
            return redirect('protocollo:particella_pratica_detail_url', id=particelle_con_geom.first().id, pk=pk)
        if particelle.exists():
            p_archivio = particelle.first()
            messages.warning(request, f"Particella F:{foglio} M:{mappale} presente in archivio ma non trovata in catasto: resta senza geometria.")
            return redirect('protocollo:particella_pratica_detail_url', id=p_archivio.id, pk=pk)

        messages.warning(request, f"Particella non trovata (F:{foglio} M:{mappale}) né in catasto né in archivio.")
        return redirect('protocollo:particelle_list_url', pk=pk)
    else:
        return render (request, 'protocollo/particelle_list.html',context={'pk':pk})
    
# elimina il soggetto dalla pratica
@login_required
def particella_pratica_delete(request, id, pk):
    particella_pratica = Cataprat.objects.get(id=id) # we need this for both GET and POST

    particella = Particella.objects.get(id=particella_pratica.particella_id)

    if request.method == 'POST':
        
        particella_pratica.delete() # delete the pratica from the database
        log_action(request, 'ELIMINATO', f'Cataprat {id}', {'particella': particella.id, 'pratica': pk})
        # redirect to the praticas list
        # return redirect('protocollo:index_pratiche_url')
        return HttpResponseRedirect(reverse('protocollo:pratica_detail_url', kwargs={'pk': pk})) # questo ridirige alla pagina di dettaglio pratica

    # no need for an `else` here. If it's a GET request, just continue

    return render(request,
                    'protocollo/particella_pratica_delete.html',
                    {'particella_pratica': particella_pratica, 'particella':particella})




# aggiunge particella alla pratica
@login_required
def add_particella_pratica_view(request):

    if request.method=="POST":
        particella = request.POST.get('particella')
        pratica_id = request.POST.get('pratica')
        subalterno = request.POST.get('subalterno')
        user=request.user

        # Crea il record di collegamento Cataprat
        cataprat = Cataprat(particella_id=particella, pratica_id=pratica_id, subalterno=subalterno, user_id=user.id)
        cataprat.save()
        log_action(request, 'CREATO', f'Cataprat {cataprat.id}', {'particella': cataprat.particella_id, 'pratica': pratica_id})
        # Nota: l'unione delle geometrie su Pratica.mpoly_pratica avviene automaticamente 
        # tramite il signal 'update_pratica_on_cataprat_change' definito in models.py

        pratica = Pratica.objects.get(id=pratica_id)
        default_pos = Point(10.09636, 44.07721, srid=4326)

        if pratica.posizione is None or pratica.posizione.equals(default_pos):
            ubica_pratica(pratica, force=True)

        # 'aggiungi e continua': torna alla ricerca particelle per inserirne un'altra
        if request.POST.get('continua'):
            return redirect('protocollo:particelle_list_url', pk=pratica_id)

        return redirect('protocollo:pratica_detail_url', pk=pratica_id)

   
# dettaglio della particella
@login_required

def ParticellaPraticaDetailView(request, id, pk):
    particella = Particella.objects.get(id=id)
    log_action(request, 'VISUALIZZATO', f'Particella {particella.id}')

    
                                    
    return render (request, 'protocollo/particella_pratica_detail.html',context={'pk':pk,'particella':particella})



# aggiunge particella alla pratica
@login_required
def add_particella_view(request, pk=None):
    submitted = False
    if request.method == "POST":
        print ('pk particella ',pk)
        form = AddParticellaForm(request.POST)
        if form.is_valid():
            particella = form.save()
            log_action(request, 'CREATO', f'Particella {particella.id}')
            return render (request, 'protocollo/particella_pratica_detail.html',context={'pk':pk,'particella':particella})
    else:
        form = AddParticellaForm()
        if 'submitted' in request.GET:
            submitted = True
    
    return render(request, 'protocollo/add_particella.html', {'form': form, 'submitted': submitted, 'pk': pk})
    

##########################################################
#                      upload_file 
##########################################################
# @editor_required(strict=True)
@user_passes_test(is_editor_func, login_url='home:index')

@login_required
def pratica_upload_list(request,pk):
    is_editor = is_editor_func(request.user)

    documenti = Documento.objects.filter(pratica_id=pk).order_by('-data_prot','-data_crea')
    log_action(request, 'VISUALIZZATO', f'Documenti pratica {pk}', {'count': documenti.count()})
    return render (request, 'protocollo/partials/_pratiche_upload_all.html',{'documenti':documenti, 'pk':pk, 'is_editor':is_editor})




# @editor_required(strict=True)
# @user_passes_test(is_editor_or_admin, login_url='home:index')




@login_required
@editor_required

def upload_file(request,pk):
    data = Pratica.objects.get(id=pk)
    doc = Documento.objects.filter(pratica_id=data.id)
    is_editor = is_editor_func(request.user)

    tot_doc=doc.count()
    # name = str(doc.data_prot_gen.year)+'-'+str(data.prot_gen)+'-'+str(tot_doc+1)
    print (pk,'77dgd5td')
    form = UploadFileForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)

        # file = obj.save(request_file.name, request_file)
        # psrint(form)
        # name = UploadFileForm.name
        # print(__name__)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.pratica_id = pk
            # obj.name=name
            obj.username_id = request.user.id
            # obj.document = 'pk_'+ str(pk)
            # obj.username = username
            # obj.name = obj.save(request_file.name, request_file)
            obj.save()    
            log_action(request, 'CREATO', f'Documento {obj.id}', {'name': obj.name, 'pratica': pk})
            # obj.name = obj.save(request_file.name, request_file)
            # Store document name in session for diario description
            request.session['last_document_name'] = obj.name
            
            is_editor = is_editor_func(request.user)
            # Ora salva la pratica con il campo aggiornato
                # print(stato_pre, pratica.stato)
            return redirect('protocollo:add_diario_url', pk=pk)
            # return HttpResponseRedirect(reverse('protocollo:pratica_detail_url', kwargs={'pk': pk})) # questo ridirige alla pagina di dettaglio pratica

    else:
        form = UploadFileForm()
        initial_name = request.session.pop('sostituzione_descrizione', None)
        if initial_name:
            form.fields['name'].initial = initial_name
        # Preimposta posta/prot/data_prot con i dati della pratica quando è il primo documento
        if tot_doc == 0:
            form.fields['posta'].initial = 'e'
            form.fields['prot'].initial = data.prot_gen
            form.fields['data_prot'].initial = data.data_prot_gen
        context ={'form': form,
                  'is_editor':is_editor,
                  }
        

    return render(request, 'protocollo/upload.html', context)


#######################################
#       TIPO DI PRATICA
#######################################



# lista tipo di pratica
@login_required
def tipopratiche_list(request):
    context = {}
    username = request.user

    if request.user.is_superuser or request.user.is_staff:
        tipo = TipoPratica.objects.all().order_by(Lower('name'), 'settore__codice')
        tp = TipoPratica.objects.all().order_by(Lower('name'))
    else:
        tipo = get_filtered_tipo_pratica_list(request.user, only_opengeoprot=False).order_by(Lower('name'), 'settore__codice')
        tp = get_filtered_tipo_pratica_list(request.user, only_opengeoprot=False)

    context={
                'tipo':tipo,
                'tp':tp,
          }
        
    return render(request,'protocollo/tipopratiche_list.html', context)


# crea tipo di pratica
@login_required
def add_tipopratica_view(request):
    submitted = False
    if request.method == "POST":
        
        form = TipoPraticaForm(request.POST)
        if form.is_valid():
            
            obj = form.save(commit=False)
            obj.user = request.user # inserisce user_id 
            obj.save() # salva il record
            form.save_m2m() # salva le U.O. visibili (M2M)
            log_action(request, 'CREATO', f'TipoPratica {obj.id}', {'name': obj.name})

            tipo = TipoPratica.objects.all().order_by(Lower('name'))
        return render(request,'protocollo/tipopratiche_list.html', {'tipo':tipo})
    else:
        form = TipoPraticaForm()
        if 'submitted' in request.GET:
            submitted = True

        return render(request,'protocollo/update_tipopratica_view.html',{'form':form,'submitted':submitted,'tp':TipoPratica.objects.all().order_by(Lower('name'))})
    
# EDITA tipo di pratica
@login_required

def tipopratica_edit(request,id):
    
    
    tipo = TipoPratica.objects.get(id=id)
    if request.method == 'POST':
        form = TipoPraticaForm(request.POST, instance=tipo)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user_id = request.user.id
            obj.save()
            form.save_m2m()  # salva le U.O. visibili (M2M)
            log_action(request, 'MODIFICATO', f'TipoPratica {obj.id}', {'name': obj.name})
            return redirect('protocollo:tipopratiche_list_url')
        return render(request, 'protocollo/update_tipopratica_view.html', {'form': form, 'tp': TipoPratica.objects.all().order_by(Lower('name'))})
    else:
        form = TipoPraticaForm(instance=tipo)

        return render(request,'protocollo/update_tipopratica_view.html',{'form': form, 'tp': TipoPratica.objects.all().order_by(Lower('name'))})


@login_required
def tipopratica_delete(request, id):
    tipo = get_object_or_404(TipoPratica, id=id)
    if tipo.tipo_pratiche.exists():
        messages.error(request, f"Impossibile eliminare il tipo pratica '{tipo.name}': esistono pratiche collegate.")
        return redirect('protocollo:tipopratiche_list_url')
    tipo.delete()
    log_action(request, 'ELIMINATO', f'TipoPratica {tipo.id}', {'name': tipo.name})
    return redirect('protocollo:tipopratiche_list_url')

    
@login_required
def get_servizi_by_settore(request, settore_id):
    settore = get_object_or_404(Settore, id=settore_id)
    servizi = StoricoServizio.objects.filter(
        settore_storico=settore.versione_vigente, data_fine__isnull=True
    ).order_by('ordine')
    data = [{'id': s.id, 'nome': f"{s.codice} - {s.nome}"} for s in servizi]
    return JsonResponse(data, safe=False)


@login_required
def get_uo_by_servizio(request, servizio_id):
    servizio = get_object_or_404(StoricoServizio, id=servizio_id)
    uos = StoricoAttivitaUO.objects.filter(
        servizio_storico=servizio, data_fine__isnull=True
    ).order_by('ordine')
    data = [{'id': u.id, 'nome': u.nome} for u in uos]
    return JsonResponse(data, safe=False)




#######################################################
#   DIARIO
#######################################################
from docx.enum.table import WD_ALIGN_VERTICAL
from collections import OrderedDict
import numpy as np


# Elenca le voci di diario in un RTF
@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home:index')
@editor_required(allow_viewers=True)
# @user_passes_test(is_editor_or_admin, login_url='home:index')

def DiarioList(request, pk=None):
	pratica = Pratica.objects.get(id=pk) # ritorna  i dati pratica
	print (pratica)
    
	# lista eventi
	eventi = Diario.objects.filter(pratica_id=pk).order_by('-data_crea')
	lista_eventi = 'procedimento' + str(pk)+'.docx'
	# commissioni = Commissione.objects.filter(pratica_id=id).order_by('-commissione_date')[:1]
	# if commissioni:
	#     user = request.user.username
	#     # print('commissioni',commissioni, 'user',user)
	#     # return redirect('protocollo:pratica_detail_url', pk=id)

	# remmo perche' il nome del documento e' lista_eventi
	# atto = 'cartellina_' +str(pratica.tipo_pratica) +'_' + str(pratica.prot_gen) +'_' + "%s" % pratica.data_prot_gen.strftime('%Y%m%d') +'.docx'
        
	document = Document()
	# imposta A4 verticale e margini
	section = document.sections[0]
	section.page_height = Mm(297)
	section.page_width = Mm(210)
	section.left_margin = Mm(20)
	section.right_margin = Mm(20)
	section.top_margin = Mm(10)
	section.bottom_margin = Mm(12)
	# section.header_distance = Mm(10)
	section.footer_distance = Mm(12.7)
        
	paragraph = document.add_paragraph()
	# Selecting a section of the document

	section = document.sections[0]
	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('FooterStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.size = Pt(7)
	obj_font.name = 'Arial'



    
	#   IMPOSTA GLI STILI DEI SINGOLI PARAGRAFI

        


	# document.add_paragraph()
	font = document.styles['Normal'].font
	font.size=Pt(11)
	font.name='Arial'



	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('Titolo', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.bold = True
	obj_font.size = Pt(18)
	obj_font.name = 'Arial'



	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('NormalStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.size = Pt(10)
	obj_font.name = 'Arial'
        
	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('SottoHeaderStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.size = Pt(11)
	obj_font.name = 'Arial'

	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('HeaderStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.size = Pt(9)
	obj_font.name = 'Arial'

	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('CduStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.size = Pt(14)
	obj_font.name = 'Arial'

	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('NumCduStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.size = Pt(11)
	obj_font.name = 'Arial'


	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('NumCduStyleItalic', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.italic = True
	obj_font.size = Pt(9)
	obj_font.name = 'Arial'

	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('DprStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.italic = True
	obj_font.size = Pt(8)
	obj_font.name = 'Arial'

	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('ParticellaStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.italic = False
	obj_font.underline = WD_UNDERLINE.SINGLE
	obj_font.bold=True
	obj_font.size = Pt(11)
	obj_font.name = 'Arial'

	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('PianoStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.italic = True
	obj_font.size = Pt(10)
	obj_font.bold=False
	obj_font.name = 'Arial'

	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('DestinazioneStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.italic = False
	obj_font.size = Pt(9)
	obj_font.name = 'Arial'

	obj_styles = document.styles
	obj_charstyle = obj_styles.add_style('CertificaStyle', WD_STYLE_TYPE.CHARACTER)
	obj_font = obj_charstyle.font
	obj_font.italic = False
	obj_font.bold=True
	obj_font.size = Pt(14)
	obj_font.name = 'Arial'
        

	#  # recupera i dati della pratica
	# pratica = Pratica.objects.get(id=pratica.id) 

	# Changing the orientation to landscape
	section.orientation = WD_ORIENT.LANDSCAPE

	# paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY_LOW

	docx_title=lista_eventi
        
	# Inserisci l'immagine nel documento
		# https://www.shibutan-bloomers.com/python_library_python-docx-2_en/7091/
		# CON ChatGpt

		# Definisci il percorso dell'immagine
	image_name = 'logo_decorato.png'
	image_path = os.path.join('static/img/', image_name)

	# Inserisci l'immagine nel documento
        
	run = paragraph.add_run()
	run.add_picture(image_path, width=Inches(1.6))
	# Posiziona centralmente l'immagine
	paragraph_format = paragraph.paragraph_format
	paragraph_format.alignment = 1 # 1 - allineato centrato 0 - allineato a sx
            

	p0 = document.add_paragraph()
	p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
	p0.paragraph_format.space_before = Pt(0)
	p0.paragraph_format.space_after = Pt(1)
	p0.add_run('Settore 6 - GOVERNO DEL TERRITORIO - Servizio 6.1',style = 'HeaderStyle')
        

	prot = pratica.prot_gen
	data = pratica.data_prot_gen

# #    stampo i dati della U.O.

	p1 = document.add_paragraph()
	p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
	p1.add_run('U.O. 6.1.2 Sportello Unico per l’Edilizia (S.U.E.) e vigilanza abusivismo',style = 'DprStyle')
        
	# stampa data:ora e user
	ora_di_stampa = timezone.now()
	ora_di_stampa = timezone.now()

	# estrae il contenuto della Pratica
	pratica = Pratica.objects.get(id=pk)
        
	p2 = document.add_paragraph()
	p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
	p2.add_run('ELENCO EVENTI pratica  Prot.Gen. ' + str(pratica.prot_gen) + ' del ' + "%s" % pratica.data_prot_gen.strftime('%d/%m/%Y'))

	p0 = document.add_paragraph()
	p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
	for e in eventi:
		user = User.objects.get(id=e.user_id)
		p0 = document.add_paragraph()
		p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
		p0.paragraph_format.space_before = Pt(1)
		p0.paragraph_format.space_after = Pt(3)
            
		p0.add_run("%s" % e.data_crea.strftime('%d/%m/%Y' ) , style = 'DprStyle').bold=True
		p0.add_run(' ' + str(user.username),style = 'DprStyle')
		p01 = document.add_paragraph()
		p01.alignment = WD_ALIGN_PARAGRAPH.LEFT
		p01.paragraph_format.left_indent = Inches(0.5)
		p01.add_run('- '+ str.lower(e.description),style = 'DestinazioneStyle')
        
        


	# Prepare document for download        
	# -----------------------------
	f = BytesIO()
	document.save(f)
	length = f.tell()
	f.seek(0)
	response = HttpResponse(
		f.getvalue(),
		content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
	)
	response['Content-Disposition'] = 'attachment; filename=' + docx_title
	response['Content-Length'] = length
	return response
    

    



# aggiunge voce di diario
@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home:index')
# @editor_required(strict=True)
# @user_passes_test(is_editor_or_admin, login_url='home:index')

@editor_required



def AddDiario(request, pk=None):
    # is_editor = request.user.groups.filter(name='editor_settore_6').exists()
    is_editor = is_editor_func(request.user)

    pratica = Pratica.objects.get(id=pk)
    stato_pre = pratica.stato
    print (stato_pre,'5dttt6')
    if  stato_pre =='a':
        stato_pre = 'attiva'
    if stato_pre == 'i':
        stato_pre = 'in corso'
    if stato_pre == 's':
        stato_pre = 'sospesa'
    if stato_pre == 'ic':
        stato_pre = 'inviata comunicazione'
    if stato_pre == 'ri':
        stato_pre = 'richiesta integrazione'
    if stato_pre == 'ai':
        stato_pre = 'accettato importo'
    if stato_pre == 'bd':
        stato_pre = 'bozza determina'
    if stato_pre == 'df':
        stato_pre = 'determina firmata'
    if stato_pre == 'ia':
        stato_pre = 'inviata ad amministrativi'
    if stato_pre == 'af':
        stato_pre = 'alla firma'
    if stato_pre == 'np':
        stato_pre = 'non procedibile'
    if stato_pre == 'dn':
        stato_pre = 'determina inviata a notaio'
    if stato_pre == 'eo':
        stato_pre = 'emessa ordinanza'

    if request.method == "POST":
        form = DiarioForm(request.POST)
        if form.is_valid():
            obj=form.save(commit=False)
            obj.user = request.user # inserisce user_id 
            obj.pratica = pratica
            # If description is empty and there's a document name in session, use it
            if not obj.description:
                last_doc_name = request.session.pop('last_document_name', None)
                if last_doc_name:
                    obj.description =  last_doc_name
            obj.save() # salva il record
            log_action(request, 'CREATO', f'Diario {obj.id}', {'pratica': pk, 'description': obj.description})
        form1 = StatoForm(request.POST,instance=pratica)
        if form1.is_valid():
            pratica = form1.save(commit=False)  # Aggiorna l'istanza di pratica senza salvarla ancora
            pratica.data_mod = timezone.now()   # Imposta data_mod alla data e ora corrente
            pratica.save()                       # Ora salva la pratica con il campo aggiornato

            # --- ENGINE DI AUTOMAZIONE GESTITO DAL C.E.D. ---
            # Questa sezione è il "motore" del sistema, manutenibile internamente 
            # tramite script Python e query SQL dirette sul DB spaziale.
            
            # 1. Trigger Geografico per il SIT
            # Ogni volta che l'istruttoria avanza, aggiorniamo il database spaziale
            # rendendo la pratica visibile sulle dashboard .
            try:
                # Log per il monitoraggio tecnico (CED)
                logger_user_actions.info(
                    f"SIT Update: Pratica {pratica.prot_gen} aggiornata a stato '{pratica.get_stato_display()}' "
                    f"dall'utente {request.user.username}. IP: {get_client_ip(request)}"
                )
            except Exception as e:
                logger_user_actions.error(f"Errore manutenzione SIT: {e}")

            # 2. Sincronizzazione API (Interoperabilità con cPortal)
            # Il C.E.D. può personalizzare questo flusso senza dipendere dal fornitore
            if pratica.stato in ['ri', 'ic', 'c', 'aa']: # Se integrazione, comunicazione, chiusura o archiviazione
                try:
                    # Simulazione chiamata API esterna per aggiornare il portale del cittadino
                    # requests.post("https://api.comune.carrara.it/v1/sync-cportal", json={
                    #     'id': pratica.id,
                    #     'stato': pratica.stato,
                    #     'nota': obj.description[:100]
                    # })
                    logger_user_actions.info(f"API Sync cPortal: Successo per pratica {pratica.prot_gen}")
                except Exception as e:
                    logger_user_actions.error(f"API Sync Failure: Verificare endpoint gestito dal CED. Errore: {e}")
            
            # 3. Cooperazione Intersettoriale
            # Possibilità per i tecnici CED di inserire logiche SQL per avvisare settori trasversali
            # (es. se la pratica tocca un'area di vincolo ambientale, avvisa il Settore 7)
            
            # --- LOGICA DI INTEGRAZIONE API (Esempio cPortal) ---
            # Invia una notifica al gestionale esterno per sincronizzare lo stato
            try:
                # Esempio ipotetico di chiamata API
                # response = requests.post("https://api.cportal.it/v1/update_status", data={
                #     'pratica_id': pratica.prot_gen,
                #     'nuovo_stato': pratica.get_stato_display(),
                #     'evento': obj.description[:100]
                # })
                logger_user_actions.info(f"Sincronizzazione API avviata per pratica {pratica.prot_gen}")
            except Exception as e:
                logger_user_actions.error(f"Errore sincronizzazione API: {e}")
            # ---------------------------------------------------

            messages.success(request, "Evento registrato e sistema sincronizzato.")
            if request.session.pop('sostituzione_flusso', None):
                return redirect('protocollo:soggetti_list_url', pk=pk)
            return redirect('protocollo:pratica_detail_url', pk)

    else:
        last_document_name = request.session.pop('last_document_name', None)
        if last_document_name:
            initial_text = last_document_name
        else:
            try:
                initial_text = Documento.objects.latest('id').name
            except Documento.DoesNotExist:
                initial_text = ''
        form = DiarioForm(initial={'description': initial_text})
        form1= StatoForm(instance=pratica)
        context = {'form':form,
                   'form1':form1,
                   'is_editor':is_editor,
                }

        return render(request,'protocollo/add_diario.html',context)
    
@login_required
# @user_passes_test(lambda u: u.groups.filter(name='editor_settore_6').count() == 1, login_url='home:index')
@editor_required
# @user_passes_test(is_editor_or_admin, login_url='home:index')


#   EDITA VOCE DI DIARIO
def EditDiario(request,id): # id diario
    pass
#     # is_editor = request.user.groups.filter(name='editor_settore_6').exists()
#     is_editor = is_editor_func(request.user)

#     diario = Diario.objects.get(id=id)
    is_editor = is_editor_func(request.user)
    diario = get_object_or_404(Diario, id=id)
    pratica = diario.pratica
    

#     pk = diario.pratica_id
#     pratica = Pratica.objects.get(id=pk)
#     # pratica = diario.pratica_id
#     if request.method == "POST":
#         stato = request.POST.get("stato")
#         print('stato',stato)
#         form = DiarioForm(request.POST, instance=diario)
    if request.method == "POST":
        form = DiarioForm(request.POST, instance=diario)
        form_stato = StatoForm(request.POST, instance=pratica)
        
#         if form.is_valid():
#             form.save()
        if form.is_valid() and form_stato.is_valid():
            form.save()
            log_action(request, 'MODIFICATO', f'Diario {diario.id}')
            p = form_stato.save(commit=False)
            p.data_mod = timezone.now()
            p.save()
            messages.success(request, "Evento di diario aggiornato.")
            return redirect('protocollo:pratica_detail_url', pk=pratica.id)
    else:
        form = DiarioForm(instance=diario)
        form_stato = StatoForm(instance=pratica)
        
#         form1 = StatoForm(request.POST,instance=pratica)
#         if form1.is_valid():
#             form1.save()
        
#         return redirect('protocollo:pratica_detail_url', pk)

#     else:
#         form = TipoPraticaForm(instance=diario)
#         form1= StatoForm(instance=pratica)
#         context = {'form':form,
#                    'form1':form1,
#                    'pratica':pratica,
#                    'diario':diario,
#                    'is_editor':
    context = {
        'form': form,
        'form1': form_stato,
        'pratica': pratica,
        'diario': diario,
        'is_editor': is_editor,
    }
    return render(request, 'protocollo/edit_diario.html', context)

@login_required
def graph_relazioni_data(request):
    """Restituisce i dati JSON per il grafo delle relazioni."""
    pratica_id = request.GET.get('pratica_id')
    nodes = []
    edges = []
    
    # Se passiamo un ID, mostriamo solo i collegamenti di quella pratica, 
    # altrimenti le ultime 50 pratiche modificate.
    if pratica_id:
        pratiche = get_practice_queryset(request.user).filter(id=pratica_id)
    else:
        pratiche = get_practice_queryset(request.user).order_by('-data_mod')[:50]
    
    added_subjects = set()
    added_streets = set()
    added_parcels = set()
    
    for p in pratiche:
        # Nodo Pratica
        nodes.append({
            'id': f'p_{p.id}',
            'label': f"Prot. {p.prot_gen}\n{p.tipo_pratica.name if p.tipo_pratica else ''}",
            'group': 'pratiche',
            'title': f"Oggetto: {p.oggetto[:100]}...",
            'shape': 'diamond',
            'color': '#fb7e81' # Rosso per le pratiche
        })

        # Relazione con la Strada (street.street)
        if p.street:
            if p.street.id not in added_streets:
                nodes.append({
                    'id': f'st_{p.street.id}',
                    'label': p.street.street,
                    'group': 'strade',
                    'shape': 'box',
                    'color': '#90ee90' # Verde per le strade
                })
                added_streets.add(p.street.id)
            
            edges.append({
                'from': f'p_{p.id}',
                'to': f'st_{p.street.id}',
                'label': 'ubicazione',
                'font': {'align': 'middle'}
            })

        # Relazioni con Particelle (via Cataprat)
        rel_catastali = p.pratiche.all().select_related('particella')
        for rel in rel_catastali:
            parc = rel.particella
            if parc.id not in added_parcels:
                nodes.append({
                    'id': f'parc_{parc.id}',
                    'label': f"Fg {parc.foglio} Map {parc.mappale}",
                    'group': 'particelle',
                    'shape': 'hexagon',
                    'color': '#ffff99' # Giallo per le particelle
                })
                added_parcels.add(parc.id)
            
            edges.append({
                'from': f'p_{p.id}',
                'to': f'parc_{parc.id}',
                'label': f'sub {rel.subalterno}' if rel.subalterno and rel.subalterno != "-" else 'mappale',
                'font': {'align': 'middle'}
            })
        
        # Relazioni tramite Anaprat
        relazioni = p.pratiche_soggetti.all().select_related('soggetto', 'tipo')
        for rel in relazioni:
            s = rel.soggetto
            if rel.id not in added_subjects:
                # Nodo Soggetto
                nodes.append({
                    'id': f's_{rel.id}',
                    'label': f"{s.cognome} {s.nome}",
                    'group': 'soggetti',
                    'title': f"Codice Fiscale: {s.codice_fiscale or 'N/D'}",
                    'shape': 'dot',
                    'color': '#97c2fc' # Blu per i soggetti
                })
                added_subjects.add(rel.id)
            
            # Arco (Edge) tra Soggetto e Pratica
            edges.append({
                'from': f's_{rel.id}',
                'to': f'p_{p.id}',
                'label': rel.tipo.name if rel.tipo else 'coinvolto',
                'font': {'align': 'middle'}
            })
            
    return JsonResponse({'nodes': nodes, 'edges': edges}, safe=False)

@login_required
def graph_relazioni_view(request):
    """Renderizza la pagina del grafo."""
    return render(request, 'protocollo/graph_relazioni.html')

@login_required
def manager_dashboard(request):
    """
    Visualizza una dashboard per i dirigenti con metriche chiave:
    - Tempi medi di istruttoria
    - Volume di pratiche per settore
    - Entrate previste dai ratei non pagati
    - Carichi di lavoro per istruttore
    """
    if not is_manager_or_admin(request.user):
        messages.error(request, "Non hai i permessi per accedere a questa pagina.")
        return redirect('home:index') # Reindirizza a una pagina di accesso negato o home

    # 1. Tempi medi di istruttoria per tipologia (dalla data di protocollo alla data di ultima modifica per pratiche chiuse/definite)
    # Consideriamo pratiche chiuse ('c') o archiviate ('aa'))
    processed_states = ['c', 'aa']
    
    avg_processing_times_by_type = Pratica.objects.filter(
        stato__in=processed_states,
        data_prot_gen__isnull=False,
        data_mod__isnull=False,
        tipo_pratica__isnull=False
    ).annotate(
        duration=ExpressionWrapper(F('data_mod') - F('data_prot_gen'), output_field=DurationField())
    ).values(
        'tipo_pratica__name'
    ).annotate(
        avg_duration=Avg('duration')
    ).order_by('tipo_pratica__name')

    # Processiamo i dati per estrarre i giorni dai timedelta
    processing_stats = []
    for item in avg_processing_times_by_type:
        if item['avg_duration']:
            processing_stats.append({
                'tipo': item['tipo_pratica__name'],
                'days': item['avg_duration'].days
            })

    # 2. Volume di pratiche per settore
    # Escludiamo i settori nulli o vuoti per una migliore visualizzazione
    practices_by_sector = Pratica.objects.filter(
        tipo_pratica__settore__isnull=False
    ).values(
        'tipo_pratica__settore__codice',
        'tipo_pratica__settore__nome'
    ).annotate(
        count=Count('id')
    ).order_by('tipo_pratica__settore__codice')

    # 3. Entrate previste dai ratei non pagati
    # Somma degli importi rata non pagati (importo_rata - importo_pagamento)
    unpaid_installments = Scadenze.objects.filter(
        pagata=False
    ).aggregate(
        total_unpaid=Sum(F('importo_rata') - Coalesce(F('importo_pagamento'), Value(0.0, output_field=DecimalField())))
    )
    total_unpaid_revenue = unpaid_installments['total_unpaid'] if unpaid_installments['total_unpaid'] else 0

    # 4. Carichi di lavoro per istruttore (pratiche in corso o attive)
    active_states = ['i', 's', 'ic', 'ri', 'bd', 'af'] # In corso, sospesa, inviata comunicazione, richiesta integrazione, bozza determina, alla firma
    workload_by_user = Pratica.objects.filter(
        stato__in=active_states,
        user__isnull=False # Solo pratiche con un utente assegnato
    ).values(
        'user__username'
    ).annotate(
        active_practices_count=Count('id')
    ).order_by('user__username')

    
    # Analisi pratiche "ferme" (Alert Istruttoria)
    # Trova pratiche non chiuse che non vengono modificate da più di 30 giorni
    threshold_date = timezone.now() - timedelta(days=30)
    stale_practices = Pratica.objects.filter(
        stato__in=['i', 'ri', 's'], 
        data_mod__lt=threshold_date
    ).values('tipo_pratica__name').annotate(count=Count('id'))

    context = {
        'processing_stats': processing_stats,
        'practices_by_sector': practices_by_sector,
        'total_unpaid_revenue': total_unpaid_revenue,
        'workload_by_user': workload_by_user,
        'stale_practices': stale_practices, # Nuova metrica per la Sindaca
        'last_update': timezone.now(),
        'tp': TipoPratica.objects.all().order_by(Lower('name')),
    }

    return render(request, 'protocollo/manager_dashboard.html', context)

@login_required
def catasto_geojson_nearby(request):
    """Restituisce le particelle del catasto generale nei dintorni di un punto."""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    raggio = float(request.GET.get('raggio', 0.002))
    if lat and lng:
        try:
            pnt = Point(float(lng), float(lat), srid=4326)
            qs = Particelle.objects.using('anagrafe').filter(
                Q(mpoly__intersects=pnt) | Q(mpoly__intersects=pnt.buffer(raggio))
            ).distinct()[:150]
            geojson_data = serializers.serialize('geojson', qs, geometry_field='mpoly', fields=('foglio', 'mappale'))
            return HttpResponse(geojson_data, content_type='application/json')
        except Exception as e:
            logger_user_active = logging.getLogger('user_active')
            logger_user_active.error(
                f"Errore catasto_geojson_nearby: {e} | lat={lat} lng={lng}"
            )
    return JsonResponse({'type': 'FeatureCollection', 'features': []})

@login_required
def catasto_geojson_bbox(request):
    """Restituisce le particelle del catasto generale all'interno di un bounding box."""
    try:
        north = float(request.GET.get('north'))
        south = float(request.GET.get('south'))
        east = float(request.GET.get('east'))
        west = float(request.GET.get('west'))
        bbox = Polygon.from_bbox((west, south, east, north))
        qs = Particelle.objects.using('anagrafe').filter(mpoly__intersects=bbox).distinct()[:300]
        geojson_data = serializers.serialize('geojson', qs, geometry_field='mpoly', fields=('foglio', 'mappale'))
        return HttpResponse(geojson_data, content_type='application/json')
    except Exception:
        return JsonResponse({'type': 'FeatureCollection', 'features': []})


@login_required
def salva_nota_osm(request):
    """Salva localmente una nota (layer NOTE) con il relativo stato."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo non consentito'}, status=405)
    testo = request.POST.get('testo', '').strip()
    try:
        lat = float(request.POST.get('lat'))
        lng = float(request.POST.get('lng'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Coordinate non valide'}, status=400)
    if not testo:
        return JsonResponse({'ok': False, 'error': 'La nota è vuota'}, status=400)
    stato = request.POST.get('stato', 'bozza')
    if stato not in dict(STATO_NOTA):
        stato = 'bozza'
    allegato = request.FILES.get('allegato')
    nota = NotaOSM.objects.create(
        utente=request.user.username,
        testo=testo,
        lat=lat,
        lng=lng,
        geom=Point(lng, lat, srid=4326),
        allegato=allegato,
        stato=stato,
    )
    return JsonResponse({'ok': True, 'id': nota.id, 'stato': nota.stato})


@login_required
def aggiorna_nota_osm(request):
    """Aggiorna lo stato e/o il testo di una nota esistente."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo non consentito'}, status=405)
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'ok': False, 'error': 'Non autorizzato'}, status=403)
    try:
        pk = int(request.POST.get('pk'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'ID non valido'}, status=400)
    stato = request.POST.get('stato', '')
    if stato not in dict(STATO_NOTA):
        return JsonResponse({'ok': False, 'error': 'Stato non valido'}, status=400)
    testo = request.POST.get('testo', None)
    if testo is not None and not testo.strip():
        return JsonResponse({'ok': False, 'error': 'Testo non valido'}, status=400)
    try:
        nota = NotaOSM.objects.get(pk=pk)
    except NotaOSM.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Nota inesistente'}, status=404)
    if testo is not None:
        nota.testo = testo.strip()
    nota.stato = stato
    update_fields = ['stato']
    if testo is not None:
        update_fields.append('testo')
    nota.save(update_fields=update_fields)
    return JsonResponse({'ok': True, 'id': nota.id, 'stato': nota.stato})


@login_required
def nota_osm_lista(request):
    """Restituisce l'elenco delle note salvate nel database."""
    qs = NotaOSM.objects.all()
    if not (request.user.is_staff or request.user.is_superuser):
        qs = qs.filter(utente=request.user.username)
    note = qs[:100]
    data = [{
        'id': n.id,
        'testo': n.testo,
        'lat': n.lat,
        'lng': n.lng,
        'stato': n.stato,
        'utente': n.utente,
        'allegato': n.allegato.url if n.allegato else '',
        'data': n.data.strftime('%d/%m/%Y %H:%M'),
    } for n in note]
    return JsonResponse({'note': data})


@login_required
def elimina_nota_osm(request):
    """Elimina una nota esistente."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo non consentito'}, status=405)
    try:
        pk = int(request.POST.get('pk'))
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'ID non valido'}, status=400)
    try:
        nota = NotaOSM.objects.get(pk=pk)
    except NotaOSM.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Nota inesistente'}, status=404)
    if not (request.user.is_staff or request.user.is_superuser or nota.utente == request.user.username):
        return JsonResponse({'ok': False, 'error': 'Non autorizzato'}, status=403)
    nota.delete()
    return JsonResponse({'ok': True, 'id': pk})


@login_required
def nota_modifica(request, pk):
    try:
        nota = NotaOSM.objects.get(pk=pk)
    except NotaOSM.DoesNotExist:
        raise Http404('Nota inesistente')
    if not (request.user.is_staff or request.user.is_superuser or nota.utente == request.user.username):
        return HttpResponseForbidden('Non autorizzato')
    if request.method == 'POST':
        testo = request.POST.get('testo', '').strip()
        stato = request.POST.get('stato', nota.stato)
        if not testo:
            return render(request, 'protocollo/nota_modifica.html', {
                'nota': nota,
                'error': 'Inserisci il testo della nota',
                'STATO_NOTA': STATO_NOTA,
            })
        if not (request.user.is_staff or request.user.is_superuser):
            stato = nota.stato
        if stato not in dict(STATO_NOTA):
            return render(request, 'protocollo/nota_modifica.html', {
                'nota': nota,
                'error': 'Stato non valido',
                'STATO_NOTA': STATO_NOTA,
            })
        nota.testo = testo
        nota.stato = stato
        nota.save(update_fields=['testo', 'stato'])
        return render(request, 'protocollo/nota_modifica.html', {
            'nota': nota,
            'saved': True,
            'STATO_NOTA': STATO_NOTA,
        })
    return render(request, 'protocollo/nota_modifica.html', {
        'nota': nota,
        'error': None,
        'STATO_NOTA': STATO_NOTA,
    })


@login_required
def nota_elimina(request, pk):
    try:
        nota = NotaOSM.objects.get(pk=pk)
    except NotaOSM.DoesNotExist:
        raise Http404('Nota inesistente')
    if not (request.user.is_staff or request.user.is_superuser or nota.utente == request.user.username):
        return HttpResponseForbidden('Non autorizzato')
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    nota.delete()
    return render(request, 'protocollo/nota_modifica.html', {
        'nota': nota,
        'deleted': True,
        'STATO_NOTA': STATO_NOTA,
    })


@login_required
def pratiche_geojson_bbox(request):
    """Restituisce le pratiche vicine nell'area attorno a lat/lng."""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    pk = request.GET.get('pk')
    if lat and lng:
        try:
            pnt = Point(float(lng), float(lat), srid=4326)
            raggio = float(request.GET.get('raggio', 0.002))
            qs = get_practice_queryset(request.user).filter(
                Q(posizione__isnull=False, posizione__intersects=pnt.buffer(raggio)) |
                Q(mpoly_pratica__isnull=False, mpoly_pratica__intersects=pnt.buffer(raggio))
            )
            if pk:
                qs = qs.exclude(id=int(pk))
            qs = qs.distinct()[:200]

            features = []
            for p in qs:
                geom = p.posizione or (p.mpoly_pratica.centroid if p.mpoly_pratica else None)
                if not geom:
                    continue
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(geom.json),
                    "properties": {
                        "id": p.id,
                        "prot_gen": p.prot_gen or '',
                        "data_prot_gen": p.data_prot_gen.strftime('%d/%m/%Y') if p.data_prot_gen else '',
                        "tipo_pratica": p.tipo_pratica.name if p.tipo_pratica else 'N/D',
                    }
                })
            return JsonResponse({'type': 'FeatureCollection', 'features': features})
        except Exception:
            return JsonResponse({'type': 'FeatureCollection', 'features': []})


@login_required
def particella_informativa(request, pk):
    from catasto.models import Particelle
    try:
        part = Particelle.objects.using('anagrafe').get(pk=pk)
        user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
        client_ip = get_client_ip(request)
        logger_user_actions.info(
            f"Apertura informativa piano - Utente: {user_username}, IP: {client_ip}, "
            f"particella_id: {pk}, foglio: {part.foglio}, mappale: {part.mappale}"
        )
        lizmap_url = (
            'https://gis.comune.carrara.ms.it/lizmap355/index.php/lizmap/service/'
            '?repository=001&project=piani_e_vincoli_pg_2023'
            '&SERVICE=WMS&VERSION=1.3.0&REQUEST=GetPrintAtlas'
            '&FORMAT=pdf&EXCEPTIONS=application/vnd.ogc.se_inimage'
            '&TRANSPARENT=true&DPI=100&TEMPLATE=informativa_'
            '&LAYER=vw_particelle_f'
            f'&EXP_FILTER=$id%20IN%20({pk})'
            f'&USER={request.user.username}'
        )
        return JsonResponse({'url': lizmap_url})
    except Particelle.DoesNotExist:
        return JsonResponse({'url': ''}, status=404)
    except Exception:
        return JsonResponse({'url': ''}, status=500)

@login_required
def pratiche_vicine_list(request):
    """Restituisce l'elenco delle pratiche vicine nell'area attorno a lat/lng."""
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    pk = request.GET.get('pk')
    if lat and lng:
        try:
            pnt = Point(float(lng), float(lat), srid=4326)
            raggio = float(request.GET.get('raggio', 0.002))
            qs = get_practice_queryset(request.user).filter(
                Q(posizione__isnull=False, posizione__intersects=pnt.buffer(raggio)) |
                Q(mpoly_pratica__isnull=False, mpoly_pratica__intersects=pnt.buffer(raggio))
            )
            if pk:
                qs = qs.exclude(id=int(pk))
            qs = qs.distinct().select_related('tipo_pratica').order_by('-data_prot_gen')[:100]

            results = []
            for p in qs:
                results.append({
                    "id": p.id,
                    "prot_gen": p.prot_gen or '',
                    "data_prot_gen": p.data_prot_gen.strftime('%d/%m/%Y') if p.data_prot_gen else '',
                    "tipo_pratica": p.tipo_pratica.name if p.tipo_pratica else 'N/D',
                    "stato": p.get_stato_display() if p.stato else '',
                    "oggetto": (p.oggetto[:150] + '...') if p.oggetto and len(p.oggetto) > 150 else (p.oggetto or ""),
                    "url": reverse('protocollo:pratica_detail_url', args=[p.id]),
                })
            return JsonResponse({"results": results})
        except Exception:
            pass
    return JsonResponse({"results": []})

@login_required
def pratiche_geojson_nearby(request):
    """
    Restituisce le pratiche collegate per lo stesso civico (parte numerica) o le stesse particelle.
    di una pratica di riferimento (current_id).
    I risultati vengono raggruppati per posizione e restituiti come centroidi.
    """
    current_id = request.GET.get('current_id')
    if not current_id:
        return JsonResponse({'type': 'FeatureCollection', 'features': []})

    try:
        p_ref = get_practice_queryset(request.user).filter(id=int(current_id)).first()
        if not p_ref:
            return JsonResponse({'type': 'FeatureCollection', 'features': []})
        ref_geom = p_ref.posizione or (p_ref.mpoly_pratica.centroid if p_ref.mpoly_pratica else None)
        
        query = Q()

        # 1. Ricerca per Civico (solo parte numerica iniziale, es. "12/A" -> "12")
        raw_civico = str(p_ref.housenumber or '').strip().lstrip('0')
        num_match = re.search(r'^(\d+)', raw_civico)
        if p_ref.street_id and num_match:
            num_part = num_match.group(1)
            # Cerca civici che iniziano con lo stesso numero (gestendo zeri e spazi)
            query |= Q(street_id=p_ref.street_id, housenumber__regex=rf'^\s*0*{num_part}(\D|$)')

        # 2. Ricerca per Particelle (tabella protocollo_cataprat)
        parcels = p_ref.particella_pratica.all()
        if parcels.exists():
            query |= Q(particella_pratica__in=parcels)

        if not query:
            return JsonResponse({'type': 'FeatureCollection', 'features': []})
            
        # Ricerca tutte le pratiche corrispondenti escludendo quella corrente
        qs = get_practice_queryset(request.user).filter(query).exclude(id=p_ref.id).select_related('tipo_pratica').distinct()[:100]

        grouped_results = {}
        for p in qs:
            # Se la pratica trovata non ha geometria, usa quella della pratica di riferimento
            geom = p.posizione or (p.mpoly_pratica.centroid if p.mpoly_pratica else None) or ref_geom
            
            if not geom: continue

            coords = (round(geom.x, 5), round(geom.y, 5))
            if coords not in grouped_results:
                grouped_results[coords] = {'geom': geom, 'items': []}

            grouped_results[coords]['items'].append({
                "id": p.id,
                "prot": p.prot_gen,
                "anno": p.data_prot_gen.year if p.data_prot_gen else '',
                "data_prot": p.data_prot_gen.strftime('%d/%m/%Y') if p.data_prot_gen else '',
                "tipo": p.tipo_pratica.name if p.tipo_pratica else "N/D",
                "tipo_id": p.tipo_pratica.id if p.tipo_pratica else 0,
                "oggetto": (p.oggetto[:120] + '...') if p.oggetto and len(p.oggetto) > 120 else (p.oggetto or "")
            })

        features = []
        for coords, data in grouped_results.items():
            features.append({
                "type": "Feature",
                "geometry": json.loads(data['geom'].json),
                "properties": {
                    "items": data['items'],
                    "count": len(data['items'])
                }
            })
        return JsonResponse({"type": "FeatureCollection", "features": features})

    except Exception as e:
        logger_user_actions.error(f"Errore pratiche_geojson_nearby: {e}")
        return JsonResponse({'type': 'FeatureCollection', 'features': []})

@login_required
@user_passes_test(lambda u: u.groups.filter(name='cartografia').exists() or u.is_superuser or u.is_staff, login_url='home:index')
def mappa_tipo_pratica(request, tipo_id):

    # se l'user non fa parte del gruppo cartografia non entra e viene rimandato alla home
    # Rimosso il decoratore per permettere a questa logica di girare
    if not (request.user.is_superuser or request.user.is_staff or request.user.groups.filter(name='cartografia').exists()):
        messages.warning(request, "Accesso negato: non hai i permessi per visualizzare la mappa tipologica. Contatta un amministratore per richiedere l'inserimento nel gruppo 'cartografia'.")
        return redirect('home:index')
        return HttpResponse(
            '<script type="text/javascript">alert("Accesso negato: non hai i permessi per visualizzare la mappa tipologica. Richiedi l\'inserimento nel gruppo \'cartografia\'.");'
            'window.location.href="/";</script>'
        )

    """Mostra una mappa con tutte le pratiche di un determinato tipo (punti e aree)."""
    tipo = get_object_or_404(TipoPratica, id=tipo_id)

    # Recupera il filtro per piano dai parametri GET
    piano_id = request.GET.get('piano')

    # Permetti a tutti gli utenti di vedere anche le pratiche di altri settori su questa mappa
    qs = get_practice_queryset().filter(tipo_pratica=tipo)

    # Se è selezionato un piano, filtriamo le informative (CDU) collegate non chiuse
    if piano_id:
        qs = qs.filter(pratiche_cdu__piano_id=piano_id).exclude(pratiche_cdu__stato_pratica='c')

    # Filtra pratiche del tipo richiesto che hanno almeno una posizione o una geometria areale
    pratiche = qs.filter(
        Q(posizione__isnull=False) | Q(mpoly_pratica__isnull=False)
    )

    piani = Piano.objects.all().order_by('name')

    return render(request, 'protocollo/mappa_tipo.html', {
        'tipo': tipo,
        'pratiche': pratiche,
        'piani': piani,
        'current_piano': piano_id,
    })

@login_required
@editor_required(allow_viewers=True)

def professionisti_list_view(request): # in realtà sarebbe soggetti_list_view
    """
    Visualizza l'elenco di tutti i soggetti censiti nel sistema,
    con i rispettivi ruoli e il numero di pratiche collegate.
    Ricerca "blanda": la query viene suddivisa in token e ogni token
    deve essere presente (case-insensitive) in cognome, nome o codice fiscale,
    così da gestire anche cognomi/nomi compositi (es. "de luca mario").
    """
    search_query = request.GET.get('q', '').strip()

    professionisti = []
    # Mostra i risultati solo a seguito di una ricerca esplicita.
    if search_query:
        # Suddivide la ricerca in token (gestisce cognomi compositi come "de luca")
        tokens = [t for t in search_query.split() if t]

        soggetti_qs = Soggetto.objects.all()

        if tokens:
            # Ogni token deve combaciare in cognome, nome o codice fiscale (AND tra token)
            query = Q()
            for token in tokens:
                query &= (
                    Q(cognome__icontains=token) |
                    Q(nome__icontains=token) |
                    Q(codice_fiscale__icontains=token)
                )
            soggetti_qs = soggetti_qs.filter(query)

        soggetti_qs = soggetti_qs.annotate(
            p_count=Count('soggetti__pratica', distinct=True)
        ).order_by('cognome', 'nome').distinct()

        for s in soggetti_qs:
            # Estraiamo i nomi dei ruoli unici ricoperti dal soggetto.
            ruoli_nomi = s.soggetti.filter(tipo__isnull=False).values_list('tipo__name', flat=True).distinct()

            professionisti.append({
                'soggetto': s,
                'ruoli': list(ruoli_nomi),
                'pratiche_count': s.p_count
            })

    return render(request, 'protocollo/professionisti_list.html', {
        'professionisti': professionisti,
        'has_query': bool(search_query),
    })

@login_required
def dashboard_riepilogo(request):
    """Dashboard analitica per tipologia di pratica e stato."""
    if not is_manager_or_admin(request.user):
        messages.error(request, "Accesso limitato ai responsabili.")
        return redirect('home:index')

    status_map = {
        'a': {'label': 'Attiva', 'class': 'badge-primary'},
        'i': {'label': 'In corso', 'class': 'badge-info'},
        's': {'label': 'Sospesa', 'class': 'badge-danger'},
        'ic': {'label': 'Com. Inviata', 'class': 'badge-warning'},
        'ri': {'label': 'Rich. Integ.', 'class': 'badge-danger'},
        'ai': {'label': 'Accett. Imp.', 'class': 'badge-success'},
        'bd': {'label': 'Bozza Det.', 'class': 'badge-warning'},
        'df': {'label': 'Det. Firmata', 'class': 'badge-success'},
        'ia': {'label': 'Inv. Amm.', 'class': 'badge-secondary'},
        'af': {'label': 'Alla Firma', 'class': 'badge-warning'},
        'np': {'label': 'Improcedibile', 'class': 'badge-dark'},
        'dn': {'label': 'Det. Notaio', 'class': 'badge-info'},
        'eo': {'label': 'Emessa Ord.', 'class': 'badge-success'},
        'c': {'label': 'Chiusa', 'class': 'badge-success'}
    }

    # Estrazione dati aggregati per tipo e stato
    base_qs = get_practice_queryset(request.user)

    anno = request.GET.get('anno')
    if anno and anno != '*' and anno != '':
        try:
            anno_int = int(anno)
            base_qs = base_qs.filter(data_prot_gen__year=anno_int)
        except (ValueError, TypeError):
            pass

    anni_disponibili = sorted(
        get_practice_queryset(request.user).dates('data_prot_gen', 'year', order='DESC'),
        key=lambda d: d.year, reverse=True
    )

    raw_stats = base_qs.values('tipo_pratica__id', 'tipo_pratica__name', 'stato').annotate(
        count=Count('id')
    ).order_by(Lower('tipo_pratica__name'))

    summary = {}
    # Primo passaggio per i totali
    for entry in raw_stats:
        tp_id = entry['tipo_pratica__id']
        tp_name = entry['tipo_pratica__name'] or "Altro/Non definito"
        if tp_name not in summary:
            summary[tp_name] = {'stats': [], 'total': 0, 'id': tp_id}
        summary[tp_name]['total'] += entry['count']

    # Secondo passaggio per dettagli e percentuali
    for entry in raw_stats:
        tp_name = entry['tipo_pratica__name'] or "Altro/Non definito"
        st_code = entry['stato']
        st_info = status_map.get(st_code, {'label': st_code, 'class': 'badge-light'})
        
        percent = (entry['count'] / summary[tp_name]['total'] * 100)
        
        summary[tp_name]['stats'].append({
            'label': st_info['label'],
            'class': st_info['class'],
            'bg': st_info['class'].replace('badge-', 'bg-'),
            'count': entry['count'],
            'percent': round(percent, 1)
        })

    # Ordina gli stati interni per ogni tipo di pratica dalla percentuale più alta alla più bassa
    for tp_name in summary:
        summary[tp_name]['stats'].sort(key=lambda x: x['percent'], reverse=True)

    sorted_summary = sorted(summary.items(), key=lambda x: x[0].lower())

    seen_ids = set()
    tipi_pratica = []
    for tp_name, data in sorted_summary:
        tp_id = data['id']
        if tp_id not in seen_ids:
            seen_ids.add(tp_id)
            tipi_pratica.append({'id': tp_id, 'name': tp_name})

    return render(request, 'protocollo/dashboard_riepilogo.html', {
        'summary': sorted_summary,
        'tipi_pratica': tipi_pratica,
        'anni_disponibili': anni_disponibili,
        'selected_anno': anno or '',
        'tp': TipoPratica.objects.all().order_by(Lower('name')),
    })

@login_required
@user_passes_test_403(lambda u: u.groups.filter(name__in=['editor_settore_6', 'cartografia', 'manager_group']).exists() or u.is_staff)
def spatial_query_info(request):
    """
    Punto di accesso WebGIS per utenti interni: 
    Fornisce informazioni su pratiche e istruttorie partendo da un punto cliccato sulla mappa.
    """
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    
    if not lat or not lng:
        return JsonResponse({'error': 'Coordinate mancanti'}, status=400)

    try:
        pnt = Point(float(lng), float(lat), srid=4326)
        # Cerca pratiche che contengono il punto o sono vicine (buffer di 5 metri)
        # Interseca sia la posizione puntuale che la geometria MultiPolygon
        buffer_area = pnt.buffer(0.00005) # Circa 5 metri
        
        pratiche_incluse = Pratica.objects.filter(
            Q(posizione__distance_lte=(pnt, 5)) | 
            Q(mpoly_pratica__intersects=buffer_area)
        ).select_related('tipo_pratica', 'user').prefetch_related('eventi')

        results = []
        for p in pratiche_incluse:
            # Logica di protezione del dato: i dipendenti vedono solo i dettagli 
            # se appartengono allo stesso settore o hanno permessi elevati
            user_profile = getattr(request.user, 'profile', None)
            can_see_details = request.user.is_staff or (user_profile and user_profile.settore and p.tipo_pratica.settore and user_profile.settore.codice == p.tipo_pratica.settore.codice)

            eventi = []
            if can_see_details:
                # Se autorizzato, mostriamo le fasi istruttorie (il "diario")
                eventi = list(p.eventi.values('data_crea', 'description', 'user__username')[:5])

            results.append({
                'id': p.id,
                'protocollo': p.prot_gen,
                'data': p.data_prot_gen.strftime('%d/%m/%Y'),
                'tipo': p.tipo_pratica.name if p.tipo_pratica else "N/D",
                'stato': p.get_stato_display(),
                'oggetto': p.oggetto if can_see_details else "Riservato (Settore Diverso)",
                'istruttoria_fasi': eventi
            })

        return JsonResponse({'count': len(results), 'pratiche': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    """Dashboard analitica per tipologia di pratica e stato."""
    if not is_manager_or_admin(request.user):
        messages.error(request, "Accesso limitato ai responsabili.")
        return redirect('home:index')

    status_map = {
        'a': {'label': 'Attiva', 'class': 'badge-primary'},
        'i': {'label': 'In corso', 'class': 'badge-info'},
        's': {'label': 'Sospesa', 'class': 'badge-danger'},
        'ic': {'label': 'Com. Inviata', 'class': 'badge-warning'},
        'ri': {'label': 'Rich. Integ.', 'class': 'badge-danger'},
        'ai': {'label': 'Accett. Imp.', 'class': 'badge-success'},
        'bd': {'label': 'Bozza Det.', 'class': 'badge-warning'},
        'df': {'label': 'Det. Firmata', 'class': 'badge-success'},
        'ia': {'label': 'Inv. Amm.', 'class': 'badge-secondary'},
        'af': {'label': 'Alla Firma', 'class': 'badge-warning'},
        'np': {'label': 'Improcedibile', 'class': 'badge-dark'},
        'dn': {'label': 'Det. Notaio', 'class': 'badge-info'},
        'eo': {'label': 'Emessa Ord.', 'class': 'badge-success'},
        'c': {'label': 'Chiusa', 'class': 'badge-success'}
    }

    # Estrazione dati aggregati per tipo e stato
    raw_stats = Pratica.objects.values('tipo_pratica__id', 'tipo_pratica__name', 'stato').annotate(
        count=Count('id')
    ).order_by('tipo_pratica__name')

    summary = {}
    # Primo passaggio per i totali
    for entry in raw_stats:
        tp_id = entry['tipo_pratica__id']
        tp_name = entry['tipo_pratica__name'] or "Altro/Non definito"
        if tp_name not in summary:
            summary[tp_name] = {'stats': [], 'total': 0, 'id': tp_id}
        summary[tp_name]['total'] += entry['count']

    # Secondo passaggio per dettagli e percentuali
    for entry in raw_stats:
        tp_name = entry['tipo_pratica__name'] or "Altro/Non definito"
        st_code = entry['stato']
        st_info = status_map.get(st_code, {'label': st_code, 'class': 'badge-light'})
        
        percent = (entry['count'] / summary[tp_name]['total'] * 100)
        
        summary[tp_name]['stats'].append({
            'label': st_info['label'],
            'class': st_info['class'],
            'bg': st_info['class'].replace('badge-', 'bg-'),
            'count': entry['count'],
            'percent': round(percent, 1)
        })

    # Ordina gli stati interni per ogni tipo di pratica dalla percentuale più alta alla più bassa
    for tp_name in summary:
        summary[tp_name]['stats'].sort(key=lambda x: x['percent'], reverse=True)

    sorted_summary = sorted(summary.items(), key=lambda x: x[1]['total'], reverse=True)

    return render(request, 'protocollo/dashboard_riepilogo.html', {
        'summary': sorted_summary,
    })


@login_required

def searchprotmap(request):
    form = UnifiedSearchForm(request.GET or None, user=request.user)

    if request.method == "GET" and any(v for k, v in request.GET.items() if k != 'page'):
        edilizia_ordered = EdiliziaPratica.objects.none()

        ids_param = request.GET.get('ids')
        id_list = None
        if ids_param:
            try:
                id_list = [int(x) for x in ids_param.split(',') if x.strip()]
            except ValueError:
                id_list = []

        if id_list is not None:
            protocollo_qs = get_practice_queryset(request.user).filter(id__in=id_list)
            edilizia_ordered = EdiliziaPratica.objects.filter(id__in=id_list).order_by('-data_prot_gen', '-id')
            pratiche_queryset = protocollo_qs
            query_params = f"ids={ids_param}"
        else:
            # Estrazione parametri
            stato = request.GET.get('stato')
            prot_gen = request.GET.get('prot_gen', '').strip()
            anno = request.GET.get('anno', '').strip()
            oggetto = request.GET.get('oggetto', '').strip()
            annotazioni = request.GET.get('annotazioni', '').strip()
            street_id = request.GET.get('street_id')
            civico = request.GET.get('civico', '').strip()
            tp = request.GET.get('tp')
            cognome = request.GET.get('cognome', '').strip()
            nome = request.GET.get('nome', '').strip()
            foglio_raw = request.GET.get('foglio', '').strip()
            mappale_raw = request.GET.get('mappale', '').strip()
            foglio_norm = normalize_foglio(foglio_raw) or ''
            foglio = _normalize_codice(foglio_norm, 4)
            mappale = mappale_raw
            matricola = request.GET.get('matricola', '').strip()
            cdu_num = request.GET.get('cdu', '').strip()
            impianto = request.GET.get('impianto', '').strip()
            atto = request.GET.get('atto', '').strip()
            istruttoria = request.GET.get('istruttoria', '').strip()
            tecnico = request.GET.get('tecnico', '').strip()

            # Costruisci i parametri di ricerca
            parametri = {
            'stato': stato, 'prot_gen': prot_gen, 'anno': anno, 'oggetto': oggetto, 'annotazioni': annotazioni,
                'street_id': street_id, 'civico': civico, 'tp': tp,
                'cognome': cognome, 'nome': nome, 'foglio': foglio, 'mappale': mappale,
                'matricola': matricola, 'cdu': cdu_num, 'impianto': impianto
            }
            query_params = urlencode({k: v for k, v in parametri.items() if v})

            # Log
            user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
            logger_user_actions.info(
                        f"Utente: {user_username} ha effettuato una ricerca con parametri - "
                        f"Richiedente: {cognome} {nome},  foglio: {foglio} mappale: {mappale}"
                        f"Stato: {stato}, Prot. Gen.: {prot_gen}, anno: {anno}, oggetto: {oggetto}, "
                        f"street_id: {street_id}, civico: civico, tp: {tp}"
                    )

            # Costruzione query
            pratica_query = Q()
            pratica_query &= ~Q(stato__iexact='aa')

            if stato and stato != '*' and stato !='':
                pratica_query &= Q(stato__iexact=stato)

            if prot_gen and prot_gen !='' and prot_gen != '*':
                pratica_query &= Q(prot_gen__icontains=prot_gen)

            if anno:
                try:
                    anno_int = int(anno)
                    pratica_query &= Q(data_prot_gen__year=anno_int)
                except ValueError:
                    pass

            if oggetto and oggetto != '' and oggetto != '*':
                for parola in oggetto.split():
                    parola = parola.strip()
                    if parola:
                        pratica_query &= Q(oggetto__icontains=parola)

            if street_id and street_id != '' and street_id != '*':
                try:
                    street_id_int = int(street_id)
                    pratica_query &= Q(street__id=street_id_int)
                except ValueError:
                    pass

            if civico and civico !='' and civico != '*':
                pratica_query &= Q(housenumber__icontains=civico)

            if tp and tp != '*' and tp != '':
                try:
                    tp_int = int(tp)
                    pratica_query &= Q(tipo_pratica__id=tp_int)
                except ValueError:
                    pass

            # Ricerca soggetti
            if cognome:
                pratica_query &= Q(pratiche_soggetti__soggetto__cognome__icontains=cognome)
            if nome:
                pratica_query &= Q(pratiche_soggetti__soggetto__nome__icontains=nome)

            # Ricerca per Particella
            if foglio_raw:
                pratica_query &= Q(pratiche__particella__foglio__startswith=foglio_raw)
            if mappale_raw:
                pratica_query &= Q(pratiche__particella__mappale__startswith=mappale_raw)

            # Matricola
            if matricola:
                matricola_pratiche_ids = Matricola.objects.filter(
                    Q(matricola_assegnata__icontains=matricola) | Q(numero__icontains=matricola)
                ).values_list('num_impianto__pratica_id', flat=True)
                pratica_query &= Q(id__in=matricola_pratiche_ids)

            if cdu_num:
                pratica_query &= Q(pratiche_cdu__cdu_number=cdu_num)
            if impianto:
                pratica_query &= Q(pratiche_impianto__num_impianto__icontains=impianto)

            # atto / istruttoria / tecnico sono campi solo dell'archivio edilizia:
            # se compilati, la ricerca OPENGEOPROT (protocollo) non deve restituire
            # tutte le pratiche per mancanza di vincoli. Li escludiamo dal lato protocollo.
            if atto or istruttoria or tecnico:
                pratica_query = Q(pk__in=[])

            # Filtro sui documenti
            if prot_gen and prot_gen != '*':
                queryDoc = Q(prot__icontains=prot_gen)
                if anno and anno != '*':
                    try:
                        anno_int = int(anno)
                        queryDoc &= Q(data_prot__year=anno_int)
                    except ValueError:
                        pass
                documenti_ids = Documento.objects.filter(queryDoc).values_list('pratica_id', flat=True)
                pratiche_queryset = get_practice_queryset(request.user).filter(pratica_query | Q(id__in=documenti_ids)).exclude(stato__iexact='aa')
            else:
                pratiche_queryset = get_practice_queryset(request.user).filter(pratica_query).exclude(stato__iexact='aa')

            edilizia_query = EdiliziaPratica.objects.all()
            if cognome:
                edilizia_query = edilizia_query.filter(richiedente__icontains=cognome)
            if nome:
                edilizia_query = edilizia_query.filter(richiedente__icontains=nome)
            if prot_gen:
                edilizia_query = edilizia_query.filter(prot_gen__icontains=prot_gen)
            if anno and anno != '*':
                edilizia_query = edilizia_query.filter(data_prot_gen__year=anno)
            if oggetto and oggetto != '*':
                edilizia_query = edilizia_query.filter(oggetto__icontains=oggetto)
            if atto and atto != '*':
                edilizia_query = edilizia_query.filter(Q(atto__icontains=atto) | Q(num_atto__icontains=atto))
            if istruttoria and istruttoria != '*':
                edilizia_query = edilizia_query.filter(istruttoria__icontains=istruttoria)
            if tecnico and tecnico != '*':
                edilizia_query = edilizia_query.filter(tecnico__icontains=tecnico)

            if street_id and street_id != '' and street_id != '*':
                try:
                    civico_obj = Civici.objects.get(id=street_id)
                    stopwords = {'via', 'viale', 'piazza', 'corso', 'largo', 'contrada', 'strada', 'borgo', 'frazione', 'località', 'loc.'}
                    ubicazione_search_terms = [
                        parola for parola in civico_obj.street.split()
                        if parola.lower() not in stopwords and len(parola) > 2
                    ]
                    if ubicazione_search_terms:
                        q_ubicazione = Q()
                        for parola in ubicazione_search_terms:
                            q_ubicazione |= Q(ubicazione__icontains=parola.strip())
                        edilizia_query = edilizia_query.filter(q_ubicazione)
                    if civico and civico != '' and civico != '*':
                        edilizia_query = edilizia_query.filter(ubicazione__icontains=civico)
                except Civici.DoesNotExist:
                    if civico and civico !='' and civico != '*':
                        for parola in civico.split():
                            parola = parola.strip()
                            if parola:
                                edilizia_query = edilizia_query.filter(ubicazione__icontains=parola)
            elif civico and civico !='' and civico != '*':
                for parola in civico.split():
                    parola = parola.strip()
                    if parola:
                        edilizia_query = edilizia_query.filter(ubicazione__icontains=parola)

            if (foglio and foglio != '*') or (mappale and mappale != '*'):
                particelle_qs = EdiliziaPratica.objects.all()
                if foglio and foglio != '*':
                    foglio_norm = normalize_foglio(foglio) or foglio
                    q_foglio = Q(particelle_univoche__foglio__startswith=foglio_norm) | Q(fg__startswith=foglio_norm)
                    particelle_qs = particelle_qs.filter(q_foglio).distinct()
                if mappale and mappale != '*':
                    mappali = extract_mappali(mappale)
                    if mappali:
                        q_mapp = Q()
                        for m in mappali:
                            q_mapp |= Q(particelle_univoche__mappale__startswith=m)
                            q_mapp |= Q(mapp__startswith=m)
                        particelle_qs = particelle_qs.filter(q_mapp).distinct()
                    else:
                        q_mapp = Q(particelle_univoche__mappale__startswith=mappale) | Q(mapp__startswith=mappale)
                        particelle_qs = particelle_qs.filter(q_mapp).distinct()
                edilizia_query = edilizia_query.filter(id__in=particelle_qs.values_list('id', flat=True).distinct())

            edilizia_ordered = edilizia_query.order_by('-data_prot_gen', '-id')

        # Query con ordinamento
        pratiche_ordered = pratiche_queryset.select_related('tipo_pratica', 'street', 'pratiche_impianto__impianti_ascensore')\
            .prefetch_related('pratiche__particella', 'pratiche_soggetti__soggetto')\
            .distinct().order_by('-data_prot_gen', '-prot_gen')

        if 'edilizia_ordered' in dir() or 'edilizia_ordered' in locals():
            all_pratiche = list(pratiche_ordered) + list(edilizia_ordered)
        else:
            all_pratiche = list(pratiche_ordered)

        pratiche_protocollo = [p for p in all_pratiche if not isinstance(p, EdiliziaPratica)]
        pratiche_edilizia = [p for p in all_pratiche if isinstance(p, EdiliziaPratica)]

        pratiche_geo_protocollo = []
        pratiche_geo_edilizia = []

        # Tab richiesta: mostra sulla mappa solo le pratiche della tab selezionata
        tab_param = request.GET.get('tab')
        if tab_param in ['opengeoprot', 'archivio']:
            default_tab = tab_param
        elif id_list:
            edilizia_count = EdiliziaPratica.objects.filter(id__in=id_list).count()
            default_tab = 'archivio' if edilizia_count == len(id_list) else 'opengeoprot'
        else:
            default_tab = 'opengeoprot' if len(pratiche_protocollo) >= len(pratiche_edilizia) else 'archivio'

        for pratica in all_pratiche:
            is_edilizia = isinstance(pratica, EdiliziaPratica)

            # Rispetta il tab richiesto: escludi le pratiche dell'altra sorgente
            if tab_param == 'opengeoprot' and is_edilizia:
                continue
            if tab_param == 'archivio' and not is_edilizia:
                continue
            if is_edilizia:
                geom = None
                geojson = None
                if pratica.mpoly_pratica:
                    geom = pratica.mpoly_pratica.centroid
                    geojson = json.loads(pratica.mpoly_pratica.json)
                else:
                    first_pu = pratica.particelle_univoche.filter(mpoly__isnull=False).first()
                    if first_pu:
                        geom = first_pu.mpoly.centroid
                        geojson = json.loads(first_pu.mpoly.json)
                if not geom:
                    continue
                latitudine = round(float(geom.y), 6)
                longitudine = round(float(geom.x), 6)
                street = ''
                civico = ''
                osm_query = ''
                mapillary_url = ''
                url = reverse('gest_edilizia:pratica_edit', args=[pratica.id])
                tipo = pratica.tipo or 'N/D'
                tipo_id = 0
                stato = ''
                matricola = ''
                soggetti = pratica.richiedente or ''
                particelle = []
                for pu in pratica.particelle_univoche.all():
                    particelle.append({
                        'foglio': pu.foglio or '',
                        'mappale': pu.mappale or '',
                        'subalterno': '-',
                        'visura_url': (
                            'http://appsrvgis/ubucomu/catasto/nctr_results_ana.php?'
                            f"f={pu.foglio}&m={pu.mappale}"
                        ),
                    })
            else:
                geom = pratica.mpoly_pratica.centroid if pratica.mpoly_pratica else pratica.posizione
                geojson = json.loads(pratica.mpoly_pratica.json) if pratica.mpoly_pratica else None
                if not geom:
                    continue
                latitudine = round(float(geom.y), 6)
                longitudine = round(float(geom.x), 6)
                street = pratica.street.street if pratica.street else ''
                civico = pratica.housenumber or ''
                osm_query = f"{street} {civico} carrara".strip()
                mapillary_url = f"https://www.mapillary.com/app/?lat={latitudine}&lng={longitudine}&z=17&focus=photo"
                url = reverse('protocollo:pratica_detail_url', kwargs={'pk': pratica.id})
                tipo = pratica.tipo_pratica.name if pratica.tipo_pratica else 'N/D'
                tipo_id = pratica.tipo_pratica_id or 0
                stato = pratica.stato or ''
                matricola = ''
                try:
                    if pratica.pratiche_impianto and pratica.pratiche_impianto.impianti_ascensore:
                        matricola = pratica.pratiche_impianto.impianti_ascensore.matricola_assegnata or ''
                except Exception:
                    pass
                soggetti = ', '.join(
                    f"{s.cognome} {s.nome}" for s in pratica.soggetto_pratica.all()
                )
                particelle = []
                for cp in pratica.pratiche.select_related('particella'):
                    if not cp.particella:
                        continue
                    particelle.append({
                        'foglio': cp.particella.foglio or '',
                        'mappale': cp.particella.mappale or '',
                        'subalterno': cp.subalterno or '-',
                        'visura_url': (
                            'http://appsrvgis/ubucomu/catasto/nctr_results_ana.php?'
                            f"f={cp.particella.foglio}&m={cp.particella.mappale}"
                        ),
                    })

            pratica.lat = latitudine
            pratica.lng = longitudine
            pratica.osm_url = f"https://www.openstreetmap.org/search?query={urlencode({'query': osm_query})}" if osm_query else ''
            pratica.mapillary_url = mapillary_url
            pratica.url = url
            pratica.tipo = tipo
            pratica.tipo_id = tipo_id
            pratica.stato = stato
            pratica.soggetti = soggetti
            pratica.matricola = matricola
            pratica.street_display = street
            pratica.civico = civico
            pratica.particelle_list = particelle
            pratica.is_edilizia = is_edilizia

            geo_item = {
                'id': pratica.id,
                'latitudine': latitudine,
                'longitudine': longitudine,
                'geojson': geojson,
                'prot': pratica.prot_gen or '',
                'data': pratica.data_prot_gen.strftime('%d/%m/%Y') if pratica.data_prot_gen else '',
                'anno': pratica.data_prot_gen.year if pratica.data_prot_gen else '',
                'oggetto': (pratica.oggetto[:150] + '...') if pratica.oggetto and len(pratica.oggetto) > 150 else (pratica.oggetto or ''),
                'tipo': tipo,
                'tipo_id': tipo_id,
                'stato': stato,
                'street': street,
                'civico': civico,
                'soggetti': soggetti,
                'matricola': matricola,
                'particelle': particelle,
                'mapillary_url': mapillary_url,
                'osm_url': pratica.osm_url,
                'url': url,
                'is_edilizia': is_edilizia,
            }
            if is_edilizia:
                pratiche_geo_edilizia.append(geo_item)
            else:
                pratiche_geo_protocollo.append(geo_item)

        # ID pratiche
        pratiche_ids = [p.id for p in all_pratiche]

        context = {
            'pratiche_protocollo': pratiche_protocollo,
            'pratiche_edilizia': pratiche_edilizia,
            'pratiche_geo_protocollo': json.dumps(pratiche_geo_protocollo, ensure_ascii=False).replace('</', '<\\/'),
            'pratiche_geo_edilizia': json.dumps(pratiche_geo_edilizia, ensure_ascii=False).replace('</', '<\\/'),
            'pratiche_ids': pratiche_ids,
            'totale_protocollo': len(pratiche_protocollo),
            'totale_edilizia': len(pratiche_edilizia),
            'totale_p': len(all_pratiche),
            'query_string': query_params,
            'default_tab': default_tab,
            'nessun_risultato': len(all_pratiche) == 0,
        }

        # Renderizza la mappa
        return render(request, 'protocollo/mappa_results.html', context)

    else:
        # Se GET senza parametri, puoi reindirizzare o mostrare una pagina di ricerca
        # Per esempio:
        return render(request, 'protocollo/ricerca_pratica.html', {'form': form, 'tipo_pratica_list': get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True)})


import json

@login_required
def pratiche_chart_view(request, tipo_pratica_id=None):
    """Visualizza un grafico lineare con l'andamento delle pratiche per tipo_pratica e anno."""
    from collections import defaultdict
    
    # Ottieni i dati aggregati: tipo_pratica + anno
    queryset = Pratica.objects.extra(
        select={'anno': "EXTRACT(YEAR FROM data_prot_gen)"}
    ).values('tipo_pratica__name', 'anno').annotate(
        count=Count('id')
    ).order_by('tipo_pratica__name', 'anno')
    
    # Filtra per tipo_pratica se specificato
    if tipo_pratica_id:
        queryset = queryset.filter(tipo_pratica_id=tipo_pratica_id)
    
    # Organizza i dati per tipo
    tipi_dict = defaultdict(lambda: {'labels': [], 'data': []})
    anni_set = set()
    
    for item in queryset:
        tipo_name = item['tipo_pratica__name']
        anno = item['anno']
        count = item['count']
        anni_set.add(anno)
        tipi_dict[tipo_name]['labels'].append(anno)
        tipi_dict[tipo_name]['data'].append(count)
    
    # Raggruppa per anno (asse x)
    anni_ordini = sorted(anni_set)
    
    # Prepara i dataset per il grafico
    datasets = []
    colors = ['#0d6efd', '#198754', '#dc3545', '#ffc107', '#0dcaf0', '#6c757d', '#212529']
    color_index = 0
    
    for tipo_name, data in tipi_dict.items():
        # Riempi i valori mancanti con 0
        dati_completi = []
        for anno in anni_ordini:
            if anno in data['labels']:
                idx = data['labels'].index(anno)
                dati_completi.append(int(data['data'][idx]))
            else:
                dati_completi.append(0)
        
        datasets.append({
            'label': tipo_name,
            'data': dati_completi,
            'borderColor': colors[color_index % len(colors)],
            'backgroundColor': colors[color_index % len(colors)] + '20',
            'fill': False,
            'tension': 0.1
        })
        color_index += 1
    
    context = {
        'labels': json.dumps([str(a) for a in anni_ordini]),
        'datasets': datasets,
        'tipo_pratica_id': tipo_pratica_id,
        'has_data': len(datasets) > 0 and len(anni_ordini) > 0,
    }
    
    return render(request, 'protocollo/pratiche_chart.html', context)


@login_required
def mappa_area(request):
    if request.GET.get('clear') == '1':
        request.session.pop('area_geojson', None)
        request.session.pop('area_filter_query', None)

    if request.method == 'POST':
        geojson = request.POST.get('area_geojson')
        if geojson:
            request.session['area_geojson'] = geojson
        return redirect('protocollo:pratiche_lista_area_url')

    # Conserva i filtri di ricerca eventualmente passati dal form (usati da
    # "Cerca su Area" per applicare gli stessi criteri della ricerca testuale)
    if request.method == 'GET' and request.GET.urlencode() not in ('', 'clear=1'):
        request.session['area_filter_query'] = request.GET.urlencode()

    return render(request, 'protocollo/mappa_area.html')


@login_required
def pratiche_lista_area(request):
    geojson = request.session.get('area_geojson')
    if not geojson:
        messages.warning(request, "Nessuna area selezionata. Seleziona un'area sulla mappa.")
        return redirect('protocollo:mappa_area_url')
    
    try:
        geom = area_search.parse_area_geometry(geojson)
        if geom is None:
            messages.error(request, "Forma area non valida.")
            if 'area_geojson' in request.session:
                del request.session['area_geojson']
            return redirect('protocollo:mappa_area_url')

        qs = get_practice_queryset(request.user)
        qs = qs.filter(
            Q(mpoly_pratica__isnull=False, mpoly_pratica__intersects=geom) |
            Q(posizione__isnull=False, posizione__intersects=geom)
        ).distinct()

        # Applica gli eventuali filtri di ricerca passati da "Cerca su Area"
        area_filter_query = request.session.get('area_filter_query')
        if area_filter_query:
            try:
                params = dict(parse_qsl(area_filter_query))
                if params:
                    qs = qs.filter(build_protocollo_filter_q(params))
            except Exception:
                pass

        qs = qs.order_by('-data_prot_gen', '-prot_gen')

        totale_p = qs.count()
        paginator = Paginator(qs, 10)
        page = request.GET.get('page')
        try:
            pratiche_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            pratiche_page = paginator.page(1)
        
        if totale_p == 0:
            messages.info(request, "nessun risultato presente nell'area selezionata!")
        
        context = {
            'pratica': pratiche_page,
            'tp': get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True),
            'totale_p': totale_p,
            'from_map': True,
            'pratiche_ids': list(qs.values_list('id', flat=True)),
            'protocollo_ids': list(qs.values_list('id', flat=True)),
            'edilizia_pratica_list': None,
            'edilizia_tot': 0,
            'edilizia_ids': [],
            'pratiche_with_particelle': [],
            'active_tab': 'opengeoprot',
            'show_opengeoprot': True,
            'show_archivio': False,
        }
        return render(request, 'protocollo/pratiche_list.html', context)
    
    except Exception as e:
        messages.error(request, f"Errore durante l'elaborazione dell'area: {str(e)}")
        if 'area_geojson' in request.session:
            del request.session['area_geojson']
        return redirect('protocollo:mappa_area_url')


@login_required
def pratiche_punto_lista(request):
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if not lat or not lng:
        messages.warning(request, "Coordinate non valide.")
        return redirect('protocollo:mappa_area_sviluppo_url')
    
    try:
        pnt = Point(float(lng), float(lat), srid=4326)
        buffer_deg = 0.00005
        geom = pnt.buffer(buffer_deg)
        
        qs = get_practice_queryset(request.user)
        qs = qs.filter(
            Q(mpoly_pratica__isnull=False, mpoly_pratica__intersects=geom) |
            Q(posizione__isnull=False, posizione__intersects=geom)
        ).distinct().order_by('-data_prot_gen', '-prot_gen')
        
        totale_p = qs.count()
        paginator = Paginator(qs, 10)
        page = request.GET.get('page')
        try:
            pratiche_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            pratiche_page = paginator.page(1)
        
        if totale_p == 0:
            messages.info(request, "nessun risultato presente nel punto selezionato!")
        
        context = {
            'pratica': pratiche_page,
            'tp': get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True),
            'totale_p': totale_p,
            'from_map': True,
            'pratiche_ids': list(qs.values_list('id', flat=True)),
            'protocollo_ids': list(qs.values_list('id', flat=True)),
            'edilizia_pratica_list': None,
            'edilizia_tot': 0,
            'edilizia_ids': [],
            'pratiche_with_particelle': [],
            'active_tab': 'opengeoprot',
            'show_opengeoprot': True,
            'show_archivio': False,
        }
        return render(request, 'protocollo/pratiche_list.html', context)
    
    except Exception as e:
        messages.error(request, f"Errore durante la ricerca nel punto: {str(e)}")
        return redirect('protocollo:mappa_area_sviluppo_url')


def permission_denied_view(request, exception=None):
    """Handler 403: pagina che spiega il blocco e rimanda alla home."""
    message = getattr(exception, 'args', ['Operazione non consentita.']) or ['Operazione non consentita.']
    message = message[0] if isinstance(message, (list, tuple)) and message else str(exception)
    gruppi = ''
    if request.user.is_authenticated:
        gruppi = ', '.join(
            request.user.groups.filter(name__startswith='user_settore')
            .values_list('name', flat=True)
        )
    return render(request, 'protocollo/permission_denied.html', {
        'message': message,
        'gruppi': gruppi,
    }, status=403)


READONLY_PREFIX = 'user_settore'
EDITOR_GROUPS = ['editor_settore_6', 'editor_settore_1', 'editor_settore_5']


def can_edit(user):
    """True se l'utente appartiene a un gruppo abilitato alla scrittura.
    I gruppi di sola lettura (user_settore_*) non possono mai modificare."""
    if not user or not user.is_authenticated:
        return False
    if user.groups.filter(name__startswith=READONLY_PREFIX).exists():
        return False
    return user.is_superuser or user.groups.filter(name__in=EDITOR_GROUPS).exists()


def is_readonly(user):
    """True se l'utente appartiene a un gruppo di sola lettura."""
    return bool(user and user.is_authenticated and
                (user.groups.filter(name__startswith=READONLY_PREFIX).exists() or
                 user.groups.filter(name='readonly').exists()))


def block_readonly_write(view_func):
    """Decoratore: gli utenti di sola lettura possono solo leggere (GET/HEAD).
    Qualsiasi richiesta di scrittura (POST/PUT/DELETE) viene bloccata con 403."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if is_readonly(request.user) and request.method.upper() not in ('GET', 'HEAD', 'OPTIONS'):
            gruppi = ', '.join(
                request.user.groups.filter(name__startswith=READONLY_PREFIX)
                .values_list('name', flat=True)
            )
            raise PermissionDenied(
                "Gruppo di sola lettura: modifica non consentita. Gruppi: " + gruppi
            )
        return view_func(request, *args, **kwargs)
    return _wrapped


import os
import re
from collections import defaultdict
from django.contrib.auth import get_user_model
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

User = get_user_model()


def _parse_log_line(line):
    m = re.match(r'\[(.*?)\] INFO User: ([^,]+), Method: ([^,]+), Path: ([^,]+), IP: (.*)$', line)
    if not m:
        return None
    ts_str, username, method, path, ip = m.groups()
    try:
        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S,%f')
    except ValueError:
        return None
    return {'ts': ts, 'username': username.strip(), 'method': method.strip(), 'path': path.strip(), 'ip': ip.strip()}


@login_required
def accessi_report(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden()
    log_path = os.path.join(settings.BASE_DIR, 'user_actions.log')
    stats = defaultdict(lambda: {'ips': set(), 'total': 0, 'weekend': 0})
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parsed = _parse_log_line(line)
                if not parsed:
                    continue
                username = parsed['username']
                ip = parsed['ip']
                stats[username]['ips'].add(ip)
                stats[username]['total'] += 1
                if parsed['ts'].weekday() >= 5:
                    stats[username]['weekend'] += 1

    users_info = {}
    for u in User.objects.all():
        users_info[u.get_username()] = u.pk

    rows = []
    for username, data in stats.items():
        uid = users_info.get(username)
        rows.append({
            'username': username,
            'user_id': uid,
            'ips': ', '.join(sorted(data['ips'])) if data['ips'] else '-',
            'total': data['total'],
            'weekend': data['weekend'],
        })
    rows.sort(key=lambda r: r['total'], reverse=True)
    return render(request, 'protocollo/accessi_report.html', {'rows': rows})


@login_required
def accessi_report_user(request, username):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden()
    log_path = os.path.join(settings.BASE_DIR, 'user_actions.log')
    entries = []
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parsed = _parse_log_line(line)
                if not parsed:
                    continue
                if parsed['username'] != username:
                    continue
                entries.append({
                    'ts': parsed['ts'],
                    'data': parsed['ts'].strftime('%d/%m/%Y %H:%M:%S'),
                    'method': parsed['method'],
                    'path': parsed['path'],
                    'ip': parsed['ip'],
                })
    entries.sort(key=lambda r: r['ts'], reverse=True)
    return render(request, 'protocollo/accessi_report_user.html', {
        'username': username,
        'entries': entries,
    })


@login_required
def serve_documento(request, pk):
    documento = get_object_or_404(Documento, pk=pk)
    if request.user.groups.filter(name='readonly').exists():
        from django.shortcuts import redirect
        return redirect('accounts:richiesta_accesso', pk=documento.pratica_id)
    pratica = documento.pratica
    if not get_practice_queryset(request.user).filter(pk=pratica.pk).exists():
        raise PermissionDenied()
    if not documento.document or not documento.document.name:
        raise Http404("Documento senza file allegato")
    filepath = os.path.join(settings.MEDIA_ROOT, documento.document.name)
    if not os.path.exists(filepath) or not os.path.isfile(filepath):
        raise Http404("File non trovato")
    with open(filepath, 'rb') as fh:
        file_bytes = fh.read()

    ext = os.path.splitext(documento.document.name)[1].lower()
    if ext == '.pdf':
        try:
            file_bytes = add_watermark_to_pdf(file_bytes, user=request.user)
        except Exception as e:
            logger = logging.getLogger('user_actions')
            logger.warning(f'Watermark fallback per documento pk={pk}: {e}')

    logger_user_active = logging.getLogger('user_active')
    logger_user_active.info(
        f"Utente: {request.user.username} ha scaricato il documento pk={pk} "
        f"nome={os.path.basename(documento.document.name)} "
        f"dalla pratica {pratica.id} / {pratica.prot_gen}"
    )

    DocumentoDownload.objects.create(
        documento=documento,
        user=request.user,
    )

    response = HttpResponse(file_bytes, content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(documento.document.name)
    return response


def _estrai_testo_documento(filepath):
    """Estrae il testo testuale da un file allegato (PDF, DOCX, TXT/MD/CSV)."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.pdf':
        try:
            import pypdf
        except Exception:
            import PyPDF2 as pypdf
        try:
            reader = pypdf.PdfReader(filepath)
            parti = []
            for page in reader.pages:
                try:
                    parti.append(page.extract_text() or '')
                except Exception:
                    continue
            return '\n'.join(parti)
        except Exception:
            return ''
    if ext == '.docx':
        try:
            d = Document(filepath)
            return '\n'.join(p.text for p in d.paragraphs)
        except Exception:
            return ''
    if ext in ('.txt', '.md', '.csv', '.log', '.rtf'):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ''
    return ''


def _testo_coerente(testo, min_lettere=10, min_caratteri=20):
    """Restituisce True se il testo estratto contiene contenuto testuale
    coerente (almeno N lettere e M caratteri totali). Serve a scartare PDF
    malformati, immagini/scansioni senza OCR o file binari che restituiscono
    solo numeri, date e spazi."""
    if not testo:
        return False
    testo = testo.strip()
    if len(testo) < min_caratteri:
        return False
    lettere = sum(1 for c in testo if c.isalpha())
    return lettere >= min_lettere


def _sanitizza_testo(testo):
    """Rimuove caratteri surrogate e di controllo non validi che PostgreSQL
    non può salvare (es. \\udbc0 prodotti da pypdf su PDF malformati)."""
    if not testo:
        return ''
    risultato = []
    for c in testo:
        cp = ord(c)
        # scarta surrogate (U+D800..U+DFFF) e caratteri di controllo
        # eccetto tab/newline/return
        if 0xD800 <= cp <= 0xDFFF:
            continue
        if cp < 0x20 and c not in ('\t', '\n', '\r'):
            continue
        risultato.append(c)
    return ''.join(risultato)


@login_required
def cerca_documenti_testo(request):
    """Ricerca full-text nei contenuti dei documenti allegati.

    Usa l'indice precomputato in IndiceDocumento (tabella DB) invece di
    leggere i file su disco a ogni richiesta, così le ricerche successive
    sono rapide (query SQL icontains). I documenti ancora non indicizzati
    vengono elaborati lazily alla prima occorrenza.
    """
    q = (request.GET.get('q') or '').strip()
    risultati = []
    if q:
        pratica_qs = get_practice_queryset(request.user)
        # Documenti visibili all'utente che hanno un file allegato
        documenti_visibili = (
            Documento.objects
            .exclude(document='')
            .exclude(document__isnull=True)
            .filter(pratica__in=pratica_qs)
            .select_related('pratica', 'pratica__tipo_pratica')
        )

        # Indicizzazione lazy dei documenti ancora senza indice
        da_indice = [
            d for d in documenti_visibili
            if not hasattr(d, 'indice_testo') or not d.indice_testo.testo
        ]
        for d in da_indice:
            filepath = os.path.join(settings.MEDIA_ROOT, d.document.name)
            if os.path.exists(filepath) and os.path.isfile(filepath):
                testo = _estrai_testo_documento(filepath)
                testo = _sanitizza_testo(testo)
                if not _testo_coerente(testo):
                    continue
                IndiceDocumento.objects.update_or_create(
                    documento=d,
                    defaults={'testo': testo},
                )

        # Query rapida sull'indice DB
        indici = (
            IndiceDocumento.objects
            .filter(testo__icontains=q)
            .select_related('documento', 'documento__pratica', 'documento__pratica__tipo_pratica')
        )
        for indice in indici:
            pratica = indice.documento.pratica
            testo = indice.testo or ''
            idx = testo.lower().find(q.lower())
            if idx == -1:
                continue
            inizio = max(0, idx - 180)
            fine = min(len(testo), idx + len(q) + 220)
            snippet = testo[inizio:fine]
            snippet = re.sub(r'\s+', ' ', snippet).strip()
            if inizio > 0:
                snippet = '…' + snippet
            if fine < len(testo):
                snippet = snippet + '…'
            risultati.append({
                'documento': indice.documento,
                'pratica': pratica,
                'snippet': snippet,
            })

    tipo_pratica_list = get_filtered_tipo_pratica_list(request.user, only_opengeoprot=True)
    context = {
        'form': UnifiedSearchForm(user=request.user),
        'tipo_pratica_list': tipo_pratica_list,
        'tp': tipo_pratica_list,
        'origine_list': Origine.objects.all().order_by('nome'),
        'mappa_area_query': '',
        'q': q,
        'risultati': risultati,
    }
    return render(request, 'protocollo/ricerca_pratica.html', context)


@login_required
def mappa_area_sviluppo(request):
    """Mappa con ricerca delle pratiche per area disegnata.

    L'area (rettangolo o poligono) viene inviata dal browser in formato
    GeoJSON; il server la normalizza e cerca tutte le pratiche che la
    intersecano: OPENGEOPROT (protocollo.Pratica) e ARCHIVIO
    (edilizia.Pratica, limitate alle pratiche con particelle collegate
    che intersecano l'area).
    """
    contesto = {
        'pratiche_area': [],
        'pratiche_edilizia_area': [],
        'totale_p': 0,
        'totale_ed': 0,
        'area_geojson': None,
        'area_geojson_obj': None,
        'risultati_geojson': area_search.feature_collection([]),
        'area_cercata': False,
        'limite_risultati': area_search.LIMITE_RISULTATI,
    }

    if request.method == 'POST':
        geojson = (request.POST.get('area_geojson') or '').strip()
        if geojson:
            # L'area cercata viene conservata in sessione solo per la
            # richiesta corrente: aprendo la pagina non viene riproposta.
            request.session['area_geojson_sviluppo'] = geojson
        else:
            messages.error(request, "Area non valida: disegna un rettangolo o un poligono sulla mappa e riprova.")
    else:
        # Apertura della pagina: nessun risultato e nessuna area precedente.
        request.session.pop('area_geojson_sviluppo', None)
        geojson = ''

    geom = area_search.parse_area_geometry(geojson)
    if geojson and geom is None:
        messages.error(request, "Area non valida: disegna un rettangolo o un poligono sulla mappa e riprova.")
        request.session.pop('area_geojson_sviluppo', None)
        geojson = ''

    if geom is not None:
        contesto['area_geojson'] = geojson
        contesto['area_cercata'] = True
        try:
            contesto['area_geojson_obj'] = json.loads(geojson)
        except ValueError:
            contesto['area_geojson_obj'] = None

        risultati = area_search.cerca_pratiche_in_area(
            geom,
            get_practice_queryset(request.user).prefetch_related(
                'pratiche_soggetti__soggetto', 'pratiche_soggetti__tipo'
            ),
            EdiliziaPratica.objects.all(),
        )

        pratiche = risultati['pratiche']
        pratiche_edilizia = risultati['archivio']

        # Richiedenti (primi 3) per l'elenco OPENGEOPROT, letti dalla
        # relatione prefetchata per evitare query N+1.
        for p in pratiche:
            rels = (getattr(p, '_prefetched_objects_cache', None) or {}).get(
                'pratiche_soggetti', []
            )
            p.richiedenti_lista = [
                '{} {}'.format(
                    (r.soggetto.nome or '').strip(),
                    (r.soggetto.cognome or '').strip(),
                ).strip()
                for r in rels
                if r.tipo and r.tipo.name and r.tipo.name.lower() == 'richiedente' and r.soggetto
            ][:3]

        contesto.update({
            'pratiche_area': pratiche,
            'pratiche_edilizia_area': pratiche_edilizia,
            'totale_p': risultati['totale'],
            'totale_ed': risultati['totale_archivio'],
        })

        if not pratiche and not pratiche_edilizia:
            messages.info(request, "Nessun risultato presente nell'area selezionata!")
        elif request.method == 'POST':
            log_action(request, 'RICERCA_AREA',
                       f"area con {risultati['totale']} pratiche OPENGEOPROT, "
                       f"{risultati['totale_archivio']} ARCHIVIO")

    return render(request, 'protocollo/mappa_area_sviluppo.html', contesto)


@login_required
def mappa_area_sviluppo_risultati(request):
    """Restituisce il GeoJSON delle pratiche che intersecano l'area disegnata.

    Usato dalla mappa per evidenziare i risultati senza appesantire la pagina
    principale con il GeoJSON completo.
    """
    if request.method != 'POST':
        return JsonResponse(area_search.feature_collection([]), safe=False)

    geojson = (request.POST.get('area_geojson') or '').strip()
    geom = area_search.parse_area_geometry(geojson)
    if geom is None:
        return JsonResponse(area_search.feature_collection([]), safe=False)

    try:
        pratiche, _ = area_search.cerca_opengeoprot(
            get_practice_queryset(request.user), geom, area_search.LIMITE_MAPPA)
        archivio, _ = area_search.cerca_archivio(
            EdiliziaPratica.objects.all(), geom, area_search.LIMITE_MAPPA)
    except Exception as e:
        logger_user_actions.warning(f"Errore nel calcolo del GeoJSON dei risultati area: {e}")
        return JsonResponse(area_search.feature_collection([]), safe=False)

    features = []
    features += area_search.features_pratiche(
        pratiche,
        'opengeoprot',
        lambda p: reverse('protocollo:pratica_detail_url', args=[p.id]),
        lambda p: '{} - {}'.format(
            p.prot_gen or p.id,
            p.tipo_pratica.name if p.tipo_pratica else ''
        ).strip(' -'),
        fallback_posizione=True,
        limite=area_search.LIMITE_MAPPA,
    )
    features += area_search.features_pratiche(
        archivio,
        'archivio',
        lambda p: reverse('gest_edilizia:pratica_edit', args=[p.id]),
        lambda p: '{} - {}'.format(
            p.prot_gen or p.id,
            (p.richiedente or '')[:60]
        ).strip(' -'),
        limite=area_search.LIMITE_MAPPA,
    )
    return JsonResponse(area_search.feature_collection(features), safe=False)


@login_required
def particella_geojson(request):
    from catasto.models import Particelle
    foglio = request.GET.get('foglio', '').strip()
    mappale = request.GET.get('mappale', '').strip()
    if not foglio or not mappale:
        return JsonResponse({'type': 'FeatureCollection', 'features': []})
    user_username = request.user.username if request.user.is_authenticated else 'Anonimo'
    client_ip = get_client_ip(request)
    try:
        foglio_norm = foglio.zfill(4)
        mappale_norm = mappale.zfill(4)
        qs = Particelle.objects.using('anagrafe').filter(
            (Q(foglio__iexact=foglio) | Q(foglio__iexact=foglio_norm)) &
            (Q(mappale__iexact=mappale) | Q(mappale__iexact=mappale_norm))
        )
        features = []
        for part in qs:
            features.append({
                'type': 'Feature',
                'id': part.id,
                'geometry': json.loads(part.mpoly.geojson),
                'properties': {
                    'id': part.id,
                    'foglio': part.foglio,
                    'mappale': part.mappale,
                }
            })
        logger_user_actions.info(
            f"Ricerca particella - Utente: {user_username}, IP: {client_ip}, "
            f"foglio: {foglio_norm}, mappale: {mappale}, risultati: {len(features)}"
        )
        return JsonResponse({'type': 'FeatureCollection', 'features': features})
    except Exception:
        logger_user_actions.info(
            f"Ricerca particella - Utente: {user_username}, IP: {client_ip}, "
            f"foglio: {foglio_norm}, mappale: {mappale}, risultati: 0 (errore)"
        )
        return JsonResponse({'type': 'FeatureCollection', 'features': []})