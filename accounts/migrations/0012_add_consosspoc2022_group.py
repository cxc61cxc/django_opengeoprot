from django.db import migrations


def crea_gruppo_consosspoc2022(apps, schema_editor):
    """Crea il gruppo 'consosspoc2022' clonato dai permessi di 'user_settore_6'.
    Sara' usato dai consiglieri comunali per l'accesso readonly limitato alle
    sole pratiche di osservazioni POC 2022 (TipoPratica id=30).
    """
    Group = apps.get_model('auth', 'Group')

    gruppo, creato = Group.objects.get_or_create(name='consosspoc2022')
    if creato or not gruppo.permissions.exists():
        try:
            template = Group.objects.get(name='user_settore_6')
            gruppo.permissions.set(template.permissions.all())
        except Group.DoesNotExist:
            pass


def rimuovi_gruppo_consosspoc2022(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='consosspoc2022').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_alter_profile_u_o'),
    ]

    operations = [
        migrations.RunPython(crea_gruppo_consosspoc2022, rimuovi_gruppo_consosspoc2022),
    ]