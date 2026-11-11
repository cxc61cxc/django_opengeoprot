# accounts/views.py
import re
from django.contrib.auth import login, update_session_auth_hash, logout
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import render, redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView
from django.http import Http404, JsonResponse
from django.db.models import Q
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


from .forms import SignUpForm, ProfileEditForm, PasswordChangeCustomForm, RichiestaAccessoForm
from .models import Profile
from .permissions import is_consigliere
from protocollo.utils import log_action


def _staff_or_superuser(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


from protocollo.views import _apply_pratica_permissions
from mailer.utils import send_notification_email


@login_required
def struttura_choices_api(request):
    """Endpoint AJAX: restituisce Servizi/UO filtrati per Settore (e Servizio)."""
    from struttura_ente.models import StoricoServizio, StoricoAttivitaUO
    settore = request.GET.get('settore', '')
    servizio_id = request.GET.get('servizio', '')

    servizi_qs = StoricoServizio.objects.filter(data_fine__isnull=True).select_related('settore_storico')
    if settore:
        servizi_qs = servizi_qs.filter(settore_storico__codice=settore)
    servizi = [
        {'id': s.id, 'label': f'{s.settore_storico.codice} / {s.codice} - {s.nome}'}
        for s in servizi_qs.order_by('settore_storico__codice', 'codice')
    ]

    uo_qs = StoricoAttivitaUO.objects.filter(data_fine__isnull=True).select_related(
        'servizio_storico__settore_storico'
    )
    if servizio_id:
        uo_qs = uo_qs.filter(servizio_storico_id=servizio_id)
    elif settore:
        uo_qs = uo_qs.filter(servizio_storico__settore_storico__codice=settore)
    uo = [
        {
            'id': u.id,
            'label': f"{u.servizio_storico.settore_storico.codice} / {u.servizio_storico.codice} / {u.nome}",
        }
        for u in uo_qs.order_by('servizio_storico__settore_storico__codice', 'servizio_storico__codice', 'nome')
    ]

    return JsonResponse({'servizi': servizi, 'uo': uo})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            return redirect('protocollo:search_protocollo_url')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileEditForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('home:index') # Reindirizza alla home dopo il salvataggio

    def dispatch(self, request, *args, **kwargs):
        # I consiglieri NON possono modificare il profilo: solo visualizzazione
        if request.user.groups.filter(name='consiglieri').exists():
            return redirect('accounts:profile_view_url')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Profile.objects.get_or_create(user=self.request.user) # Assicurasi che il profilo esista
        context['profile'] = self.request.user.profile
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        log_action(self.request, 'MODIFICATO', 'Profilo utente')
        user = self.request.user
        if not (user.is_staff or user.is_superuser):
            self._notify_staff_profile_modifica(user, form)
        return response

    def _notify_staff_profile_modifica(self, user, form):
        """Invia una email di avviso quando un utente non staff modifica il profilo.
        Destinatari: t4950c@gmail.com fisso + tutti gli staff/superuser attivi con email.
        """
        profile, _ = Profile.objects.get_or_create(user=user)
        settore = profile.settore
        u_o = profile.u_o
        servizio = u_o.servizio_storico if u_o else None

        changed = list(form.changed_data) if form.changed_data else []

        staff_emails = list(
            User.objects.filter(is_staff=True, is_active=True)
            .exclude(email='')
            .values_list('email', flat=True)
        )
        recipient = ['t4950c@gmail.com'] + [e for e in staff_emails if e != 't4950c@gmail.com']

        subject = f'Modifica profilo utente: {user.username}'
        message = (
            f"L'utente {user.get_full_name()} ({user.username}) ha modificato il proprio profilo.\n\n"
            f"  Username: {user.username}\n"
            f"  Nome: {user.first_name}\n"
            f"  Cognome: {user.last_name}\n"
            f"  Email: {user.email}\n"
            f"  Settore: {settore.codice if settore else 'N/D'}\n"
            f"  Servizio: {servizio.codice if servizio else 'N/D'}\n"
            f"  U.O.: {u_o.nome if u_o else 'N/D'}\n"
            f"  Campi modificati: {', '.join(changed) if changed else '(nessuno)'}\n\n"
            f"  IP: {self.request.META.get('REMOTE_ADDR', 'N/D')}\n"
            f"  User-Agent: {self.request.META.get('HTTP_USER_AGENT', 'N/D')}\n"
        )
        try:
            send_notification_email(subject, message, recipient=recipient)
            logger.info("Notifica email modifica profilo inviata a %s per %s", recipient, user.username)
            messages.success(self.request, 'Notifica di modifica profilo inviata allo staff.')
        except Exception as exc:
            logger.exception("Notifica email modifica profilo fallita per %s: %s", user.username, exc)


@login_required
def profile_view(request):
    """Visualizzazione del profilo in sola lettura (per consiglieri e per tutti
    gli utenti che vogliono solo consultare i propri dati)."""
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    commissioni = (
        user.commissioni
        .filter(tipo_commissione__attivo=True)
        .select_related('tipo_commissione')
        .prefetch_related('tipo_commissione__settori')
        .order_by('tipo_commissione__ordine', 'tipo_commissione__nome')
    )
    log_action(request, 'VISUALIZZATO', f'Profilo (read-only)')
    return render(request, 'accounts/profile_view.html', {
        'profile_user': user,
        'profile': profile,
        'commissioni': commissioni,
        'is_consigliere': user.groups.filter(name='consiglieri').exists(),
    })


def _profile_completo(user):
    """Restituisce True se il profilo dell'utente ha settore, servizio e u_o
    tutti impostati. I consiglieri non hanno settore/u_o e vengono considerati
    completi (hanno accesso solo in lettura).
    """
    if is_consigliere(user):
        return True
    profile = getattr(user, 'profile', None)
    if profile is None:
        return False
    if user.is_staff or user.is_superuser:
        # Per gli user staff basta che il settore sia impostato sul profilo
        # o che lo settore sia determinato dal gruppo user_staff_*
        if profile.settore is not None:
            return True
        return user.groups.filter(name__startswith='user_staff_').exists()
    if profile.settore is None:
        return False
    if profile.u_o is None:
        return False
    if profile.u_o.servizio_storico is None:
        return False
    return True


@login_required
def profile_settore_check(request):
    """Verifica le impostazioni profilo settore/servizio/uo.

    Se il profilo ha settore, servizio (via u_o) e u_o tutti impostati,
    reindirizza alla visualizzazione profilo. In caso contrario mostra un
    template con la lista dei settori/servizi/uo disponibili per l'utente
    (filtrati in base al gruppo di appartenenza), affinche' l'utente possa
    individuare e selezionare le proprie assegnazioni tramite la pagina di
    modifica profilo.

    I consiglieri (che non hanno settore/u_o) vengono reindirizzati direttamente
    al profilo in sola lettura.
    """
    user = request.user

    # I consiglieri non hanno settore/u_o: reindirizza al profilo
    if is_consigliere(user):
        return redirect('accounts:profile_view_url')

    from struttura_ente.models import Settore, StoricoSettore, StoricoServizio, StoricoAttivitaUO

    profile, _ = Profile.objects.get_or_create(user=user)

    settore_ok = profile.settore is not None
    uo_ok = profile.u_o is not None
    servizio_ok = uo_ok and profile.u_o.servizio_storico is not None
    # Per gli user staff basta che il settore sia impostato
    if user.is_staff or user.is_superuser:
        uo_ok = settore_ok
        servizio_ok = settore_ok
    if _profile_completo(user):
        return redirect('accounts:profile_view_url')

    # --- Determina i settori disponibili per l'utente in base al gruppo ---
    user_group = user.groups.filter(name__startswith='user_settore_').first()
    if user_group:
        settore_codice = user_group.name.replace('user_settore_', 'settore ')
    else:
        staff_group = user.groups.filter(name__startswith='user_staff_').first()
        if staff_group:
            settore_codice = staff_group.name.replace('user_staff_', 'staff ')
        else:
            settore_codice = None

    settori_qs = StoricoSettore.objects.filter(data_fine__isnull=True).order_by(
        'settore__ordine', 'codice'
    )
    if settore_codice:
        settori_qs = settori_qs.filter(codice__iexact=settore_codice)

    # Costruisce una lista di settori con servizi pre-filtrati (i template di
    # Django non supportano .filter() o .count con kwargs in {% for %}).
    settori_list = []
    for s in settori_qs:
        servizi = list(
            s.settore.servizi.filter(attivo=True).order_by('ordine', 'nome')
        )
        # Annota il conteggio U.O. attive per ciascun servizio
        servizi_con_uo = []
        for srv in servizi:
            uo_count = srv.attivita.filter(attivo=True).count()
            servizi_con_uo.append({
                'id': srv.id,
                'pk': srv.pk,
                'codice': srv.codice,
                'nome': srv.nome,
                'descrizione': srv.descrizione,
                'uo_count': uo_count,
            })
        settori_list.append({
            'storico': s,
            'codice': s.codice,
            'nome': s.nome,
            'servizi': servizi_con_uo,
        })

    # Nodo settore: se il settore esiste gia' nel profilo ma e' diverso,
    # considera comunque il settore del profilo per i servizi/uo.
    settore_attivo = profile.settore

    servizi = None
    uo_list = None
    if settore_attivo:
        servizi = StoricoServizio.objects.filter(
            data_fine__isnull=True,
            settore_storico=settore_attivo,
        ).order_by('settore_storico__codice', 'codice')
        if uo_ok and profile.u_o and profile.u_o.servizio_storico_id:
            uo_list = StoricoAttivitaUO.objects.filter(
                data_fine__isnull=True,
                servizio_storico_id=profile.u_o.servizio_storico_id,
            ).order_by('servizio_storico__codice', 'nome')

    log_action(request, 'VISUALIZZATO', f'Lista settore/servizio/uo (profilo incompleto)')

    return render(request, 'accounts/profile_settore_list.html', {
        'profile': profile,
        'settore_ok': settore_ok,
        'servizio_ok': servizio_ok,
        'uo_ok': uo_ok,
        'settori': settori_list,
    })


@login_required
@user_passes_test(_staff_or_superuser)
def profile_incomplete_users(request):
    """Vista admin: elenca tutti gli utenti (esclusi i consiglieri) il cui
    profilo ha settore, servizio o u_o non impostati.
    """
    from django.contrib.auth.models import User

    utenti = User.objects.select_related('profile').prefetch_related(
        'groups', 'profile__settore', 'profile__u_o',
    ).filter(
        is_active=True,
    ).exclude(
        is_superuser=True,
    ).order_by('username')

    risultati = []
    for u in utenti:
        # Salta i consiglieri (hanno profilo vuoto per design)
        if is_consigliere(u):
            continue
        profilo = getattr(u, 'profile', None)
        if profilo is None:
            risultati.append({
                'user': u,
                'profilo': None,
                'settore_ok': False,
                'servizio_ok': False,
                'uo_ok': False,
            })
            continue
        settore_ok = profilo.settore is not None
        uo_ok = profilo.u_o is not None
        servizio_ok = uo_ok and profilo.u_o.servizio_storico is not None
        # Per gli user staff basta che il settore sia impostato
        if u.is_staff or u.is_superuser:
            uo_ok = settore_ok
            servizio_ok = settore_ok
        if settore_ok and servizio_ok and uo_ok:
            continue  # profilo completo: non compare nella lista
        risultati.append({
            'user': u,
            'profilo': profilo,
            'settore_ok': settore_ok,
            'servizio_ok': servizio_ok,
            'uo_ok': uo_ok,
        })

    log_action(request, 'VISUALIZZATO', f'Utenti con profilo incompleto',
               {'count': len(risultati)})

    return render(request, 'accounts/profile_incomplete_users.html', {
        'utenti': risultati,
    })


class PasswordChangeCustomView(LoginRequiredMixin, FormView):
    form_class = PasswordChangeCustomForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('home:index')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passiamo l'utente corrente al form per il controllo della password
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        user.set_password(form.cleaned_data.get('new_password'))
        user.save()
        # Mantiene l'utente loggato dopo il cambio password
        update_session_auth_hash(self.request, user)
        messages.success(self.request, 'Password aggiornata con successo!')
        return super().form_valid(form)

    
@login_required
@user_passes_test(_staff_or_superuser)
def user_management_view(request):
    """Visualizza la lista degli utenti e i loro gruppi per la gestione amministrativa."""
    users = User.objects.all().prefetch_related('groups').order_by('username')
    log_action(request, 'VISUALIZZATO', f'User management', {'users_count': users.count()})
    return render(request, 'accounts/user_management.html', {'users': users})

@login_required
@user_passes_test(_staff_or_superuser)
def edit_user_groups(request, user_id):
    """Permette di modificare l'appartenenza ai gruppi per un utente specifico.

    I gruppi 'user_settore_N' e 'editor_settore_N' sono raggruppati per Settore
    e mostrati solo se il Settore corrispondente esiste in struttura_ente.
    I settori 'staff A' / 'Staff B' seguono lo stesso schema con suffisso
    'staff_a' / 'staff_b'.
    I gruppi collegati alle commissioni (TipoCommissione.gruppo_django)
    sono mostrati in una sezione dedicata.
    Tutti gli altri gruppi finiscono nella sezione 'Altri gruppi'.
    """
    user_to_edit = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        selected_groups = request.POST.getlist('groups')
        user_to_edit.groups.set(Group.objects.filter(id__in=selected_groups))
        log_action(request, 'MODIFICATO', f'User {user_to_edit.id}', {'username': user_to_edit.username, 'groups': list(user_to_edit.groups.values_list('name', flat=True))})
        messages.success(request, f"Gruppi aggiornati per l'utente {user_to_edit.username}")
        return redirect('accounts:user_management_url')

    from struttura_ente.models import Settore, TipoCommissione

    Group.objects.get_or_create(name='relatore_commissione')
    settori = list(Settore.objects.all().order_by('codice'))
    all_groups = list(Group.objects.all().order_by('name'))

    def settore_group_suffix(codice):
        """Normalizza il codice settore in un suffisso per i gruppi.
        'settore 6' -> 'settore_6', 'staff A' -> 'staff_a', 'Staff B' -> 'staff_b'
        """
        return codice.lower().strip().replace(' ', '_')

    # Settori "normali" tipo 'settore N'
    settore_by_num = {}
    for s in settori:
        m = re.match(r'^\s*settore\s+(\d+)\s*$', s.codice, re.IGNORECASE)
        if m:
            settore_by_num[m.group(1)] = s

    # Settori "staff" tipo 'staff A', 'Staff B'
    staff_settori = {}
    for s in settori:
        lower = s.codice.lower().strip()
        if lower.startswith('staff'):
            staff_settori[lower] = s

    # Gruppi per settore (settore N), in ordine di codice settore
    settore_groups = []
    used_group_ids = set()
    for num, s in sorted(settore_by_num.items(), key=lambda kv: int(kv[0])):
        user_g = next((g for g in all_groups if g.name == f'user_settore_{num}'), None)
        editor_g = next((g for g in all_groups if g.name == f'editor_settore_{num}'), None)
        if user_g:
            used_group_ids.add(user_g.id)
        if editor_g:
            used_group_ids.add(editor_g.id)
        settore_groups.append({
            'settore': s,
            'user_group': user_g,
            'editor_group': editor_g,
        })

    # Gruppi staff (staff_a, staff_b)
    staff_groups = []
    for lower_key, s in sorted(staff_settori.items(), key=lambda kv: kv[0]):
        suffix = settore_group_suffix(s.codice)
        user_g = next((g for g in all_groups if g.name == f'user_{suffix}'), None)
        editor_g = next((g for g in all_groups if g.name == f'editor_{suffix}'), None)
        if user_g:
            used_group_ids.add(user_g.id)
        if editor_g:
            used_group_ids.add(editor_g.id)
        staff_groups.append({
            'settore': s,
            'user_group': user_g,
            'editor_group': editor_g,
        })

    # Gruppi commissioni (dal TipoCommissione.gruppo_django + gruppo 'consiglieri')
    commissione_group_names = set()
    for tc in TipoCommissione.objects.all():
        if tc.gruppo_django:
            commissione_group_names.add(tc.gruppo_django)
    commissione_group_names.add('consiglieri')

    commissioni_groups = []
    for g in all_groups:
        if g.name in commissione_group_names:
            used_group_ids.add(g.id)
            commissioni_groups.append(g)

    relatore_group = next((g for g in all_groups if g.name == 'relatore_commissione'), None)
    if relatore_group:
        used_group_ids.add(relatore_group.id)

    other_groups = [g for g in all_groups if g.id not in used_group_ids]

    user_groups_ids = list(user_to_edit.groups.values_list('id', flat=True))

    return render(request, 'accounts/edit_user_groups.html', {
        'user_to_edit': user_to_edit,
        'settore_groups': settore_groups,
        'staff_groups': staff_groups,
        'commissioni_groups': commissioni_groups,
        'relatore_group': relatore_group,
        'other_groups': other_groups,
        'user_groups_ids': user_groups_ids,
    })

@login_required
@user_passes_test(_staff_or_superuser)
def toggle_staff(request, user_id):
    """Attiva/disattiva il flag is_staff per un utente specifico."""
    if request.method == 'POST':
        user_to_edit = get_object_or_404(User, id=user_id)
        user_to_edit.is_staff = not user_to_edit.is_staff
        user_to_edit.save()
        log_action(request, 'MODIFICATO', f'User {user_to_edit.id}',
                   {'username': user_to_edit.username, 'is_staff': user_to_edit.is_staff})
        messages.success(request,
                         f"Stato staff {'attivato' if user_to_edit.is_staff else 'rimosso'} per {user_to_edit.username}")
    return redirect('accounts:user_management_url')


@login_required
@user_passes_test(_staff_or_superuser)
def group_management_view(request):
    """Visualizza e gestisce i gruppi e i relativi permessi."""
    Group.objects.get_or_create(name='relatore_commissione')
    groups = Group.objects.all().prefetch_related('permissions').order_by('name')
    
    if request.method == 'POST':
        group_name = request.POST.get('name')
        if group_name:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                log_action(request, 'CREATO', f'Group {group.id}', {'name': group.name})
            messages.success(request, f"Gruppo '{group_name}' creato con successo.")
        return redirect('accounts:group_management_url')

    return render(request, 'accounts/group_management.html', {
        'groups': groups,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_group_permissions(request, group_id):
    """Gestisce l'assegnazione dei permessi a un gruppo."""
    group_to_edit = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        permission_ids = request.POST.getlist('permissions')
        group_to_edit.permissions.set(Permission.objects.filter(id__in=permission_ids))
        log_action(request, 'MODIFICATO', f'Group {group_to_edit.id}', {'name': group_to_edit.name, 'permissions': list(group_to_edit.permissions.values_list('codename', flat=True))})
        messages.success(request, f"Permessi aggiornati per il gruppo {group_to_edit.name}")
        return redirect('accounts:group_management_url')
    
    all_permissions = Permission.objects.select_related('content_type').all().order_by('content_type__app_label', 'codename')
    group_permissions_ids = group_to_edit.permissions.values_list('id', flat=True)
    
    perms_by_app = {}
    for perm in all_permissions:
        app = perm.content_type.app_label
        perms_by_app.setdefault(app, []).append(perm)

    return render(request, 'accounts/edit_group_permissions.html', {
        'group': group_to_edit,
        'perms_by_app': perms_by_app,
        'group_permissions_ids': group_permissions_ids,
    })


@login_required
def richiesta_accesso_pratica(request, pk, tipo='protocollo'):
    from accounts.permissions import is_consigliere
    close_on_success = request.GET.get('from_pdf') == '1' or request.POST.get('from_pdf') == '1'
    from_consigliere = is_consigliere(request.user)
    origine_tipo = None
    if tipo == 'edilizia':
        from edilizia_compat import EDILIZIA_AVAILABLE, EdiliziaPratica
        if not EDILIZIA_AVAILABLE:
            # App archivio non pubblicata nel repository: la pratica
            # non e' consultabile in questa installazione.
            raise Http404("Archivio edilizia non disponibile in questa installazione.")
        pratica = get_object_or_404(EdiliziaPratica, pk=pk)
        pratica_type = 'Edilizia'
        pratica_url_name = 'gest_edilizia:pratica_edit'
        origine_tipo = pratica.origine.nome if pratica.origine else None
    else:
        from protocollo.models import Pratica
        pratica = get_object_or_404(
            _apply_pratica_permissions(Pratica.objects.all(), request.user),
            pk=pk,
        )
        pratica_type = 'Protocollo'
        pratica_url_name = 'protocollo:pratica_edit_url'
        if pratica.tipo_pratica:
            origine_tipo = pratica.tipo_pratica.name

    if request.method == 'POST':
        form = RichiestaAccessoForm(request.POST)
        if form.is_valid():
            motivazione = form.cleaned_data['motivazione']
            utente = request.user
            settore_utente = getattr(getattr(utente, 'profile', None), 'settore', 'N/A')

            subject = f'Richiesta accesso {pratica_type} #{pratica.pk} - {utente.username}'
            origine_label = 'Origine' if tipo == 'edilizia' else 'Tipo pratica'

            # Soggetti e particelle SOLO per il destinatario dell'email
            # (l'amministrazione); il consigliere non li vede mai a video.
            soggetti_lines = []
            particelle_lines = []
            if tipo == 'edilizia':
                for sp in pratica.soggetto_pratica.select_related('soggetto').all() if hasattr(pratica, 'soggetto_pratica') else []:
                    if sp.soggetto:
                        s = sp.soggetto
                        soggetti_lines.append(f"    - {getattr(s, 'cognome', '')} {getattr(s, 'nome', '')} ({getattr(s, 'cf', '') or getattr(s, 'codice_fiscale', '')})")
                if hasattr(pratica, 'particella_pratica'):
                    for p in pratica.particella_pratica.all():
                        particelle_lines.append(f"    - F.{getattr(p, 'foglio', '')} Mapp.{getattr(p, 'mappale', '')}")
            else:
                for sp in pratica.pratiche_soggetti.select_related('soggetto').all():
                    if sp.soggetto:
                        s = sp.soggetto
                        soggetti_lines.append(f"    - {getattr(s, 'cognome', '')} {getattr(s, 'nome', '')} ({getattr(s, 'cf', '') or getattr(s, 'codice_fiscale', '')})")
                for p in pratica.particella_pratica.all():
                    particelle_lines.append(f"    - F.{getattr(p, 'foglio', '')} Mapp.{getattr(p, 'mappale', '')}")

            # Commissioni di appartenenza dell'utente (per il destinatario email)
            commissioni_lines = []
            if from_consigliere:
                for c in utente.commissioni.filter(
                    tipo_commissione__attivo=True,
                    data_fine__isnull=True,
                ).select_related('tipo_commissione', 'settore'):
                    cod = c.tipo_commissione.codice
                    nome = c.tipo_commissione.nome
                    sett = c.settore.codice if c.settore else 'N/D'
                    commissioni_lines.append(f"    - {cod} - {nome} (Settore: {sett})")

            # IP del client (con supporto a X-Forwarded-For dietro proxy)
            xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
            client_ip = (xff.split(',')[0].strip() if xff else '') or request.META.get('REMOTE_ADDR', 'N/D')

            message = (
                f"L'utente {utente.get_full_name()} ({utente.username}) ha richiesto l'accesso alla pratica {pratica_type}:\n\n"
                f"  ID: {pratica.pk}\n"
                f"  Protocollo: {pratica.prot_gen}\n"
                f"  {origine_label}: {origine_tipo or 'N/D'}\n"
                f"  Oggetto: {pratica.oggetto}\n"
                f"  Settore utente: {settore_utente}\n"
                f"  Annotazioni: {pratica.annotazioni or '(nessuna)'}\n\n"
                f"Commissioni di appartenenza:\n" + ("\n".join(commissioni_lines) if commissioni_lines else "    (nessuna)") + "\n\n"
                f"Soggetti:\n" + ("\n".join(soggetti_lines) if soggetti_lines else "    (nessuno)") + "\n\n"
                f"Particelle catastali:\n" + ("\n".join(particelle_lines) if particelle_lines else "    (nessuna)") + "\n\n"
                f"Motivazione:\n{motivazione}\n\n"
                f"IP del client: {client_ip}\n"
                f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'N/D')}\n\n"
                f"Accedi alla pratica: {request.build_absolute_uri(pratica.get_absolute_url())}"
            )

            from mailer.utils import send_notification_email
            try:
                send_notification_email(subject, message)
            except Exception:
                pass

            # Log: registra l'invio della richiesta con i dettagli
            log_action(
                request,
                'RICHIESTA_COPIA_INVIATA',
                f'Pratica {pratica.pk} ({pratica_type})',
                {
                    'pratica_id': pratica.pk,
                    'pratica_type': pratica_type,
                    'prot_gen': pratica.prot_gen or None,
                    'oggetto': pratica.oggetto or None,
                    'n_soggetti': len(soggetti_lines),
                    'n_particelle': len(particelle_lines),
                    'commissioni': commissioni_lines or None,
                    'motivazione': motivazione,
                    'client_ip': client_ip,
                    'user_agent': request.META.get('HTTP_USER_AGENT', 'N/D'),
                    'consigliere': from_consigliere,
                    'richiesta_ricevuta': False,  # sarà implementata in seguito
                },
            )

            messages.success(request, 'Richiesta inviata. Verrai contattato se l\'accesso viene concesso.')
            if from_consigliere:
                # Consiglieri: mostra pagina di conferma con link a 'Le mie
                # Commissioni' (nessun redirect diretto alla pratica).
                return render(request, 'accounts/richiesta_accesso_close.html', {
                    'return_url': reverse('accounts:mie_commissioni_url'),
                })
            if close_on_success:
                if tipo == 'edilizia':
                    return_url = reverse('protocollo:search_protocollo_url')
                else:
                    return_url = reverse('protocollo:search_protocollo_url')
                return render(request, 'accounts/richiesta_accesso_close.html', {
                    'return_url': return_url,
                })
            return redirect(pratica.get_absolute_url())
    else:
        form = RichiestaAccessoForm()

    return render(request, 'accounts/richiesta_accesso.html', {
        'form': form,
        'pratica': pratica,
        'pratica_type': pratica_type,
        'close_on_success': close_on_success,
    })


# ============================================================
# CRUD Commissioni consiliari (admin / staff)
# ============================================================


@login_required
@user_passes_test(_staff_or_superuser)
def commissioni_list(request):
    """Lista delle TipiCommissione raggruppate per Settore (con anche quelle
    non associate a nessun settore). Le commissioni mostrano l'elenco dei
    consiglieri iscritti (accounts.Commissione).
    """
    from struttura_ente.models import Settore, TipoCommissione
    from .models import Commissione

    commissioni_qs = (
        TipoCommissione.objects.all()
        .prefetch_related('settori', 'iscritti__user')
        .order_by('ordine', 'nome')
    )

    # Per ogni commissione, calcola consiglieri attivi
    today = timezone.now().date()
    commissioni_con_iscritti = []
    for c in commissioni_qs:
        iscritti = []
        for iscr in c.iscritti.all():
            attiva = iscr.data_fine is None or iscr.data_fine >= today
            if attiva:
                iscritti.append(iscr)
        commissioni_con_iscritti.append({'c': c, 'iscritti': iscritti})

    # Raggruppamento per settore (M2M)
    by_settore = {}
    for s in Settore.objects.filter(attivo=True).order_by('ordine', 'codice'):
        by_settore[s.pk] = {'settore': s, 'items': []}
    by_settore[None] = {'settore': None, 'items': []}  # bucket "senza settore"

    for item in commissioni_con_iscritti:
        c = item['c']
        settori = list(c.settori.all())
        if not settori:
            by_settore[None]['items'].append(item)
        else:
            for s in settori:
                if s.pk not in by_settore:
                    by_settore[s.pk] = {'settore': s, 'items': []}
                by_settore[s.pk]['items'].append(item)

    # bucket ordinato: settori attivi prima, None bucket alla fine
    gruppi = [g for k, g in by_settore.items() if k is not None and g['items']]
    if by_settore[None]['items']:
        gruppi.append({
            'settore': None,
            'items': by_settore[None]['items'],
        })

    return render(request, 'accounts/commissioni_list.html', {
        'gruppi': gruppi,
    })


@login_required
@user_passes_test(_staff_or_superuser)
def commissione_edit(request, pk=None):
    """Crea/modifica un TipoCommissione. Se pk: modifica; altrimenti nuovo."""
    from struttura_ente.models import Settore, TipoCommissione

    instance = get_object_or_404(TipoCommissione, pk=pk) if pk else None

    if request.method == 'POST':
        codice = (request.POST.get('codice') or '').strip()
        nome = (request.POST.get('nome') or '').strip()
        descrizione = request.POST.get('descrizione', '')
        gruppo_django = (request.POST.get('gruppo_django') or '').strip()
        ordine = int(request.POST.get('ordine') or 0)
        attivo = bool(request.POST.get('attivo'))
        tipo_pratica_ids = request.POST.getlist('tipo_pratica')
        settori_ids = request.POST.getlist('settori')

        if not codice or not nome or not gruppo_django:
            messages.error(request, 'Compilare tutti i campi obbligatori (codice, nome, gruppo_django).')
            return redirect(request.path if not pk else reverse('accounts:commissione_edit_url', args=[pk]))
        if not settori_ids:
            messages.error(request, 'Selezionare almeno un Settore di riferimento.')
            return redirect(request.path if not pk else reverse('accounts:commissione_edit_url', args=[pk]))

        if instance is None:
            if TipoCommissione.objects.filter(codice=codice).exists():
                messages.error(request, f"Esiste gia' un TipoCommissione con codice '{codice}'.")
                return redirect(reverse('accounts:commissione_new_url'))
            instance = TipoCommissione.objects.create(
                codice=codice, nome=nome, descrizione=descrizione,
                gruppo_django=gruppo_django, ordine=ordine, attivo=attivo,
            )
        else:
            instance.codice = codice
            instance.nome = nome
            instance.descrizione = descrizione
            instance.gruppo_django = gruppo_django
            instance.ordine = ordine
            instance.attivo = attivo
            instance.save()
        instance.settori.set(Settore.objects.filter(pk__in=settori_ids))
        instance.tipo_pratica.set(tipo_pratica_ids)

        # Crea il gruppo Django se non esiste
        from django.contrib.auth.models import Group as AuthGroup
        gruppo, creato = AuthGroup.objects.get_or_create(name=instance.gruppo_django)
        if creato or not gruppo.permissions.exists():
            try:
                template = AuthGroup.objects.get(name='user_settore_6')
                gruppo.permissions.set(template.permissions.all())
            except AuthGroup.DoesNotExist:
                pass

        log_action(request, 'MODIFICA COMMISSIONE', f"{instance.codice} - {instance.nome}")
        messages.success(request, f"Commissione '{instance.nome}' salvata.")
        return redirect(reverse('accounts:commissioni_list_url'))

    # GET
    from protocollo.models import TipoPratica
    tipi_pratica = TipoPratica.objects.all().order_by('name')
    tutti_settori = Settore.objects.filter(attivo=True).order_by('ordine', 'codice')

    return render(request, 'accounts/commissione_edit.html', {
        'commissione': instance,
        'tipi_pratica': tipi_pratica,
        'tutti_settori': tutti_settori,
    })


@login_required
@user_passes_test(_staff_or_superuser)
def commissione_delete(request, pk):
    from struttura_ente.models import TipoCommissione
    from .models import Commissione
    from django.contrib.auth.models import Group as AuthGroup
    c = get_object_or_404(TipoCommissione, pk=pk)
    if request.method == 'POST':
        label = f"{c.codice} - {c.nome}"
        related_commissioni = Commissione.objects.filter(tipo_commissione=c)
        count = related_commissioni.count()

        # Rimuovi l'appartenenza al gruppo Django per tutti i consiglieri iscritti
        gruppo_nome = c.gruppo_django
        if gruppo_nome:
            gruppo = AuthGroup.objects.filter(name=gruppo_nome).first()
            if gruppo:
                for iscr in related_commissioni.select_related('user'):
                    if iscr.user:
                        iscr.user.groups.remove(gruppo)
                gruppo.delete()

        if count > 0:
            related_commissioni.delete()
        c.delete()
        log_action(request, 'ELIMINA COMMISSIONE', label)
        if count > 0:
            messages.warning(request, f"Commissione '{label}' eliminata insieme a {count} iscrizione/i consigliere.")
        else:
            messages.success(request, f"Commissione '{label}' eliminata.")
        return redirect(reverse('accounts:commissioni_list_url'))
    return render(request, 'accounts/commissione_confirm_delete.html', {'commissione': c})


@login_required
@user_passes_test(_staff_or_superuser)
def commissione_iscritti(request, pk):
    """Mostra la lista consiglieri iscritti a una commissione e permette
    aggiungere/rimuovere un consigliere (creando il Commissione record)."""
    from struttura_ente.models import TipoCommissione
    from .models import Commissione
    from django.utils import timezone as djtz

    commissione = get_object_or_404(TipoCommissione, pk=pk)
    iscritti = Commissione.objects.filter(tipo_commissione=commissione).select_related('user')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            user_id = request.POST.get('user_id')
            user = get_object_or_404(User, pk=user_id)
            # Snapshot settore
            from struttura_ente.models import StoricoSettore
            settore_snap = None
            s_main = commissione.settore_principale
            if s_main:
                settore_snap = StoricoSettore.objects.filter(
                    codice=s_main.codice, data_fine__isnull=True,
                ).first()
            Commissione.objects.update_or_create(
                user=user, tipo_commissione=commissione,
                defaults={'data_fine': None, 'settore': settore_snap},
            )
            # Aggiungi gruppi
            from .forms import _assegna_gruppo_consigliere
            _assegna_gruppo_consigliere(user, commissione)
            log_action(request, 'AGGIUNGI CONSIGLIERE', f"{user.username} → {commissione.codice}")
            messages.success(request, f"Consigliere {user.username} aggiunto.")
        elif action == 'remove':
            iscr_id = request.POST.get('iscr_id')
            iscr = get_object_or_404(Commissione, pk=iscr_id, tipo_commissione=commissione)
            label = f"{iscr.user.username} ← {commissione.codice}"
            # Rimuovi l'appartenenza al gruppo Django associato
            gruppo_nome = commissione.gruppo_django
            if gruppo_nome and iscr.user:
                from django.contrib.auth.models import Group as AuthGroup
                gruppo = AuthGroup.objects.filter(name=gruppo_nome).first()
                if gruppo:
                    iscr.user.groups.remove(gruppo)
            iscr.delete()
            log_action(request, 'RIMUOVI CONSIGLIERE', label)
            messages.success(request, f"Consigliere rimosso.")
        return redirect(reverse('accounts:commissione_iscritti_url', args=[pk]))

    # candidati: utenti in 'consiglieri' group non ancora iscritti a questa commissione
    iscritti_user_ids = set(iscritti.values_list('user_id', flat=True))
    candidati = User.objects.filter(groups__name='consiglieri').exclude(pk__in=iscritti_user_ids).order_by('username')

    return render(request, 'accounts/commissione_iscritti.html', {
        'commissione': commissione,
        'iscritti': iscritti,
        'candidati': candidati,
    })


@login_required
def mie_commissioni(request):
    """Pagina 'Le mie commissioni' per il consigliere loggato.

    Mostra tutte le Commissione attive dell'utente. Se l'utente NON e' un
    consigliere, mostra un messaggio. Se ha piu' commissioni, puo' selezionare
    quale guardare tramite GET param ?commissione=<pk>. La pagina mostra
    l'elenco delle Pratiche filtrate per i TipiPratica della commissione
    selezionata (e il settore snapshot).
    """
    from accounts.models import Commissione
    from protocollo.models import Pratica

    user = request.user
    commissioni = (
        user.commissioni
        .filter(tipo_commissione__attivo=True)
        .select_related('tipo_commissione', 'settore')
        .prefetch_related('tipo_commissione__tipo_pratica', 'tipo_commissione__settori')
        .order_by('tipo_commissione__ordine', 'tipo_commissione__nome')
    )

    selezionata = None
    pratiche = Pratica.objects.none()
    tipo_ids_selezionata = []
    selezionata_pk = request.GET.get('commissione')
    if selezionata_pk:
        try:
            selezionata = commissioni.get(pk=int(selezionata_pk))
        except (Commissione.DoesNotExist, ValueError):
            selezionata = None

    # Se non c'e' selezione esplicita, prendi la prima commissione
    if selezionata is None and commissioni.exists():
        selezionata = commissioni.first()

    if selezionata:
        tipo_ids_selezionata = sorted({
            tp.id for tp in selezionata.tipo_commissione.tipo_pratica.all()
        })
        qs = Pratica.objects.all()
        # Filtro autorizzativo (applica la Q della commissione + settore)
        qs = _apply_pratica_permissions(qs, user)
        if tipo_ids_selezionata:
            qs = qs.filter(tipo_pratica_id__in=tipo_ids_selezionata)
        else:
            # Commissione senza TipiPratica: mostra tutte le pratiche del
            # settore (grazie al filtro autorizzativo)
            pass
        # Filtri opzionali da GET (ricerca protocollo / anno)
        prot_gen_q = (request.GET.get('prot_gen') or '').strip()
        anno_q = (request.GET.get('anno') or '').strip()
        # Di default NON mostrare tutte le pratiche: l'utente deve cercare.
        pratiche = Pratica.objects.none()
        if prot_gen_q or anno_q:
            if prot_gen_q:
                qs = qs.filter(
                    Q(prot_gen__icontains=prot_gen_q) |
                    Q(code_p__icontains=prot_gen_q)
                )
            if anno_q:
                try:
                    qs = qs.filter(data_prot_gen__year=int(anno_q))
                except ValueError:
                    messages.warning(request, f"Anno '{anno_q}' non valido.")
                    qs = qs.none()
            pratiche = qs.distinct().order_by('-data_mod', '-id')[:200]
        else:
            prot_gen_q = ''
            anno_q = ''
        # Log azione consigliere (solo se consigliere) - campi minimi
        if is_consigliere(user):
            log_action(
                request,
                'VISUALIZZATO',
                f'Le mie Commissioni - {selezionata.tipo_commissione.codice}',
                {
                    'commissione_codice': selezionata.tipo_commissione.codice,
                    'filtro_prot_gen': prot_gen_q or None,
                    'filtro_anno': anno_q or None,
                    'n_risultati': len(pratiche),
                },
            )

    return render(request, 'accounts/mie_commissioni.html', {
        'commissioni': commissioni,
        'selezionata': selezionata,
        'pratiche': pratiche,
        'tipo_ids_selezionata': tipo_ids_selezionata,
        'prot_gen_q': prot_gen_q if selezionata else '',
        'anno_q': anno_q if selezionata else '',
        'ricerca_eseguita': bool(selezionata and (prot_gen_q or anno_q)),
    })


class CustomLoginView(DjangoLoginView):
    """Login view che redirrige i consiglieri direttamente a 'Le mie
    Commissioni' inveito che a SearchProt / home.

    Per gli altri utenti, se il profilo (settore/servizio/uo) non e' completo,
    reindirizza alla verifica impostazioni profilo.
    """

    def get_success_url(self):
        user = self.request.user
        if is_consigliere(user):
            return reverse('accounts:mie_commissioni_url')
        if not _profile_completo(user):
            return reverse('accounts:profile_settore_check_url')
        if not user.has_perm('protocollo.visualizza_tipo_pratica'):
            return reverse('accounts:profile_view_url')
        return super().get_success_url()