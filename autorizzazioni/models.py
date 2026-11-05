from django.db import models

class RegistroAutorizzazioni(models.Model):
    periodo = models.CharField(max_length=50)
    titolo = models.CharField(max_length=200)
    filename = models.CharField(max_length=500)

    class Meta:
        ordering = ['periodo']

    def __str__(self):
        return f"{self.periodo} - {self.titolo}"
