from django.db import models
from django.urls import reverse
from django.utils.timezone import now
import datetime

import os
from simple_history.models import HistoricalRecords

from django.db.models.functions import Coalesce

# Create your models here.

class Passocarraio(models.Model):
    # dati generici del passo carraio

    access_choice = [
    ('pc', 'area privata ad uso parcheggio condominiale'),
    ('app', 'area privata ad uso parcheggio'),
    ('apg', 'area privata ad uso garage'),
    ('bpg', 'box privato ad uso garage'),
    ('Altro', 'altro'),
    ]
    tipo_choice = [
    ('nuova_istanza', 'richiesta di concessione passo carraio'),
    ('revoca', 'richiesta di REVOCA concessione passo carraio'),
    ('voltura', 'richiesta di VOLTURA concessione passo carraio'),
    ('modifica', 'richiesta di MODIFICA concessione passo carraio'),
    ]
#   richiama la pratica protocollata ( la richiesta di passo carraio )
    pratica = models.OneToOneField('protocollo.Pratica', on_delete=models.SET_NULL, null=True)

#   numerazione del passo carraio
    pc_number = models.PositiveBigIntegerField(blank=True,null=True)
    pc_date = models.DateField(blank=True,null=True)

#   utilizzo del passo carraio
#   impone iter diversi e specifici
#   FARE QUERY
    uso=models.CharField(
        max_length=100,
        choices=access_choice,
        default='pc',
        )
    tipo=models.CharField(
        max_length=100,
        choices=tipo_choice,
        default='nuova_istanza',
        )
#   riferimento alle norme vigenti alla data???.... da visualizzare ed impostare manualemnte solo se il passo carraio
#   è per successione


#   data di creazione del record

    data_crea = models.DateTimeField(auto_now_add=True)
    largh=models.DecimalField("larghezza", max_digits=5,decimal_places=2, blank=True, null=True)
    prof=models.DecimalField("profondita'",max_digits=5,decimal_places=2, blank=True, null=True)
    area=models.DecimalField("area",max_digits=5,decimal_places=2, blank=True, null=True)
    description=models.CharField(max_length=300, null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        # constraints = [
        #     models.UniqueConstraint(fields=[ 'pc_number', 'pc_date'], name='numero_pc'),
        # ]
        verbose_name_plural = "Passi carrai"
        ordering = ['id']

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):       # ---> new function
        return reverse('passo_carraio_detail_url', args=[str(self.id)])

