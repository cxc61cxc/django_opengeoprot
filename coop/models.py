from django.db import models
from decimal import Decimal
from datetime import datetime, timedelta
from simple_history.models import HistoricalRecords


# Create your models here.
now=datetime.now()


class IstrConv(models.Model):
    tipo_diritto_choice = [
    ('Superficie', 'Superficie'),
    ('Proprietà', 'Proprietà'),
    ('solo superficie','solo superficie'),
    ]

    valore_choice = [
        ('213.36'), ('Marina di Carrara'),
        ('168.65'), ('Avenza Ovest'),
        ('151.78'), ('Bonascola, Avenza Est'),
        ('139.13'), ('Fossola'),
        ('107.50'), ('Monte'),
    ]


    #   richiama la pratica protocollata ( la richiesta di passo carraio )
    pratica     = models.OneToOneField('protocollo.Pratica', on_delete=models.CASCADE, related_name='convenzioni')
    tipo_diritto = models.CharField(
        max_length=30,
        choices=tipo_diritto_choice,
        default='Superficie',
        )
    notaio          = models.CharField(max_length=150, null=True, blank=True)
    atto            = models.CharField(max_length=200, null=True, blank=True)
    data_atto       = models.DateField(null=True,blank=True)
    data_rival      = models.DateField(default='2024-05-01')
    millesimi       = models.DecimalField(max_digits=20, decimal_places=5, null=True, blank=True)
    durata          = models.IntegerField(null=True,blank=True)
    coeff_temp      = models.DecimalField(max_digits=20, decimal_places=5, null=True, blank=True)
    area            = models.IntegerField(null=True,blank=True)
    edifici         = models.IntegerField(null=True,blank=True)
    ref_millesimi   = models.BooleanField(default=False)
    prop_acquisita  = models.BooleanField(default=False) # da spuntare se ha acquisito in precedenza la proprietà
    alloggi         = models.IntegerField(null=True,blank=True)
    volume          = models.IntegerField(null=True,blank=True)
    conv_lire       = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cong_lire       = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    tot_conv        = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    conv_rival      = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cong_rival      = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    coeff_istat     = models.DecimalField(max_digits=20, decimal_places=5, null=True, blank=True,default='1.672')
    tot_conv_rival  = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    valore_residuo  = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    valore_perizia  = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True) # valore unitario come da del. CC 56/2024
    valore_venale   = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True) # valore perizia x 0.60 x superficie area
    valore_dirsup   = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    crv             = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True) # valore rimozione vincolo complessivo
    crv_uiu         = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True) # valore rimozione vincolo singola UIU
    history = HistoricalRecords()

    # campi calcolati
    # def discounted_price(self):
    #     discount_percentage = 0.2  # Assuming a 20% discount
    #     return self.price - (self.price * discount_percentage)
    def conv_euro(self):
        cambio = 1936.27 # cambio lire per euro
        return (self.conv_lire / Decimal(cambio))
    
    def cong_euro(self):
        cambio = 1936.27 # cambio lire per euro
        return (self.cong_lire / Decimal(cambio))
    
    
    
    class Meta:
        
        verbose_name_plural = "Istruttorie"
        ordering = ['id']

    def __str__(self):
        return self.id
    

# tabella accettazione

class AccettaImporto(models.Model):
    convenzione     = models.OneToOneField('coop.IstrConv', on_delete=models.CASCADE,related_name='accettazioni')
    prot_gen = models.CharField('Prot.Gen.',max_length=20, null=True, blank=True)
    data_accettazione = models.DateField()
    annotazione = models.TextField(null=True, blank=True)
    iuv = models.CharField(max_length=50, null=True, blank=True)
    importo = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True )
    rateo = models.BooleanField(default=False)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "AccettaImporti"
        ordering = ['-data_accettazione']
    
    def __str__(self):
        return str(self.id)

# tabella scadenze rate ( solo se AccettaImporto.rateo = True )

class Scadenze(models.Model):
    convenzione = models.ForeignKey('coop.IstrConv', on_delete=models.CASCADE, related_name='scadenze_rate_convenzione', null=True,blank=True)
    data_scadenza = models.DateField(null=False,blank=False)
    importo_rata = models.DecimalField(max_digits=15, decimal_places=2, null=False,blank=False)
    data_pagamento = models.DateField(default=0,null=True,blank=True)
    importo_pagamento = models.DecimalField(max_digits=15, decimal_places=2,null=True,blank=True)
    iuv = models.CharField(max_length=50, null=True, blank=True)
    pagata = models.BooleanField(default=False)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Scadenze"
        ordering = ['data_scadenza']

    def save(self, *args, **kwargs):
    # Imposta pagata a True se importo_pagamento è uguale ad importo_rata
        if self.importo_pagamento !='':
            self.pagata = (self.importo_pagamento == self.importo_rata)
        else:
            self.pagata = False
        super().save(*args, **kwargs)
    
    def __str__(self):
        return str(self.id)