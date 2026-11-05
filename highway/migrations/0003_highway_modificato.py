from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('highway', '0002_highway_tipo'),
    ]

    operations = [
        migrations.AddField(
            model_name='highway',
            name='modificato',
            field=models.BooleanField(default=False, verbose_name='Modificato da Comune di Carrara'),
        ),
    ]