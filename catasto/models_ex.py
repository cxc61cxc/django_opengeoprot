from django.contrib.gis.db import models
from django.urls import reverse
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon


class Particelle(models.Model):
    foglio = models.CharField(max_length=5, blank=True, null=True)
    mappale = models.CharField(max_length=5, blank=True, null=True)
    mpoly = models.MultiPolygonField(srid=4326, null=True, blank=True)

    def __str__(self):
        return str(self.foglio)+'-'+(self.mappale)
    def get_absolute_url(self):
        return reverse("catastali_Particelle_detail", args=(self.pk,))
