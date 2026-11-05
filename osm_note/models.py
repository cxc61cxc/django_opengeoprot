from django.contrib.gis.db import models


class OsmStrada(models.Model):
    osm_id = models.BigIntegerField(unique=True, verbose_name="OSM Way ID")
    nome = models.CharField(max_length=255, blank=True, verbose_name="Nome strada")
    highway = models.CharField(max_length=50, blank=True, verbose_name="Tipo highway")
    operator = models.CharField(max_length=255, blank=True, verbose_name="Operator")
    geom = models.LineStringField(srid=4326, verbose_name="Geometria")
    data_importazione = models.DateTimeField(auto_now=True, verbose_name="Data importazione")

    class Meta:
        ordering = ['nome']
        verbose_name = 'Strada OSM'
        verbose_name_plural = 'Strade OSM'

    def __str__(self):
        return f"#{self.osm_id} {self.nome}"


class StradaProcessata(models.Model):
    osm_id = models.BigIntegerField(unique=True, verbose_name="OSM Way ID")
    nome = models.CharField(max_length=255, blank=True, verbose_name="Nome strada")
    utente = models.CharField(max_length=150, blank=True, verbose_name="Utente")
    data_elaborazione = models.DateTimeField(auto_now_add=True, verbose_name="Data elaborazione")
    note = models.TextField(blank=True, verbose_name="Note")

    class Meta:
        ordering = ['-data_elaborazione']
        verbose_name = 'Strada processata'
        verbose_name_plural = 'Strade processate'

    def __str__(self):
        return f"#{self.osm_id} {self.nome} ({self.data_elaborazione:%d/%m/%Y %H:%M})"
