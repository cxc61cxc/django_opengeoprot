from django.db import models
from django.urls import reverse

from django.contrib.auth import get_user_model
from simple_history.models import HistoricalRecords

from protocollo.models import Pratica

User = get_user_model()


class IstruttoriaMixin:
    """Comportamento comune a istruttoria, commissione e consiglio.

    Ogni modello dichiara il proprio campo data con `data_field`.
    """

    data_field = None

    def get_absolute_url(self):
        return reverse(self.url_name, kwargs={'pratica_id': self.pratica_id})

    @property
    def data_val(self):
        return getattr(self, self.data_field, None)

    @property
    def compilata(self):
        return bool((self.testo or '').strip() or self.data_val)

    @property
    def vuota(self):
        return not (self.testo or '').strip() and not self.data_val and not self.user_id

    def svuota(self):
        """Azzera i contenuti mantenendo il record e la tracciatura."""
        self.testo = ''
        setattr(self, self.data_field, None)
        self.user = None
        self.save(update_fields=['testo', self.data_field, 'user', 'data_mod'])


class Istruttoria(IstruttoriaMixin, models.Model):
    url_name = 'istruttoria_poc:istruttoria_detail'
    data_field = 'data_istr_poc'

    pratica = models.OneToOneField(
        Pratica,
        on_delete=models.CASCADE,
        related_name='istruttoria_poc',
        verbose_name='Pratica',
    )
    testo = models.TextField('Testo istruttoria', blank=True, null=True)
    data_istr_poc = models.DateField(
        'Data istruttoria',
        blank=True,
        null=True,
        default=None,
        help_text='Lasciare vuoto per non valorizzare la data.',
    )
    user = models.ForeignKey(
        User,
        verbose_name='Utente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='istruttorie_poc',
    )
    data_crea = models.DateTimeField('Data creazione', auto_now_add=True)
    data_mod = models.DateTimeField('Ultima modifica', auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Istruttoria'
        verbose_name_plural = 'Istruttorie POC 2022'
        ordering = ['-data_crea']

    def __str__(self):
        return f"Istruttoria pratica {self.pratica_id}"


class IstrComm(IstruttoriaMixin, models.Model):
    url_name = 'istruttoria_poc:istrcomm_detail'
    data_field = 'data_commissione'

    pratica = models.OneToOneField(
        Pratica,
        on_delete=models.CASCADE,
        related_name='istrcomm_poc',
        verbose_name='Pratica',
    )
    testo = models.TextField('Testo commissione', blank=True, null=True)
    data_commissione = models.DateField(
        'Data commissione',
        blank=True,
        null=True,
        default=None,
        help_text='Lasciare vuoto per non valorizzare la data.',
    )
    user = models.ForeignKey(
        User,
        verbose_name='Utente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='istrcomm_poc',
    )
    data_crea = models.DateTimeField('Data creazione', auto_now_add=True)
    data_mod = models.DateTimeField('Ultima modifica', auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Comunicazione di commissione'
        verbose_name_plural = 'Commissioni POC 2022'
        ordering = ['-data_crea']

    def __str__(self):
        return f"Comunicazione pratica {self.pratica_id}"


class IstrCons(IstruttoriaMixin, models.Model):
    url_name = 'istruttoria_poc:istrcons_detail'
    data_field = 'data_consiglio'

    pratica = models.OneToOneField(
        Pratica,
        on_delete=models.CASCADE,
        related_name='istrcons_poc',
        verbose_name='Pratica',
    )
    testo = models.TextField('Testo consiglio', blank=True, null=True)
    data_consiglio = models.DateField(
        'Data consiglio',
        blank=True,
        null=True,
        default=None,
        help_text='Lasciare vuoto per non valorizzare la data.',
    )
    user = models.ForeignKey(
        User,
        verbose_name='Utente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='istrcons_poc',
    )
    data_crea = models.DateTimeField('Data creazione', auto_now_add=True)
    data_mod = models.DateTimeField('Ultima modifica', auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Consiglio'
        verbose_name_plural = 'Consigli POC 2022'
        ordering = ['-data_crea']

    def __str__(self):
        return f"Consiglio pratica {self.pratica_id}"
