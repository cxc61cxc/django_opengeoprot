import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('protocollo', '0033_nota_osm_allegato'),
        ('struttura_ente', '0005_tipocommissione'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipocommissione',
            name='tipo_pratica',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='commissioni',
                to='protocollo.tipopratica',
                help_text='Se valorizzato, i consiglieri di questa commissione vedono SOLO le pratiche di questo tipo (altrimenti il filtro non si applica).',
            ),
        ),
    ]