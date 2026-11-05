from django.db import migrations
import django.contrib.gis.db.models.fields
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Highway",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("osm_id", models.BigIntegerField(db_index=True, unique=True, verbose_name="OSM Way ID")),
                ("nome", models.CharField(blank=True, db_index=True, max_length=255, verbose_name="Nome via")),
                ("highway", models.CharField(blank=True, db_index=True, max_length=100, verbose_name="Tipo highway")),
                ("attributi", models.JSONField(blank=True, default=dict, verbose_name="Attributi OSM")),
                ("data_importazione", models.DateTimeField(auto_now=True, verbose_name="Data importazione")),
                ("geom", django.contrib.gis.db.models.fields.LineStringField(srid=4326, verbose_name="Geometria")),
            ],
            options={
                "verbose_name": "Highway OSM",
                "verbose_name_plural": "Highway OSM",
                "ordering": ["nome", "osm_id"],
            },
        ),
    ]
