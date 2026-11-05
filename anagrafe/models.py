from django.db import models
from django.urls import reverse

# Create your models here.

class Residenti(models.Model):
    id_famiglia = models.IntegerField()
    id_individuo = models.IntegerField(unique=True)
    civico = models.CharField(max_length=10, null=True, blank=True)
    lettera = models.CharField(max_length=10,null=True, blank=True)
    corte = models.CharField(max_length=10,null=True, blank=True)
    scala = models.CharField(max_length=10,null=True, blank=True)
    interno = models.CharField(max_length=10,null=True, blank=True)
    piano = models.CharField(max_length=20,null=True, blank=True)
    edificio = models.CharField(max_length=10,null=True, blank=True)
    dug = models.CharField(max_length=30,null=True, blank=True)
    descrizione = models.CharField(max_length=150,null=True, blank=True)
    code_istat = models.IntegerField(null=True, blank=True)
    code_sicra = models.IntegerField(null=True, blank=True)
    codice_fiscale = models.CharField(max_length=16,null=True, blank=True)
    id_relazione = models.IntegerField(null=True, blank=True)
    cognome = models.CharField(max_length=80)
    nome = models.CharField(max_length=80)
    data_nascita = models.DateField()
    comune_nascita = models.CharField(max_length=180)
    comune_residenza = models.CharField(max_length=180,null=True)
    addr = models.CharField(max_length=80)
    # email = models.EmailField(unique=True, null=True, blank=True)
    # email_pec = models.EmailField(null=True, blank=True)
    # cellulare = models.CharField(max_length=100, null=True)
    # telefono = models.CharField(max_length=100, null=True)
    # fax = models.CharField(max_length=100, null=True)
    

    class Meta:
        verbose_name_plural = "residenti"
        ordering = ['cognome','nome']

    def __str__(self):
        return  self.cognome +" "+ self.nome


    def get_absolute_url(self):       # ---> new function
        return reverse('soggetto_anagrafe_detail_url', kwargs={'id': self.id})
    