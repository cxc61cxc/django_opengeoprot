from django.db import models
from django.utils.timezone import now
from django.urls import reverse
from datetime import date
from protocollo.models import *

from simple_history.models import HistoricalRecords
User=get_user_model()

# Create your models here.
tipo_richiedente_idonall_choice = [
    ('Proprietario', 'Proprietario'),
    ('Conduttore', 'Conduttore'),
    ('Ospite', 'Ospite'),
    ]

tipo_richiesta_choice = [
    ('Attestazione', 'Attestazione'),
    ('Cointestazione', 'Cointestazione'),
    ('Duplicato', 'Duplicato'),
    ('Rinnovo', 'Rinnovo'),
    ]

tipo_uso_choice = [
    ('Carta di soggiorno','carta di soggiorno'),
    ('Coesione','coesione'),
    ('Conversione','conversione'),
    ('Ricongiungimento','ricongiungimento'),
    ('Seguito','seguito'),
]

class Istruttoria(models.Model):
    pratica = models.OneToOneField('protocollo.Pratica', on_delete=models.CASCADE, related_name='pratica_idonall')
    user = models.ForeignKey(User,on_delete=models.SET_NULL, blank=True, null=True)
    data_crea=models.DateTimeField(auto_now_add=True, blank=True, null=True)
    data_mod= models.DateTimeField(auto_now=True, blank=True,null=True)    
    history = HistoricalRecords()
    # prima parte del modulo di richiesta
    tipo_richiedente_idonall = models.CharField(max_length=180, choices=tipo_richiedente_idonall_choice, null=False)
    tipo_richiesta = models.CharField(max_length=180, choices=tipo_richiesta_choice, null=False)
    # tipo_uso = models.CharField(max_length=180, choices=tipo_uso_choice, null=False)

    # Allegati (verifica con spunta) ... NB gli allegati saranno presenti in Documenti
    ante1975 = models.BooleanField(default=False,null=True)
    catasto = models.BooleanField(default=False,null=True) # visura e planimetria ???
    # autocert_prop = models.BooleanField(default=False) # autocertificazione proprietario
    doc_prop = models.BooleanField(default=False) # documento proprietario
    # abitabilita = models.BooleanField(default=False) # cetificato di abitabilita'
    # rel_tecnica = models.BooleanField(default=False) # relazione a firma di tecnico abiilitato
    conf_imp = models.BooleanField(default=False) # conformita' degli impianti
    caldaia = models.BooleanField(default=False) # revisione caldaia

    mq = models.FloatField(null=True, blank=True)
    vani = models.FloatField(null=True, blank=True)
    nota_relazione =   models.CharField(max_length=500, null=True, blank=True)
    nota_abitabilita = models.CharField(max_length=500, null=True, blank=True)
    nota_prop = models.CharField(max_length=500, null=True, blank=True)
    num_adulti = models.IntegerField(null=True,blank=True)
    num_minori = models.IntegerField(null=True,blank=True)




    class Meta:
        
        # verbose_name = "Idoneita' alloggiativa"
        verbose_name_plural = "Idoneita' alloggiative   "
        ordering = ['id']

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):       # ---> new function
        return reverse('idonall_detail_url', args=[str(self.id)])
    
    # # se ante1975 = yes/no
    # def save(self, *args, **kwargs):
    #     if self.ante1975:
    #         self.mq = 0
    #     else:
    #         self.vani = 0
        
        

class Idonall(models.Model):
    
    #   richiama la pratica protocollata ( la richiesta di Provvedimento  )
    # pratica = models.OneToOneField('protocollo.Pratica', on_delete=models.CASCADE, related_name='pratiche_idonall')
    istruttoria = models.OneToOneField(Istruttoria,on_delete=models.CASCADE,related_name='certificato_istruttoria')
    idonall_number = models.PositiveIntegerField()
    idonall_date = models.DateField(null=True, blank=True)

    descrizione = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User,on_delete=models.SET_NULL, blank=True, null=True)

   
    
    data_crea = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=[ 'idonall_number', 'idonall_date'], name='numero_idonall'),
        ]
        verbose_name = "Idoneita' alloggiativa"
        verbose_name_plural = "Idoneita' alloggiative   "
        ordering = ['idonall_date','idonall_number']

    def __str__(self):
        return str(self.idonall_date)+'-'+str(self.idonall_number)

    def get_absolute_url(self):       # ---> new function
        return reverse('idon_detail_url', args=[str(self.id)])
