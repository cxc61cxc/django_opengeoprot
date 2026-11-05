from django.db import migrations


def seed_tipo_commissione_2(apps, schema_editor):
    """Crea un TipoCommissione di prova ('commissione 2') con gruppo Django
    'conscommissione2'. Non filtra per tipo_pratica (campo nullo).
    """
    TipoCommissione = apps.get_model('struttura_ente', 'TipoCommissione')
    TipoCommissione.objects.get_or_create(
        codice='commissione_2',
        defaults={
            'nome': 'Commissione 2',
            'descrizione': "Commissione consigliare di test (commissione 2).",
            'gruppo_django': 'conscommissione2',
            'ordine': 20,
            'attivo': True,
        },
    )


def unseed_tipo_commissione_2(apps, schema_editor):
    TipoCommissione = apps.get_model('struttura_ente', 'TipoCommissione')
    TipoCommissione.objects.filter(codice='commissione_2').delete()


def crea_gruppo_conscommissione2(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    gruppo, creato = Group.objects.get_or_create(name='conscommissione2')
    if creato or not gruppo.permissions.exists():
        try:
            template = Group.objects.get(name='user_settore_6')
            gruppo.permissions.set(template.permissions.all())
        except Group.DoesNotExist:
            pass


def rimuovi_gruppo_conscommissione2(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='conscommissione2').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('struttura_ente', '0006_tipocommissione_tipo_pratica'),
    ]

    operations = [
        migrations.RunPython(crea_gruppo_conscommissione2, rimuovi_gruppo_conscommissione2),
        migrations.RunPython(seed_tipo_commissione_2, unseed_tipo_commissione_2),
    ]