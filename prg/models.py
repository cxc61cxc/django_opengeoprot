from django.db import models
from django.utils.timezone import now
from django.urls import reverse
from datetime import date
from protocollo.models import *

from simple_history.models import HistoricalRecords

# Create your models here.



today=date.today()


class Piano(models.Model):
    
    name = models.CharField("Nome piano",max_length=80)
    description = models.TextField("Descrizione")
    tipo_provvedimento = models.CharField(max_length=80, null=True, blank=True)
    atto = models.CharField(max_length=50, null=True, blank=True)
    data_atto= models.DateField( null=True, blank=True)
    data_in= models.DateField(null=True, blank=True)
    data_out= models.DateField(null=True, blank=True)
    ordine = models.FloatField()
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural="Piani"
        ordering = ['name']
		

    def __str__(self):
        return self.name

    def get_absolute_url(self):       # ---> new function
        return reverse('prg:piano_edit_url', args=[(self.id)])
    

class Destinazione(models.Model):

    piano = models.ForeignKey('Piano', on_delete=models.SET_NULL,null=True,  related_name='piani')
    name = models.CharField(max_length=180)
    description = models.TextField()
    norma = models.CharField(max_length=150, null=True)
    data_crea = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Destinazioni"
        ordering = ['piano','name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):       # ---> new function
        return reverse('prg:edit_destinazione_url', args=[str(self.id)])





class Cerdesurb(models.Model):

    categ_choice = [
    ('Atto', 'Atto'),
    ('Successione', 'Successione'),
    ('Altro', 'Altro'),
    ('Informativa', 'Informativa'),
    ]

#   richiama la pratica protocollata ( la richiesta di CDU )
    pratica = models.OneToOneField('protocollo.Pratica', on_delete=models.CASCADE, null=True, related_name='pratiche_cdu')

#   numerazione del cdu
    cdu_number = models.PositiveBigIntegerField()
    cdu_date = models.DateField()

#   utilizzo del cdu
#   impone iter diversi e specifici
#   FARE QUERY
    uso=models.CharField(
        max_length=25,
        choices=categ_choice,
        default='Atto',
        )
#   riferimento alle norme vigenti alla data???.... da visualizzare ed impostare manualemnte solo se il cdu
#   è per successione

    # data_riferimento = models.DateField(default=timezone.now(), null=True)
    data_riferimento = models.DateField(  blank=True, null=True)

#   data di creazione del record

    data_crea = models.DateTimeField(auto_now_add=True)



    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=[ 'cdu_number', 'cdu_date'], name='numero_cdu'),
        ]
        verbose_name_plural = "Cert.Dest.Urb."
        ordering = ['cdu_date','cdu_number']

    def __str__(self):
        return str(self.cdu_number) +'-'+str(self.cdu_date.year)

    def get_absolute_url(self):       # ---> new function
        return reverse('cerdesurb_detail_url', args=[str(self.id)])



class Istruttoria(models.Model):
    cataprat = models.ForeignKey('protocollo.Cataprat',on_delete=models.CASCADE)
    # piano = models.ForeignKey(Piano, on_delete=models.CASCADE, related_name='piani_istruttoria',default='')
    destinazione = models.ForeignKey(Destinazione, on_delete=models.CASCADE, related_name='destinazioni_istruttoria')
    parte = models.BooleanField(default=0, null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=[ 'cataprat', 'destinazione'], name='istruttoria_particella'),
        ]
        verbose_name_plural = "Istruttorie"
        ordering = ['id','cataprat','destinazione']

    def __str__(self):
        return str(self.cataprat)

    def get_absolute_url(self):       # ---> new function
        return reverse('istruttoria_detail_url', args=[str(self.id)])
    


class Marca(models.Model):
    cdu = models.ForeignKey(Cerdesurb, on_delete=models.CASCADE, related_name='marche', null=False)
    iuv = models.CharField(max_length=255, null=True, blank=True)
    data_iuv = models.DateField(null=True, blank=True)
    marca = models.CharField(max_length=255, null=True, blank=True)
    data_marca = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.iuv} - {self.marca}"
