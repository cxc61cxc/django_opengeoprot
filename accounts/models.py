from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


settore_choice = [
    ('staff A', 'Staff Segretario generale'),
    ('staff B', 'AVVOCATURA COMUNALE'),
    ('settore 1', 'AFFARI E SERVIZI GENERALI'),
    ('settore 2', 'RISORSE UMANE, FINANZIARIE E SOCIETARIE'),
    ('settore 3', 'ATTIVITÀ PRODUTTIVE E SERVIZI EDUCATIVI / SCOLASTICI'),
    ('settore 4', 'CULTURA E TURISMO'),
    ('settore 5', 'LAVORI PUBBLICI E ATTUAZIONE PNRR'),
    ('settore 6', 'GOVERNO DEL TERRITORIO'),
    ('settore 7', 'SERVIZI AMBIENTALI / MARMO'),
    ('settore 8', 'SUPPORTO ORGANI ISTITUZIONALI / SERVIZI SOCIALI E POLITICHE ABITATIVE'),
    ('settore 9', 'POLIZIA LOCALE, SICUREZZA E MOBILITÀ'),
    # ('settore 10', 'Settore 10 Polizia locale, sicurezza, mobilità'),
    ]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    settore = models.ForeignKey(
        'struttura_ente.StoricoSettore',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='profiles',
        help_text='FK allo snapshot storico del Settore (immutabile).',
    )
    u_o = models.ForeignKey(
        'struttura_ente.StoricoAttivitaUO',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='profiles',
        help_text='FK allo snapshot storico della Attivita U.O. (immutabile).',
    )
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Commissione(models.Model):
    """Iscrizione di un utente (consigliere) a una commissione consigliare.

    Una Commissione lega un User a un TipoCommissione (definito in
    struttura_ente) con una data di inizio/fine: l'utente acquisisce i
    permessi del gruppo Django associato al TipoCommissione per il periodo
    indicato.

    Il campo `settore` e' uno snapshot StoricoSettore al momento dell'iscrizione
    (il primo settore del TipoCommissione). Serve per filtrare le pratiche
    per settore: un consigliere vede solo le pratiche del settore di ciascuna
    commissione a cui e' iscritto.
    """
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='commissioni',
    )
    user_name = models.CharField(max_length=255, blank=True, null=True,
                                  help_text='Snapshot del nome utente al momento dell\'iscrizione.')
    tipo_commissione = models.ForeignKey(
        'struttura_ente.TipoCommissione',
        on_delete=models.PROTECT, related_name='iscritti',
    )
    settore = models.ForeignKey(
        'struttura_ente.StoricoSettore',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='commissioni_iscritti',
        help_text='Snapshot del settore principale della commissione al '
                  'momento dell\'iscrizione (immutabile).',
    )
    data_inizio = models.DateField(auto_now_add=True)
    data_fine = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Commissione'
        verbose_name_plural = 'Commissioni'
        ordering = ['-data_inizio', 'user__username']

    def __str__(self):
        name = self.user_name or (self.user.username if self.user else "sconosciuto")
        return f"{name} → {self.tipo_commissione.codice}"

    def save(self, *args, **kwargs):
        if self.user and not self.user_name:
            self.user_name = str(self.user)
        super().save(*args, **kwargs)

    @property
    def user_display(self):
        if self.user_id:
            return str(self.user) if self.user else self.user_name or "sconosciuto"
        return self.user_name or "sconosciuto"

    @property
    def attiva(self):
        from django.utils import timezone
        if self.data_fine is not None and self.data_fine < timezone.localdate():
            return False
        return True