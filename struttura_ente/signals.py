import re
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group


_USER_TEMPLATE = 'user_settore_6'
_EDITOR_TEMPLATE = 'editor_settore_1'

# Settore 6 (Governo del Territorio) e' l'unico con permessi legacy specifici
# gia' definiti: NON sovrascriverne i permessi se il gruppo esiste gia'.
_SKIP_OVERWRITE = {'6'}


def _num_da_codice(codice):
    """Estrae la parte numerica finale da un codice tipo 'Settore 5' o 'settore 5'.
    Ritorna la stringa numerica o None se non matcha.
    """
    if not codice:
        return None
    m = re.match(r'^\s*settore\s+(\d+)\s*$', codice, re.IGNORECASE)
    return m.group(1) if m else None


def _crea_gruppi_per_settore(codice_settore, force=False):
    """Crea i gruppi user_settore_X e editor_settore_X se non esistono,
    copiando i permessi dai template (user_settore_6 per utenti readonly,
    editor_settore_5 per editor).

    Se il gruppo esiste gia' e non e' 'vuoto' (force=False) i permessi
    esistenti non vengono sovrascritti. Settore 6 viene saltato del tutto
    perche' il gruppo user_settore_6 e' il template stesso.

    Ritorna (user_group, editor_group) o None se il codice non e' un settore.
    """
    num = _num_da_codice(codice_settore)
    if num is None:
        return None
    if num == '6':
        return None

    user_group_name = f'user_settore_{num}'
    editor_group_name = f'editor_settore_{num}'

    user_group, _ = Group.objects.get_or_create(name=user_group_name)
    if force or not user_group.permissions.exists():
        try:
            template_user = Group.objects.get(name=_USER_TEMPLATE)
            user_group.permissions.set(template_user.permissions.all())
        except Group.DoesNotExist:
            pass

    editor_group, _ = Group.objects.get_or_create(name=editor_group_name)
    if force or not editor_group.permissions.exists():
        try:
            template_editor = Group.objects.get(name=_EDITOR_TEMPLATE)
            editor_group.permissions.set(template_editor.permissions.all())
        except Group.DoesNotExist:
            pass

    return user_group, editor_group


@receiver(post_save, sender='struttura_ente.Settore')
def crea_gruppi_settore(sender, instance, created, **kwargs):
    """Quando viene creato un Settore 'Settore N' (N != 6),
    crea automaticamente i gruppi user_settore_N e editor_settore_N.
    """
    if not created:
        return
    _crea_gruppi_per_settore(instance.codice)