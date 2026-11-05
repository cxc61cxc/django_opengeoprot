from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('struttura_ente', '0004_servizi_attivita'),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoCommissione',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codice', models.CharField(help_text="Codice breve (es. 'poc_2022', 'urbanistica')", max_length=50, unique=True)),
                ('nome', models.CharField(help_text='Nome esteso della commissione', max_length=200)),
                ('descrizione', models.TextField(blank=True)),
                ('gruppo_django', models.CharField(help_text="Nome del gruppo Django a cui verra' aggiunto il consigliere (verra' creato al volo se non esiste).", max_length=100)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('attivo', models.BooleanField(default=True)),
                ('data_creazione', models.DateTimeField(auto_now_add=True)),
                ('data_modifica', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Tipo Commissione',
                'verbose_name_plural': 'Tipi Commissione',
                'ordering': ['ordine', 'nome'],
            },
        ),
    ]