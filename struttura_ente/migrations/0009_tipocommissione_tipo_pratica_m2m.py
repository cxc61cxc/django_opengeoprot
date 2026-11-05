from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('protocollo', '0033_nota_osm_allegato'),
        ('struttura_ente', '0008_tipocommissione_settori'),
    ]

    operations = [
        # Converte la FK tipo_pratica in M2M.
        # Strategia: drop della FK + add di M2M. I dati (max 1-2 record)
        # vengono ripristinati in una data migration successiva.
        migrations.RemoveField(
            model_name='tipocommissione',
            name='tipo_pratica',
        ),
        migrations.AddField(
            model_name='tipocommissione',
            name='tipo_pratica',
            field=models.ManyToManyField(
                blank=True,
                related_name='commissioni',
                to='protocollo.tipopratica',
                help_text="Se valorizzato, i consiglieri di questa commissione vedono SOLO le pratiche di questi tipi (altrimenti il filtro non si applica).",
            ),
        ),
    ]