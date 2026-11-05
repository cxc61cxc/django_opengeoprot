from accounts.permissions import is_editor as _is_editor, is_manager as _is_manager


def navbar_context(request):
    user = getattr(request, 'user', None)
    return {
        'is_editor': bool(user and user.is_authenticated and _is_editor(user)),
        'is_manager': bool(user and user.is_authenticated and _is_manager(user)),
    }
