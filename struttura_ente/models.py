from django.db import models
from django.utils import timezone


class Settore(models.Model):
    codice = models.CharField(max_length=20, unique=True, help_text="Es. 'settore 5' o 'staff A'")
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True)
    ordine = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(default=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ordine', 'codice']
        verbose_name = 'Settore'
        verbose_name_plural = 'Settori'

    def __str__(self):
        return f"{self.codice} - {self.nome}"

    @property
    def versione_vigente(self):
        return self.versioni.filter(data_fine__isnull=True).first()

    def storico_apri(self, atto_riferimento='', data_inizio=None):
        vigente = self.versione_vigente
        now = timezone.now()
        if vigente is not None and self._snapshot_matches_vigente(vigente):
            return vigente
        if vigente is not None and vigente.data_fine is None:
            vigente.data_fine = now
            vigente.save(update_fields=['data_fine'])
        return StoricoSettore.objects.create(
            settore=self,
            codice=self.codice,
            nome=self.nome,
            descrizione=self.descrizione,
            ordine=self.ordine,
            atto_riferimento=atto_riferimento or '',
            data_inizio=data_inizio or now,
            data_fine=None,
        )

    def _snapshot_matches_vigente(self, vigente):
        return (
            vigente.codice == self.codice
            and vigente.nome == self.nome
            and vigente.descrizione == self.descrizione
            and vigente.ordine == self.ordine
        )


class Servizio(models.Model):
    """Servizio erogato da un Settore. Ogni Servizio puo' avere piu'
    AttivitaUO (le unita' operative che materialmente svolgono il servizio).
    """
    settore = models.ForeignKey(
        Settore,
        on_delete=models.CASCADE,
        related_name='servizi',
    )
    codice = models.CharField(max_length=20, help_text="Codice breve del servizio")
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True)
    ordine = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(default=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['settore__ordine', 'settore__codice', 'ordine', 'nome']
        verbose_name = 'Servizio'
        verbose_name_plural = 'Servizi'
        constraints = [
            models.UniqueConstraint(fields=['settore', 'codice'], name='servizio_codice_unico_per_settore'),
        ]

    def __str__(self):
        return f"{self.settore.codice} / {self.codice} - {self.nome}"

    @property
    def versione_vigente(self):
        return self.versioni.filter(data_fine__isnull=True).first()

    def storico_apri(self, atto_riferimento='', data_inizio=None):
        vigente = self.versione_vigente
        now = timezone.now()
        if vigente is not None and self._snapshot_matches_vigente(vigente):
            return vigente
        if vigente is not None and vigente.data_fine is None:
            vigente.data_fine = now
            vigente.save(update_fields=['data_fine'])
        return StoricoServizio.objects.create(
            servizio=self,
            settore_storico=self.settore.versione_vigente,
            codice=self.codice,
            nome=self.nome,
            descrizione=self.descrizione,
            ordine=self.ordine,
            atto_riferimento=atto_riferimento or '',
            data_inizio=data_inizio or now,
            data_fine=None,
        )

    def _snapshot_matches_vigente(self, vigente):
        return (
            vigente.settore_storico == self.settore.versione_vigente
            and vigente.codice == self.codice
            and vigente.nome == self.nome
            and vigente.descrizione == self.descrizione
            and vigente.ordine == self.ordine
        )


class AttivitaUO(models.Model):
    """Unita' operativa (figlia di un Servizio)."""
    servizio = models.ForeignKey(
        Servizio,
        on_delete=models.CASCADE,
        related_name='attivita',
    )
    nome = models.CharField(max_length=120)
    descrizione = models.TextField(blank=True)
    ordine = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(default=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['servizio__settore__ordine', 'servizio__ordine', 'ordine', 'nome']
        verbose_name = 'Attivita U.O.'
        verbose_name_plural = 'Attivita U.O.'

    def __str__(self):
        return f"{self.servizio.settore.codice} / {self.servizio.codice} / {self.nome}"

    @property
    def versione_vigente(self):
        return self.versioni.filter(data_fine__isnull=True).first()

    def storico_apri(self, atto_riferimento='', data_inizio=None):
        vigente = self.versione_vigente
        now = timezone.now()
        if vigente is not None and self._snapshot_matches_vigente(vigente):
            return vigente
        if vigente is not None and vigente.data_fine is None:
            vigente.data_fine = now
            vigente.save(update_fields=['data_fine'])
        return StoricoAttivitaUO.objects.create(
            attivita=self,
            servizio_storico=self.servizio.versione_vigente,
            nome=self.nome,
            descrizione=self.descrizione,
            ordine=self.ordine,
            atto_riferimento=atto_riferimento or '',
            data_inizio=data_inizio or now,
            data_fine=None,
        )

    def _snapshot_matches_vigente(self, vigente):
        return (
            vigente.servizio_storico == self.servizio.versione_vigente
            and vigente.nome == self.nome
            and vigente.descrizione == self.descrizione
            and vigente.ordine == self.ordine
        )


class StoricoSettore(models.Model):
    settore = models.ForeignKey(
        Settore,
        on_delete=models.CASCADE,
        related_name='versioni',
    )
    codice = models.CharField(max_length=20)
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True)
    ordine = models.PositiveIntegerField(default=0)
    atto_riferimento = models.CharField(max_length=255, blank=True)
    data_inizio = models.DateTimeField()
    data_fine = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-data_inizio']
        verbose_name = 'Storico Settore'
        verbose_name_plural = 'Storico Settori'
        indexes = [
            models.Index(fields=['codice', 'data_fine']),
            models.Index(fields=['data_inizio']),
        ]

    def __str__(self):
        return f"{self.codice} - {self.nome} ({self.data_inizio:%Y-%m-%d})"

    @property
    def vigente(self):
        return self.data_fine is None


class StoricoServizio(models.Model):
    servizio = models.ForeignKey(
        Servizio,
        on_delete=models.CASCADE,
        related_name='versioni',
    )
    settore_storico = models.ForeignKey(
        StoricoSettore,
        on_delete=models.PROTECT,
        related_name='servizi_versioni',
    )
    codice = models.CharField(max_length=20)
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True)
    ordine = models.PositiveIntegerField(default=0)
    atto_riferimento = models.CharField(max_length=255, blank=True)
    data_inizio = models.DateTimeField()
    data_fine = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-data_inizio']
        verbose_name = 'Storico Servizio'
        verbose_name_plural = 'Storico Servizi'
        indexes = [
            models.Index(fields=['codice', 'data_fine']),
            models.Index(fields=['data_inizio']),
        ]

    def __str__(self):
        return f"{self.settore_storico.codice} / {self.codice} - {self.nome} ({self.data_inizio:%Y-%m-%d})"

    @property
    def vigente(self):
        return self.data_fine is None


class StoricoAttivitaUO(models.Model):
    attivita = models.ForeignKey(
        AttivitaUO,
        on_delete=models.CASCADE,
        related_name='versioni',
    )
    servizio_storico = models.ForeignKey(
        StoricoServizio,
        on_delete=models.PROTECT,
        related_name='attivita_versioni',
    )
    nome = models.CharField(max_length=120)
    descrizione = models.TextField(blank=True)
    ordine = models.PositiveIntegerField(default=0)
    atto_riferimento = models.CharField(max_length=255, blank=True)
    data_inizio = models.DateTimeField()
    data_fine = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-data_inizio']
        verbose_name = 'Storico Attivita U.O.'
        verbose_name_plural = 'Storico Attivita U.O.'
        indexes = [
            models.Index(fields=['data_fine']),
            models.Index(fields=['data_inizio']),
        ]

    def __str__(self):
        return f"{self.servizio_storico.settore_storico.codice} / {self.servizio_storico.codice} / {self.nome} ({self.data_inizio:%Y-%m-%d})"

    @property
    def vigente(self):
        return self.data_fine is None


class TipoCommissione(models.Model):
    """Tipologia di commissione consigliare (es. 'POC 2022', 'Urbanistica', 'Bilancio').

    Ogni TipoCommissione e' mappato a un gruppo Django: alla registrazione di un
    consigliere che seleziona questa commissione, l'utente viene aggiunto al
    gruppo corrispondente (che verra' creato al volo clonando i permessi di
    'user_settore_6' se non esiste).

    Una commissione puo' essere collegata a uno o piu' Settori (per la CRUD di
    amministrazione) e a un insieme di utenti consigli (m2m accounts.User
    tramite accounts.Commissione). Il filtro pratiche rimane governato da
    `tipo_pratica` (se valorizzato, i consiglieri di questa commissione vedono
    SOLO le pratiche di quel tipo).
    """
    codice = models.CharField(
        max_length=50, unique=True,
        help_text="Codice breve (es. 'poc_2022', 'urbanistica')",
    )
    nome = models.CharField(max_length=200, help_text="Nome esteso della commissione")
    descrizione = models.TextField(blank=True)
    gruppo_django = models.CharField(
        max_length=100,
        help_text="Nome del gruppo Django a cui verra' aggiunto il consigliere "
                  "(verra' creato al volo se non esiste).",
    )
    settori = models.ManyToManyField(
        Settore,
        blank=True,
        related_name='commissioni',
        help_text='Settori di riferimento della commissione (una commissione '
                  'puo' ' essere collegata a uno o piu' ' settori).',
    )
    tipo_pratica = models.ManyToManyField(
        'protocollo.TipoPratica',
        blank=True,
        related_name='commissioni',
        help_text='Se valorizzato, i consiglieri di questa commissione vedono '
                  'SOLO le pratiche di questi tipi (altrimenti il filtro non '
                  'si applica).',
    )
    ordine = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(default=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ordine', 'nome']
        verbose_name = 'Tipo Commissione'
        verbose_name_plural = 'Tipi Commissione'

    def __str__(self):
        return f"{self.codice} - {self.nome}"

    def clean(self):
        super().clean()
        if not self.pk and not self.settori.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError(
                {'settori': "Una commissione deve essere collegata ad almeno un Settore."}
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Dopo il save, se non ha settori (es. creata da shell), non blocchiamo
        # (la validazione e' demandata al form/admin).

    @property
    def settore_principale(self):
        """Restituisce il primo settore collegato (snapshot predefinito)."""
        return self.settori.first()