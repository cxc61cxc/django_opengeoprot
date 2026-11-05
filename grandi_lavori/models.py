from django.db import models

class RegistroGrandiLavori(models.Model):
    periodo = models.CharField(max_length=50)
    lettera = models.CharField(max_length=20)
    titolo = models.CharField(max_length=200)
    filename = models.CharField(max_length=500)

    class Meta:
        ordering = ['periodo', 'lettera']
        unique_together = ('periodo', 'lettera')

    def __str__(self):
        return f"{self.periodo} - {self.titolo}"
