import django.db.models.deletion
from django.db import migrations, models


def copy_settore_to_fk(apps, schema_editor):
    Settore = apps.get_model('struttura_ente', 'Settore')
    TipoPratica = apps.get_model('protocollo', 'TipoPratica')
    for tp in TipoPratica.objects.all():
        old_val = tp.settore
        if old_val:
            try:
                settore = Settore.objects.get(codice__iexact=old_val)
            except Settore.DoesNotExist:
                settore = None
            if settore is None:
                try:
                    settore = Settore.objects.get(codice__lower=models.functions.Lower(models.Value(old_val)))
                except Settore.DoesNotExist:
                    settore = None
            if settore:
                TipoPratica.objects.filter(id=tp.id).update(settore_new=settore)


def copy_settore_to_fk_historical(apps, schema_editor):
    Settore = apps.get_model('struttura_ente', 'Settore')
    HistoricalTipoPratica = apps.get_model('protocollo', 'HistoricalTipoPratica')
    for tp in HistoricalTipoPratica.objects.all():
        old_val = tp.settore
        if old_val:
            try:
                settore = Settore.objects.get(codice__iexact=old_val)
            except Settore.DoesNotExist:
                settore = None
            if settore:
                HistoricalTipoPratica.objects.filter(id=tp.id).update(settore_new=settore)
            else:
                HistoricalTipoPratica.objects.filter(id=tp.id).update(settore_new=None)


class Migration(migrations.Migration):

    dependencies = [
        ('protocollo', '0034_historicaltipopratica_servizio_and_more'),
        ('struttura_ente', '0011_remove_storicounitaorganizzativa_struttura_e_data_fi_21a0a0_idx_and_more'),
    ]

    operations = [
        # --- Main model: tipopratica ---
        # 1. Add new FK field (settore_new)
        migrations.AddField(
            model_name='tipopratica',
            name='settore_new',
            field=models.ForeignKey(
                blank=True,
                help_text='Settore di appartenenza del tipo pratica.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tipo_pratiche_new',
                to='struttura_ente.settore',
            ),
        ),
        # 2. Copy data from old CharField 'settore' to new FK 'settore_new'
        migrations.RunPython(copy_settore_to_fk, migrations.RunPython.noop),
        # 3. Remove old CharField 'settore'
        migrations.RemoveField(
            model_name='tipopratica',
            name='settore',
        ),
        # 4. Rename settore_new -> settore
        migrations.RenameField(
            model_name='tipopratica',
            old_name='settore_new',
            new_name='settore',
        ),

        # --- Historical model: historicaltipopratica ---
        migrations.AddField(
            model_name='historicaltipopratica',
            name='settore_new',
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text='Settore di appartenenza del tipo pratica.',
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='struttura_ente.settore',
            ),
        ),
        migrations.RunPython(copy_settore_to_fk_historical, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='historicaltipopratica',
            name='settore',
        ),
        migrations.RenameField(
            model_name='historicaltipopratica',
            old_name='settore_new',
            new_name='settore',
        ),
    ]
