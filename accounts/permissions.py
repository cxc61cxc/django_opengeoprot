from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied

EDITOR_GROUPS = ['editor_settore_6', 'editor_settore_1']
EDITOR_GROUPS_STRICT = ['editor_settore_6']
VIEWER_GROUPS = ['user_settore_1', 'user_settore_6']
ARCHIVIO_GROUPS = ['archivio_settore_6', 'user_settore_6']
EDITOR_SETTORE_GROUPS = ['editor_settore_6', 'editor_settore_1', 'editor_settore_5']
ALL_GROUPS = EDITOR_GROUPS + VIEWER_GROUPS


def is_editor(user):
    return user.groups.filter(name__in=EDITOR_GROUPS).exists()


def is_user(user):
    return user.groups.filter(name__startswith='user_settore_').exists()


def is_manager(user):
    return user.is_superuser or user.is_staff or user.groups.filter(name__in=EDITOR_GROUPS).exists()


def is_consigliere(user):
    """True se l'utente appartiene al gruppo 'consiglieri' oppure ha
    almeno una Commissione attiva. Usato per consentire ai consiglieri
    l'accesso in sola lettura alle sole pratiche delle commissioni a cui
    sono iscritti.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return False
    if user.groups.filter(name='consiglieri').exists():
        return True
    from accounts.models import Commissione
    return user.commissioni.filter(tipo_commissione__attivo=True).exists()


def editor_required(function=None, *, strict=False, allow_viewers=False):
    groups = EDITOR_GROUPS_STRICT if strict else EDITOR_GROUPS
    if allow_viewers:
        test = lambda u: u.is_superuser or u.is_staff or u.groups.filter(name__in=groups).exists() or is_user(u) or u.groups.filter(name='readonly').exists()
    else:
        test = lambda u: u.is_superuser or u.is_staff or u.groups.filter(name__in=groups).exists()
    decorator = user_passes_test(
        test,
        login_url='home:index',
    )
    if function:
        return decorator(function)
    return decorator


def viewer_required(function=None):
    decorator = user_passes_test(
        lambda u: u.is_superuser or u.groups.filter(name__in=VIEWER_GROUPS).exists(),
        login_url='home:index',
    )
    if function:
        return decorator(function)
    return decorator


def archivio_edilizia_required(function=None):
    def check(u):
        return u.is_superuser or u.is_staff or u.groups.filter(name='archivio_settore_6').exists() or u.groups.filter(name='user_settore_6').exists() or u.groups.filter(name__startswith='editor_settore_').exists()

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if check(request.user):
                return view_func(request, *args, **kwargs)
            pk = kwargs.get('pk') or kwargs.get('id')
            if pk:
                return redirect(f'{reverse("accounts:richiesta_accesso_edilizia", args=[pk])}?from_pdf=1')
            return redirect('home:index')
        return wrapper
    if function:
        return decorator(function)
    return decorator


def user_passes_test_403(test_func):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            raise PermissionDenied("Non hai i permessi per accedere a questa pagina.")
        return _wrapped_view
    return decorator
