from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import settore_choice, Profile


class RichiestaAccessoForm(forms.Form):
    motivazione = forms.CharField(
        label='Motivazione',
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Inserisci la motivazione della richiesta...'}),
        required=True,
        max_length=500,
    )


def get_settore_choices():
    """Restituisce le scelte settore leggendo i Settori vigenti in struttura_ente."""
    try:
        from struttura_ente.models import StoricoSettore
        vigenti = StoricoSettore.objects.filter(data_fine__isnull=True).order_by('codice')
        choices = [('', '---------')]
        for v in vigenti:
            choices.append((v.codice, f'{v.codice} - {v.nome}'))
        if len(choices) > 1:
            return choices
    except Exception:
        pass
    return [('', '---------')] + [(c, n) for c, n in settore_choice]


def get_servizio_choices(settore_codice=None):
    """Restituisce i Servizi vigenti del Settore indicato (o tutti se None)."""
    try:
        from struttura_ente.models import StoricoServizio
        qs = StoricoServizio.objects.filter(data_fine__isnull=True).select_related('settore_storico')
        if settore_codice:
            qs = qs.filter(settore_storico__codice=settore_codice)
        choices = [('', '---------')]
        for s in qs.order_by('settore_storico__codice', 'codice'):
            choices.append((s.id, f'{s.settore_storico.codice} / {s.codice} - {s.nome}'))
        if len(choices) > 1:
            return choices
    except Exception:
        pass
    return [('', '---------')]


def get_uo_choices(settore_codice=None, servizio_id=None):
    """Restituisce le AttivitaUO vigenti del Servizio indicato (o del Settore)."""
    try:
        from struttura_ente.models import StoricoAttivitaUO
        qs = StoricoAttivitaUO.objects.filter(data_fine__isnull=True).select_related(
            'servizio_storico__settore_storico'
        )
        if servizio_id:
            qs = qs.filter(servizio_storico_id=servizio_id)
        elif settore_codice:
            qs = qs.filter(servizio_storico__settore_storico__codice=settore_codice)
        choices = [('', '---------')]
        for u in qs.order_by('servizio_storico__settore_storico__codice', 'servizio_storico__codice', 'nome'):
            choices.append((
                u.id,
                f'{u.servizio_storico.settore_storico.codice} / {u.servizio_storico.codice} / {u.nome}',
            ))
        if len(choices) > 1:
            return choices
    except Exception:
        pass
    return [('', '---------')]


def sync_user_group_by_settore(user, settore_label):
    """Assegna all'utente i gruppi corretti in base al Settore (testuale)."""
    settore = settore_label
    if settore:
        if settore.startswith('settore '):
            num = settore.split(' ')[1]
            target_group_name = f'user_settore_{num}'
        else:
            target_group_name = f'user_{settore.lower().replace(" ", "_").replace("/", "_")}'

        groups_to_remove = user.groups.filter(
            Q(name__startswith='user_settore_') |
            Q(name__startswith='user_staff_')
        ).exclude(name=target_group_name)
        user.groups.remove(*groups_to_remove)

        group, created = Group.objects.get_or_create(name=target_group_name)
        if created:
            try:
                template_group = Group.objects.get(name='user_settore_6')
                group.permissions.set(template_group.permissions.all())
            except Group.DoesNotExist:
                pass
        user.groups.add(group)

    if user.is_staff or user.is_superuser:
        readonly_group, _ = Group.objects.get_or_create(name='readonly')
        user.groups.add(readonly_group)


def _resolve_servizio_storico(servizio_id):
    if not servizio_id:
        return None
    from struttura_ente.models import StoricoServizio
    return StoricoServizio.objects.filter(pk=servizio_id, data_fine__isnull=True).first()


def _resolve_uo_storico(uo_id):
    if not uo_id:
        return None
    from struttura_ente.models import StoricoAttivitaUO
    return StoricoAttivitaUO.objects.filter(pk=uo_id, data_fine__isnull=True).first()


def get_commissione_choices():
    """Restituisce le commissioni attive in struttura_ente."""
    try:
        from struttura_ente.models import TipoCommissione
        qs = TipoCommissione.objects.filter(attivo=True).order_by('ordine', 'nome')
        choices = [('', '---------')]
        for c in qs:
            choices.append((str(c.id), c.nome))
        if len(choices) > 1:
            return choices
    except Exception:
        pass
    return [('', '---------')]


def _assegna_gruppo_consigliere(user, tipo_commissione):
    """Crea (se mancante) il gruppo indicato dal TipoCommissione, clona i
    permessi da 'user_settore_6' e aggiunge l'utente.
    Aggiunge SEMPRE anche il gruppo 'consiglieri' (per i permessi di base
    comuni: profile view-only, password change, ecc.).
    Logga l'operazione in user_actions.log.
    """
    import logging
    logger = logging.getLogger('user_actions')

    gruppo_nome = tipo_commissione.gruppo_django
    gruppo, creato = Group.objects.get_or_create(name=gruppo_nome)
    if creato or not gruppo.permissions.exists():
        try:
            template = Group.objects.get(name='user_settore_6')
            gruppo.permissions.set(template.permissions.all())
        except Group.DoesNotExist:
            pass
    user.groups.add(gruppo)

    consiglieri, _ = Group.objects.get_or_create(name='consiglieri')
    if not consiglieri.permissions.exists():
        try:
            template = Group.objects.get(name='user_settore_6')
            consiglieri.permissions.set(template.permissions.all())
        except Group.DoesNotExist:
            pass
    user.groups.add(consiglieri)

    logger.info(
        f"REGISTRAZIONE CONSIGLIERE: username={user.username} "
        f"commissione={tipo_commissione.codice} ({tipo_commissione.nome}) "
        f"gruppo={gruppo_nome}"
    )
    return gruppo


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(label='Nome', max_length=30, required=True)
    last_name = forms.CharField(label='Cognome', max_length=30, required=True)
    email = forms.EmailField(max_length=254, required=True)
    settore = forms.ChoiceField(choices=get_settore_choices, required=False)
    servizio = forms.ChoiceField(choices=[('', '---------')], required=False)
    u_o = forms.ChoiceField(choices=[('', '---------')], required=False)
    consigliere = forms.BooleanField(
        label='Consigliere di una commissione',
        required=False,
        help_text='Selezionare se si è Consiglieri comunali. '
                  'L\'accesso sarà limitato in sola lettura al proprio profilo '
                  'e alle pratiche relative alle commissioni selezionate.',
    )
    commissioni = forms.MultipleChoiceField(
        choices=get_commissione_choices,
        required=False,
        help_text='Selezionare una o più commissioni di cui si è membri '
                  '(visibile solo se "Consigliere" è spuntato).',
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aggiorna le scelte della commissione (potrebbero essere cambiate)
        self.fields['commissioni'].choices = get_commissione_choices()
        # popola servizio/u_o in base al settore corrente del form
        initial_settore = self.data.get('settore') or (self.initial.get('settore') if hasattr(self, 'initial') else None) or ''
        self.fields['servizio'].choices = get_servizio_choices(initial_settore)
        self.fields['u_o'].choices = get_uo_choices(initial_settore)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.email = self.cleaned_data.get('email')
        is_consigliere = self.cleaned_data.get('consigliere', False)
        commissione_ids = self.cleaned_data.get('commissioni') or []

        if commit:
            user.save()
            if is_consigliere:
                from struttura_ente.models import TipoCommissione, StoricoSettore
                from .models import Commissione
                # Consigliere: nessun settore/uo sul Profile
                Profile.objects.update_or_create(
                    user=user,
                    defaults={'settore': None, 'u_o': None},
                )
                for cid in commissione_ids:
                    tc = TipoCommissione.objects.filter(pk=cid, attivo=True).first()
                    if not tc:
                        continue
                    _assegna_gruppo_consigliere(user, tc)
                    # Snapshot del settore principale della commissione (se presente)
                    settore_snap = None
                    s_main = tc.settore_principale
                    if s_main:
                        settore_snap = StoricoSettore.objects.filter(
                            codice=s_main.codice, data_fine__isnull=True,
                        ).first()
                    Commissione.objects.update_or_create(
                        user=user,
                        tipo_commissione=tc,
                        defaults={'data_fine': None, 'settore': settore_snap},
                    )
                if not commissione_ids:
                    # Commissione non valida: solo gruppo consiglieri
                    consiglieri, _ = Group.objects.get_or_create(name='consiglieri')
                    user.groups.add(consiglieri)
            else:
                from struttura_ente.models import StoricoSettore
                settore_storico = StoricoSettore.objects.filter(
                    codice=self.cleaned_data.get('settore'),
                    data_fine__isnull=True,
                ).first()
                servizio_storico = _resolve_servizio_storico(self.cleaned_data.get('servizio'))
                uo_storico = _resolve_uo_storico(self.cleaned_data.get('u_o'))
                Profile.objects.update_or_create(
                    user=user,
                    defaults={
                        'settore': settore_storico,
                        'u_o': uo_storico,
                    },
                )
                sync_user_group_by_settore(user, self.cleaned_data.get('settore'))
        return user

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        if email and '@comune.carrara.ms.it' not in email:
            self.add_error('email', "Indirizzo email non accettato, contatta l'amministrazione")
        is_consigliere = cleaned_data.get('consigliere')
        commissioni = cleaned_data.get('commissioni')
        if is_consigliere:
            if not commissioni:
                self.add_error('commissioni', "Selezionare almeno una commissione di cui si è membri.")
        else:
            if not cleaned_data.get('settore'):
                self.add_error('settore', "Selezionare un settore oppure spuntare 'Consigliere'.")
        return cleaned_data


class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(label='Nome', max_length=30, required=True)
    last_name = forms.CharField(label='Cognome', max_length=30, required=True)
    email = forms.EmailField(max_length=254, required=True)
    settore = forms.ChoiceField(choices=get_settore_choices, required=True)
    servizio = forms.ChoiceField(choices=[('', '---------')], required=False)
    u_o = forms.ChoiceField(choices=[('', '---------')], required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('instance'):
            user = kwargs['instance']
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            profile, _ = Profile.objects.get_or_create(user=user)
            initial_settore = self.data.get('settore') or (
                profile.settore.codice if profile.settore else ''
            )
            self.fields['settore'].initial = initial_settore
            self.fields['servizio'].choices = get_servizio_choices(initial_settore)
            self.fields['u_o'].choices = get_uo_choices(initial_settore)
            self.fields['servizio'].initial = self.data.get('servizio') or (
                str(profile.u_o.servizio_storico_id) if profile.u_o and profile.u_o.servizio_storico else ''
            )
            self.fields['u_o'].initial = self.data.get('u_o') or (
                str(profile.u_o_id) if profile.u_o_id else ''
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.email = self.cleaned_data.get('email')

        if commit:
            user.save()
            from struttura_ente.models import StoricoSettore
            settore_storico = StoricoSettore.objects.filter(
                codice=self.cleaned_data.get('settore'),
                data_fine__isnull=True,
            ).first()
            servizio_storico = _resolve_servizio_storico(self.cleaned_data.get('servizio'))
            uo_storico = _resolve_uo_storico(self.cleaned_data.get('u_o'))
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    'settore': settore_storico,
                    'u_o': uo_storico,
                },
            )
            sync_user_group_by_settore(user, self.cleaned_data.get('settore'))
        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and '@comune.carrara.ms.it' not in email:
            raise ValidationError("Indirizzo email non accettato, contatta l'amministrazione")
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Questa email è già in uso da un altro utente.')
        return email


class PasswordChangeCustomForm(forms.Form):
    current_password = forms.CharField(
        label='Password Attuale',
        widget=forms.PasswordInput,
        required=True,
    )
    new_password = forms.CharField(
        label='Nuova Password',
        widget=forms.PasswordInput,
        required=True,
    )
    confirm_password = forms.CharField(
        label='Conferma Nuova Password',
        widget=forms.PasswordInput,
        required=True,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get('current_password')
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if current_password and not self.user.check_password(current_password):
            self.add_error('current_password', 'La password attuale non è corretta.')

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', 'Le password non coincidono.')
        return cleaned_data