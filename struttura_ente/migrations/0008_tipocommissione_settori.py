from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('struttura_ente', '0007_seed_commissione2'),
    ]

    operations = [
        migrations.AddField(
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