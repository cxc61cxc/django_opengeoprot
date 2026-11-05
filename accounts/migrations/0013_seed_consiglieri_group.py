from django.db import migrations


def crea_gruppo_consiglieri(apps, schema_editor):
    """Crea il gruppo 'consiglieri' (raggruppa tutti i consiglieri) clonato
    dai permessi di 'user_settore_6'. Il gruppo verra' usato per identificare
    gli utenti che hanno accesso limitato al solo profilo personale.
    """
    Group = apps.get_model('auth', 'Group')
    gruppo, creato = Group.objects.get_or_create(name='consiglieri')
    if creato or not gruppo.permissions.exists():
        try:
            template = Group.objects.get(name='user_settore_6')
            gruppo.permissions.set(template.permissions.all())
        except Group.DoesNotExist:
            pass


def rimuovi_gruppo_consiglieri(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='consiglieri').delete()


def seed_tipo_commissione_poc_2022(apps, schema_editor):
    """Crea il TipoCommissione 'POC 2022' (codice=poc_2022) legato al gruppo
    'consosspoc2022' se non esiste gia'.
    """
    TipoCommissione = apps.get_model('struttura_ente', 'TipoCommissione')
    TipoCommissione.objects.get_or_create(
        codice='poc_2022',
        defaults={
            'nome': 'Osservazioni POC 2022',
            'descrizione': "Commissione consigliare per l'esame delle osservazioni al POC 2022.",
            'gruppo_django': 'consosspoc2022',
            'ordine': 10,
            'attivo': True,
        },
    )


def unseed_tipo_commissione_poc_2022(apps, schema_editor):
    TipoCommissione = apps.get_model('struttura_ente', 'TipoCommissione')
    TipoCommissione.objects.filter(codice='poc_2022').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_add_consosspoc2022_group'),
        ('struttura_ente', '0005_tipocommissione'),
    ]

    operations = [
        migrations.RunPython(crea_gruppo_consiglieri, rimuovi_gruppo_consiglieri),
        migrations.RunPython(seed_tipo_commissione_poc_2022, unseed_tipo_commissione_poc_2022),
    ]