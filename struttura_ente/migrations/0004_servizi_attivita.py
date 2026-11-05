import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('struttura_ente', '0003_rename_struttura_e_codice__idx_struttura_e_codice_bb7ff5_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Servizio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codice', models.CharField(help_text='Codice breve del servizio', max_length=20)),
                ('nome', models.CharField(max_length=200)),
                ('descrizione', models.TextField(blank=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('attivo', models.BooleanField(default=True)),
                ('data_creazione', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('data_modifica', models.DateTimeField(auto_now=True, default=django.utils.timezone.now)),
                ('settore', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='servizi', to='struttura_ente.settore')),
            ],
            options={
                'verbose_name': 'Servizio',
                'verbose_name_plural': 'Servizi',
                'ordering': ['settore__ordine', 'settore__codice', 'ordine', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='AttivitaUO',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120)),
                ('descrizione', models.TextField(blank=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('attivo', models.BooleanField(default=True)),
                ('data_creazione', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
                ('data_modifica', models.DateTimeField(auto_now=True, default=django.utils.timezone.now)),
                ('servizio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attivita', to='struttura_ente.servizio')),
            ],
            options={
                'verbose_name': 'Attivita U.O.',
                'verbose_name_plural': 'Attivita U.O.',
                'ordering': ['servizio__settore__ordine', 'servizio__ordine', 'ordine', 'nome'],
            },
        ),
        migrations.CreateModel(
            name='StoricoServizio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codice', models.CharField(max_length=20)),
                ('nome', models.CharField(max_length=200)),
                ('descrizione', models.TextField(blank=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('atto_riferimento', models.CharField(blank=True, max_length=255)),
                ('data_inizio', models.DateTimeField()),
                ('data_fine', models.DateTimeField(blank=True, null=True)),
                ('servizio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versioni', to='struttura_ente.servizio')),
                ('settore_storico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='servizi_versioni', to='struttura_ente.storicosettore')),
            ],
            options={
                'verbose_name': 'Storico Servizio',
                'verbose_name_plural': 'Storico Servizi',
                'ordering': ['-data_inizio'],
            },
        ),
        migrations.CreateModel(
            name='StoricoAttivitaUO',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120)),
                ('descrizione', models.TextField(blank=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('atto_riferimento', models.CharField(blank=True, max_length=255)),
                ('data_inizio', models.DateTimeField()),
                ('data_fine', models.DateTimeField(blank=True, null=True)),
                ('attivita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versioni', to='struttura_ente.attivitauo')),
                ('servizio_storico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='attivita_versioni', to='struttura_ente.storicoservizio')),
            ],
            options={
                'verbose_name': 'Storico Attivita U.O.',
                'verbose_name_plural': 'Storico Attivita U.O.',
                'ordering': ['-data_inizio'],
            },
        ),
        migrations.AddConstraint(
            model_name='servizio',
            constraint=models.UniqueConstraint(fields=('settore', 'codice'), name='servizio_codice_unico_per_settore'),
        ),
        migrations.AddIndex(
            model_name='storicoservizio',
            index=models.Index(fields=['codice', 'data_fine'], name='struttura_serv_codice_idx'),
        ),
        migrations.AddIndex(
            model_name='storicoservizio',
            index=models.Index(fields=['data_inizio'], name='struttura_serv_in_idx'),
        ),
        migrations.AddIndex(
            model_name='storicoattivitauo',
            index=models.Index(fields=['data_fine'], name='struttura_att_fine_idx'),
        ),
        migrations.AddIndex(
            model_name='storicoattivitauo',
            index=models.Index(fields=['data_inizio'], name='struttura_att_in_idx'),
        ),
    ]