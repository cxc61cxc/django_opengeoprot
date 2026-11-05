from django.db import models
from django.utils.timezone import now
from django.urls import reverse
from datetime import date
from protocollo.models import *

from simple_history.models import HistoricalRecords

# Create your models here.

class Matricola(models.Model):
    num_impianto = models.OneToOneField(
        'ascensori.impianto',
        on_delete=models.CASCADE,
        related_name='impianti_ascensore',
        null=True,
        blank=False
    )

    numero = models.PositiveIntegerField(null=True, blank=True)
    matricola_date = models.DateField(null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    matricola_comunicata = models.CharField(max_length=70, blank=True, null=True)

    data_crea = models.DateTimeField(auto_now_add=True)

    matricola_assegnata = models.CharField(max_length=220, null=True, blank=True)

    history = HistoricalRecords()

    def _generate_matricola(self):
        """
        Crea la matricola da usare:
        - se matricola_comunicata è valorizzata, la usa
        - altrimenti genera da numero + anno matricola_date
        """
        if self.matricola_comunicata:
            return self.matricola_comunicata
        if self.numero and self.matricola_date:
            return f"MS-{self.numero}-{self.matricola_date.year}"
        return None

    @property
    def matricola(self):
        """
        Ritorna il valore definitivo della matricola:
        matricola_assegnata se presente, altrimenti generata.
        """
        return self.matricola_assegnata or self._generate_matricola()

    def save(self, *args, **kwargs):
        # Aggiorna matricola_assegnata sempre prima di salvare
        generated = self._generate_matricola()
        if generated:
            self.matricola_assegnata = generated
        else:
            self.matricola_assegnata = None  # opzionale, per sicurezza

        super().save(*args, **kwargs)

    class Meta:
       
        verbose_name = "Matricola"
        verbose_name_plural = "Matricole"
        ordering = ['matricola_date', 'numero']



    

class Impianto(models.Model):
        pratica = models.OneToOneField('protocollo.Pratica', on_delete=models.CASCADE, null=True, blank=True, related_name='pratiche_impianto')
        num_impianto = models.CharField(max_length=220, null=True, blank=True)
        velocita = models.DecimalField(max_digits=5, decimal_places=2,null=True, blank=True ) # velocità impianto
        portata = models.DecimalField(max_digits=6, decimal_places=2,null=True, blank=True) # portata in Kg
        corsa = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True) # estensione complessiva della tratta
        fermate = models.IntegerField(null=True, blank=True)
        azionamento = models.CharField(max_length=220, null=True, blank=True)
        data_crea = models.DateTimeField(auto_now_add=True, null=True, blank=True)
        history = HistoricalRecords()
        note = models.TextField(null=True, blank=True)

        class Meta:
            # constraints = [
            #     models.UniqueConstraint(fields=[ 'num_impianto'], name='numero_impianto'),
            # ]
            verbose_name = "Impianto"
            verbose_name_plural = "Impianti"
            ordering = ['data_crea','num_impianto']

        def __str__(self):
            return str(self.data_crea.year)+'-'+str(self.num_impianto)