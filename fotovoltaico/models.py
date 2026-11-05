from django.db import models
from django.utils.timezone import now
from django.urls import reverse
from datetime import date
from protocollo.models import *

from simple_history.models import HistoricalRecords


User=get_user_model()

# Create your models here.

class ImpFot(models.Model):
    
    #   richiama la pratica protocollata ( la richiesta di Provvedimento  )
    pratica = models.ForeignKey('protocollo.Pratica', on_delete=models.CASCADE, related_name='pratiche_fotovoltaico')
    user = models.ForeignKey(User,on_delete=models.SET_NULL, blank=True, null=True)

    pod = models.CharField(max_length=50, null=True, blank=True)
    code_e = models.CharField(max_length=50, null=True, blank=True)

    pn = models.PositiveSmallIntegerField(null=True,blank=True) # potenza nominale
    pa = models.PositiveSmallIntegerField(null=True,blank=True) # potenza accumulata
    pi = models.PositiveSmallIntegerField(null=True,blank=True) # potenza immessa

    mod1 = models.BooleanField(default=False)
    mod2 = models.BooleanField(default=False)

    allp = models.BooleanField(default=False)
    
    prot_pe = models.CharField(max_length=50, null=True, blank=True)
    data_prot_pe = models.DateField(null=True, blank=True)



    annotazione = models.TextField(null=True, blank=True)
    
   
    
    data_crea=models.DateTimeField(auto_now_add=True, blank=True, null=True)
    data_mod= models.DateTimeField(auto_now=True, blank=True,null=True)  
    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['pod'],
                name='numero_pod',
                condition=models.Q(pod__isnull=False),
            ),
        ]
        verbose_name = "Impianto Fotovoltaico"
        verbose_name_plural = "Impianti Fotovoltaici"
        ordering = ['pod']

    def __str__(self):
        return str(self.pod)

    def get_absolute_url(self):       # ---> new function
        return reverse('impfot_detail_url', args=[str(self.id)])
    
    def save(self, *args, **kwargs):
        # Convert empty string pod to None to avoid unique constraint violations
        if self.pod is not None and self.pod.strip() == '':
            self.pod = None

        # Se mod1 o mod2 sono True, imposta allp, prot_pe e data_prot_pe a False o None
        if self.mod1 or self.mod2:
            self.allp = False
            self.prot_pe = ''
            self.data_prot_pe = None

        # Se allp è True, imposta mod1 e mod2 a False
        if self.allp:
            self.mod1 = False
            self.mod2 = False

        super().save(*args, **kwargs)