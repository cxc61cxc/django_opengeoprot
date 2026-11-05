from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('struttura_ente', '0009_tipocommissione_tipo_pratica_m2m'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tipocommissione',
            name='settori',
            field=models.ManyToManyField(
                blank=True,
                related_name='commissioni',
                to='struttura_ente.settore',
                help_text="Settori di riferimento della commissione (una commissione puo' essere collegata a uno o piu' settori).",
            ),
        ),
    ]