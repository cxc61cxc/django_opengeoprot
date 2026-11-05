from django import template

register = template.Library()


@register.filter(name='is_consigliere')
def is_consigliere(user):
    """Ritorna True se l'utente e' un consigliere (gruppo 'consiglieri'
    oppure ha almeno una accounts.Commissione attiva).
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser or user.is_staff:
        return False
    if user.groups.filter(name='consiglieri').exists():
        return True
    if hasattr(user, 'commissioni'):
        from accounts.models import Commissione
        if Commissione.objects.filter(user=user, tipo_commissione__attivo=True).exists():
            return True
    return False


def _has_complete_profile(user):
    """Ritorna True se l'utente ha definito settore, servizio e UO nel profilo.

    Staff e superuser sono sempre considerati completi (esclusi dal check).
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_staff or user.is_superuser:
        return True
    try:
        profile = user.profile
    except Exception:
        return False
    if not profile.settore:
        return False
    if not profile.u_o:
        return False
    if not profile.u_o.servizio_storico:
        return False
    return True


@register.filter(name='can_use_protocollo')
def can_use_protocollo(user):
    """Ritorna True se l'utente puo' accedere ai menu di protocollo.

    Staff e superuser sempre; altrimenti serve profilo completo
    (settore + servizio + UO definiti).
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_staff or user.is_superuser:
        return True
    return _has_complete_profile(user)