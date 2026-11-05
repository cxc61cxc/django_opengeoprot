from django.db import migrations


def relink_uo_to_active_servizio(apps, schema_editor):
    StoricoServizio = apps.get_model('struttura_ente', 'StoricoServizio')
    StoricoAttivitaUO = apps.get_model('struttura_ente', 'StoricoAttivitaUO')
    db_alias = schema_editor.connection.alias

    archived_to_active = {}
    for sv in StoricoServizio.objects.using(db_alias).filter(data_fine__isnull=False):
        active = StoricoServizio.objects.using(db_alias).filter(
            servizio=sv.servizio, data_fine__isnull=True
        ).first()
        if active:
            archived_to_active[sv.id] = active.id

    for uo in StoricoAttivitaUO.objects.using(db_alias).filter(
        servizio_storico__data_fine__isnull=False
    ):
        if uo.servizio_storico_id in archived_to_active:
            uo.servizio_storico_id = archived_to_active[uo.servizio_storico_id]
            uo.save(update_fields=['servizio_storico'])


class Migration(migrations.Migration):

    dependencies = [
        ('struttura_ente', '0011_remove_storicounitaorganizzativa_struttura_e_data_fi_21a0a0_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(relink_uo_to_active_servizio, migrations.RunPython.noop),
    ]
