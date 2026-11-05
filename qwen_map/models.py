from django.contrib.gis.db import models


class Municipality(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        verbose_name = "Municipality"
        verbose_name_plural = "Municipalities"

    def __str__(self):
        return self.name