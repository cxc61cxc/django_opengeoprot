from django.db import models

# Create your models here.




class Civici(models.Model):

    street=models.CharField(max_length=500)
   

    class Meta:
        verbose_name_plural = "Civici"

    def __str__(self):
        return str(self.street)
    
# class OsmPoint(models.Model):
    # via = models.CharField(max_length=500)
    # number = models.CharField(max_length=30)
    # x = models.DecimalField(max_digits=12, decimal_places=6)
    # y = models.DecimalField(max_digits=12, decimal_places=6)
    
    # class Meta:
    #     verbose_name_plural = "punti_civici"

    # def __str__(self):
    #     return str(self.via)+', '+str(self.number)