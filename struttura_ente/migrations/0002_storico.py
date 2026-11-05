import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('struttura_ente', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='settore',
            name='attivo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='settore',
            name='data_creazione',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='settore',
            name='data_modifica',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='unitaorganizzativa',
            name='attivo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='unitaorganizzativa',
            name='data_creazione',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='unitaorganizzativa',
            name='data_modifica',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='StoricoSettore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codice', models.CharField(max_length=20)),
                ('nome', models.CharField(max_length=200)),
                ('descrizione', models.TextField(blank=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('atto_riferimento', models.CharField(blank=True, max_length=255)),
                ('data_inizio', models.DateTimeField()),
                ('data_fine', models.DateTimeField(blank=True, null=True)),
                ('settore', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versioni', to='struttura_ente.settore')),
            ],
            options={
                'verbose_name': 'Storico Settore',
                'verbose_name_plural': 'Storico Settori',
                'ordering': ['-data_inizio'],
            },
        ),
        migrations.CreateModel(
            name='StoricoUnitaOrganizzativa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120)),
                ('descrizione', models.TextField(blank=True)),
                ('ordine', models.PositiveIntegerField(default=0)),
                ('atto_riferimento', models.CharField(blank=True, max_length=255)),
                ('data_inizio', models.DateTimeField()),
                ('data_fine', models.DateTimeField(blank=True, null=True)),
                ('unita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versioni', to='struttura_ente.unitaorganizzativa')),
                ('settore_storico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='unita_versioni', to='struttura_ente.storicosettore')),
            ],
            options={
                'verbose_name': 'Storico U.O.',
                'verbose_name_plural': 'Storico U.O.',
                'ordering': ['-data_inizio'],
            },
        ),
        migrations.AddIndex(
            model_name='storicosettore',
            index=models.Index(fields=['codice', 'data_fine'], name='struttura_e_codice__idx'),
        ),
        migrations.AddIndex(
            model_name='storicosettore',
            index=models.Index(fields=['data_inizio'], name='struttura_e_data_in_idx'),
        ),
    ]