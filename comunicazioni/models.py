from django.db import models
from django.urls import reverse

# Create your models here.
from protocollo.models import TipoPratica
class Modello(models.Model):

    name = models.CharField(max_length=280, blank=False, null=False, unique=True)
    description = models.TextField('Descrizione', blank=True,null=True)

    tipo_pratica = models.ForeignKey(TipoPratica, on_delete=models.CASCADE, related_name='modelli_pratica')
    
    class Meta:
        verbose_name_plural="Modelli"
        ordering = ['id']
	    
    def __str__(self):
        return self.name
    
    def get_fields(self):
        return [(field.verbose_name, field.value_from_object(self))
                
                if field.verbose_name != 'tipo_pratica' 
                
                else 
                    (field.verbose_name, 
                    TipoPratica.objects.get(pk=field.value_from_object(self)).name)
                
                for field in self.__class__._meta.fields[1:]
            ]
    

    def get_absolute_url(self):       # ---> new function
        return reverse('modello_detail', args=[str(self.id)])

	