from django.contrib.auth.models import Group

from edilizia_compat import EDILIZIA_AVAILABLE, GEST_EDILIZIA_AVAILABLE


READONLY_PREFIX = 'user_settore'


def readonly_flags(request):
    user = getattr(request, 'user', None)
    is_readonly = bool(
        user and user.is_authenticated and
        user.groups.filter(name__startswith=READONLY_PREFIX).exists()
    )
    return {
        'is_readonly': is_readonly,
        'can_write': not is_readonly,
        # App opzionali dell'archivio storico (non pubblicate nel repo):
        # usati dai template per nascondere i link a edilizia/gest_edilizia.
        'edilizia_available': EDILIZIA_AVAILABLE,
        'gest_edilizia_available': GEST_EDILIZIA_AVAILABLE,
    }
