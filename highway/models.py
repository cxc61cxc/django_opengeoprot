from django.contrib.gis.db import models

TIPO_OSM_CHOICES = [
    ("way", "Way"),
    ("relation", "Relation"),
    ("node", "Node"),
]
class Highway(models.Model):
    osm_id = models.BigIntegerField(unique=True, db_index=True, verbose_name="OSM Way ID")
    tipo = models.CharField(max_length=20, choices=TIPO_OSM_CHOICES, default="way", verbose_name="Tipo OSM")
    nome = models.CharField(max_length=255, blank=True, db_index=True, verbose_name="Nome via")
    highway = models.CharField(max_length=100, blank=True, db_index=True, verbose_name="Tipo highway")
    attributi = models.JSONField(default=dict, blank=True, verbose_name="Attributi OSM")
    geom = models.LineStringField(srid=4326, verbose_name="Geometria")
    data_importazione = models.DateTimeField(auto_now=True, verbose_name="Data importazione")
    modificato = models.BooleanField(default=False, verbose_name="Modificato da Comune di Carrara")

    class Meta:
        ordering = ["nome", "osm_id"]
        verbose_name = "Highway OSM"
        verbose_name_plural = "Highway OSM"

    def __str__(self):
        return f"#{self.osm_id} {self.nome}".strip()
