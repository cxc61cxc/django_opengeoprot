from django.db import models


from simple_history.models import HistoricalRecords
from django.utils.timezone import now
from django.urls import reverse
from datetime import date
from protocollo.models import *
from django.contrib.auth import get_user_model

User=get_user_model()
# Create your models here.



class Commissione(models.Model):

    categ_choice = [
    ('Ordinaria', 'Ordinaria'),
    ('Semplificata', 'Semplificata'),
    ]
    parere_choice = [
    ('Favorevole', 'Favorevole'),
    ('Contrario', 'Contrario'),
    ('Favorevole a condizione','Favorevole a condizione'),
    ('Richiesta integrazioni','Richiesta integrazioni')
    ]
#   richiama la pratica protocollata ( la richiesta di CDU )
    pratica = models.ForeignKey('protocollo.Pratica', on_delete=models.CASCADE, null=True)

#   numerazione del cdu
    commissione_number = models.PositiveBigIntegerField()
    commissione_date = models.DateField()
    parere = models.TextField('Parere', null=True)
    parere_sintetico = models.CharField(
        max_length=30, 
        null=True, 
        blank=True,
        choices=parere_choice,)
    # parere_sintetico = models.CharField(
    #     max_length=30,
    #     choices=categ_choice,
    #     null=True,
    #     )
#   utilizzo del cdu
#   impone iter diversi e specifici
#   FARE QUERY
    tipo_paesaggio = models.CharField(
        max_length=30,
        choices=categ_choice,
        default='Ordinaria',
        )
#   riferimento alle norme vigenti alla data???.... da visualizzare ed impostare manualemnte solo se il cdu
#   è per successione
    user = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True)
    history = HistoricalRecords()
    # data_modifica = models.DateField(default=timezone.now(), null=True)
    data_modifica = models.DateField(  blank=True, null=True)

#   data di creazione del record

    data_crea = models.DateTimeField(auto_now_add=True)

    class Meta:
        # constraints = [
        #     models.UniqueConstraint(fields=[ 'commissione_number', 'commissione_date'], name='numero_commissione'),
        # ]
        verbose_name_plural = "Commissioni"
        ordering = ['commissione_date','commissione_number']

    def __str__(self):
        return str(self.commissione_date.year)+'-'+str(self.commissione_number)

    def get_absolute_url(self):       # ---> new function
        return reverse('commissione_detail_url', args=[str(self.id)])