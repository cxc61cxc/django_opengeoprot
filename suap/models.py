from django.db import models
from django.utils.timezone import now
from django.urls import reverse
from datetime import date
from protocollo.models import *

from simple_history.models import HistoricalRecords

# Create your models here.

class Pau(models.Model):
    
    #   richiama la pratica protocollata ( la richiesta di Provvedimento  )
    pratica = models.ForeignKey('protocollo.Pratica', on_delete=models.CASCADE, related_name='pratiche_pau')

    pau_number = models.PositiveIntegerField()
    pau_date = models.DateField()
    description = models.TextField(null=True, blank=True)
    
    importo_1 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    importo_2 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    importo_3 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    importo_4 = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    data_crea = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=[ 'pau_number', 'pau_date'], name='numero_pau'),
        ]
        verbose_name = "Provvedimento Unico Autorizzativo"
        verbose_name_plural = "Provvedimenti Autorizzativi Unici"
        ordering = ['pau_date','pau_number']

    def __str__(self):
        return str(self.pau_date)+'-'+str(self.pau_number)

    def get_absolute_url(self):       # ---> new function
        return reverse('pau_detail_url', args=[str(self.id)])