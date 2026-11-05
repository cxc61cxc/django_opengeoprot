#!/usr/bin/env python
import os
import sys
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carrara.settings')

import django
django.setup()

from django.contrib.auth.models import Group, Permission
from django.db import transaction


def copy_permissions(source_name, dest_name, clear=False):
    source = Group.objects.get(name=source_name)
    dest = Group.objects.get(name=dest_name)

    print(f"Sorgente   : {source.name} (id={source.pk})")
    print(f"Destinazione: {dest.name} (id={dest.pk})")

    source_perms = source.permissions.all()
    source_count = source_perms.count()
    print(f"Permessi nel gruppo sorgente: {source_count}")

    if clear:
        dest.permissions.clear()
        print("Permessi rimossi dal gruppo destinazione.")
        to_add = source_perms
    else:
        existing_count = dest.permissions.count()
        print(f"Permessi attuali nel gruppo destinazione: {existing_count}")
        to_add = source_perms.exclude(pk__in=dest.permissions.values_list('pk', flat=True))

    to_add_count = to_add.count()
    print(f"Permessi da aggiungere: {to_add_count}")

    if to_add_count == 0:
        print("Nessun permesso nuovo da aggiungere.")
        return

    through_model = Group._meta.get_field('permissions').remote_field.through
    through_objs = [
        through_model(group=dest, permission_id=pk)
        for pk in to_add.values_list('pk', flat=True)
    ]
    with transaction.atomic():
        through_model.objects.bulk_create(through_objs, ignore_conflicts=True)
    print(f"Aggiunti {to_add_count} permessi da '{source_name}' a '{dest_name}'.")


def main():
    parser = argparse.ArgumentParser(description='Copia i permessi da un gruppo Django a un altro.')
    parser.add_argument('source', help='Nome del gruppo sorgente')
    parser.add_argument('destination', help='Nome del gruppo destinazione')
    parser.add_argument('--clear', action='store_true', help='Svuota i permessi del gruppo destinazione prima di copiare')
    args = parser.parse_args()

    copy_permissions(args.source, args.destination, clear=args.clear)


if __name__ == '__main__':
    main()
