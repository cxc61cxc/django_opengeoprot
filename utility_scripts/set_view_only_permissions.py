#!/usr/bin/env python
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carrara.settings')

import django
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


GROUP_NAME = 'user_settore_1'


def set_view_only_permissions():
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    updated_view = 0
    removed_change = 0
    removed_delete = 0

    for model in apps.get_models():
        ct = ContentType.objects.get_for_model(model)
        base_codename = model._meta.model_name
        verbose = model._meta.verbose_name

        view_perm, _ = Permission.objects.get_or_create(
            codename=f'view_{base_codename}',
            content_type=ct,
            defaults={'name': f'Can view {verbose}'},
        )
        if view_perm not in group.permissions.all():
            group.permissions.add(view_perm)
            updated_view += 1

        for action in ('change', 'delete'):
            perm = Permission.objects.filter(
                codename=f'{action}_{base_codename}',
                content_type=ct,
            ).first()
            if perm and perm in group.permissions.all():
                group.permissions.remove(perm)
                if action == 'change':
                    removed_change += 1
                else:
                    removed_delete += 1

    print(f"Gruppo '{GROUP_NAME}' aggiornato.")
    print(f"Permessi view aggiunti: {updated_view}")
    print(f"Permessi change rimossi: {removed_change}")
    print(f"Permessi delete rimossi: {removed_delete}")


if __name__ == '__main__':
    set_view_only_permissions()
