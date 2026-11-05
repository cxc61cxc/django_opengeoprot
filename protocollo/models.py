from django.db import models
from django.urls import reverse
from django.utils.timezone import now
import datetime

import os
from simple_history.models import HistoricalRecords

from django.contrib.gis.db import models # as gis_models

from django.contrib.auth import get_user_model
# from django.db import models
from viario.models import Civici

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

User=get_user_model()


class TipoPratica(models.Model):
	name = models.CharField(max_length=70, unique=True)
	description = models.CharField(max_length=170, null=True, blank=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
	settore = models.ForeignKey(
		'struttura_ente.Settore',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='tipo_pratiche',
		help_text='Settore di appartenenza del tipo pratica.',
	)
	servizio = models.ForeignKey(
		'struttura_ente.StoricoServizio',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='tipo_pratiche',
		help_text='Se impostato, filtra le pratiche a livello di servizio.',
	)
	u_o = models.ForeignKey(
		'struttura_ente.StoricoAttivitaUO',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='tipo_pratiche',
		help_text='Se impostato, filtra le pratiche a livello di unita operativa.',
	)
	visibile_solo_uo = models.BooleanField(
		default=False,
		help_text='Se attivo, la pratica è visibile e scaricabile solo da staff e utenti appartenenti alle U.O. indicate in "uo_visibili".',
	)
	uo_visibili = models.ManyToManyField(
		'struttura_ente.StoricoAttivitaUO',
		blank=True,
		related_name='tipo_pratiche_visibili',
		help_text='Unità operative abilitate alla visualizzazione (attivo solo se "visibile_solo_uo" è impostato).',
	)
	history = HistoricalRecords()
		
	class Meta:
		permissions = [
			('visualizza_tipo_pratica', 'Puoi visualizzare tipo pratica'),
		]
		verbose_name_plural="TipoPratiche"
		ordering = ['settore']

	def __str__(self):
		return self.name

	def get_absolute_url(self):       # ---> new function
		return reverse('tipopratica_detail', args=[str(self.id)])

	def numero_pratiche(self):
		"""Restituisce il numero di pratiche collegate a questo tipo di pratica."""
		return self.tipo_pratiche.count()
	
	

class Soggetto(models.Model):
	cognome = models.CharField(max_length=150)
	nome = models.CharField(max_length=100)
	data_nascita = models.DateField(null=True, blank=True)
	comune_nascita = models.CharField(max_length=80, null=True, blank=True)
	codice_fiscale = models.CharField(max_length=16, null=True, blank=True)
	comune_residenza = models.CharField(max_length=80, null=True, blank=True)
	addr = models.CharField(max_length=150, null=True, blank=True)
	addr_sede = models.CharField(max_length=150, null=True, blank=True)
	email = models.EmailField( blank=True,null=True)
	pec = models.EmailField("PEC",null=True)
	cellulare = models.CharField(max_length=100, null=True)
	telefono = models.CharField(max_length=100, null=True)
	fax = models.CharField(max_length=100, null=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
	history = HistoricalRecords()

	class Meta:
		verbose_name_plural="Soggetti"
		ordering = ['cognome','nome']
		constraints = [
            models.UniqueConstraint(fields=['cognome', 'nome','codice_fiscale', 'email'], name='email_soggetto'),
        ]

	def __str__(self):
		return self.cognome + ' ' + self.nome

	def get_absolute_url(self):       # ---> new function
		return reverse('soggetto_detail_nopk_url', kwargs={'id': self.id})

class Particella(models.Model):
	foglio		=	models.CharField(max_length=5)
	mappale		=	models.CharField(max_length=5)
	mpoly       = models.MultiPolygonField(srid=4326, null=True, blank=True)

	class Meta:
		verbose_name_plural="Particelle"
		ordering = ['foglio','mappale']
		# Impedisce i doppioni basandosi su foglio e mappale
		constraints = [
            models.UniqueConstraint(fields=['foglio', 'mappale'], name='particella_unique'),
        ]
	
	def __str__(self):
		return self.foglio + '-' + self.mappale

	def get_absolute_url(self):       # ---> new function
		return reverse('particella_detail_url', kwargs={'id': self.id})

	
		

stato_choice = [
    ('a', 'attiva'),
    ('aa', 'archiviata'),
    ('c', 'chiusa'),
    ('i', 'in corso'),
    ('s', 'sospesa'),
	('ic', 'inviata comunicazione'),
	('ri', 'richiesta integrazione'),
	('ai', 'importo accettato'),
	('bd', 'bozza determina'),
	('df', 'determina firmata'),
	('ia', 'inviata ad amministrativi'),
	('af', 'alla firma'),
	('np', 'improcedibile'),
	('dn', 'Determina inviata a notaio'),
	('eo', 'emessa Ordinanza'),
    ]


class Pratica(models.Model):
	prot_gen = models.CharField('Prot.Gen.',max_length=20)
	data_prot_gen = models.DateField()
	stato = models.CharField(max_length=25, choices=stato_choice, null=True, default='a')
	code_p = models.BigIntegerField(null=True, blank=True) # contatore pratiche
	classe = models.IntegerField(null=True, blank=True)

	sub_code = models.IntegerField(null=True, blank=True)
	street=models.ForeignKey(Civici,on_delete=models.SET_NULL, related_name='pratiche_strada', blank=True, null=True)
	housenumber=models.CharField('Civico',max_length=50, blank=True, null=True)
	posizione = models.PointField(null=True, blank=True)
	mpoly_pratica = models.MultiPolygonField(srid=4326, null=True, blank=True)
	tipo_pratica = models.ForeignKey(TipoPratica, on_delete=models.SET_NULL, related_name='tipo_pratiche', blank=True, null=True)
	oggetto = models.TextField(null=True, blank=True)
	annotazioni = models.TextField(null=True, blank=True)
	soggetto_pratica = models.ManyToManyField(Soggetto,related_name="soggetti_in", through='Anaprat')
	particella_pratica = models.ManyToManyField(Particella,related_name="particelle_in", through='Cataprat')
	user = models.ForeignKey(User,on_delete=models.SET_NULL, blank=True, null=True)
	user_name = models.CharField(blank=True, help_text="Snapshot del nome utente al momento della creazione.", max_length=255, null=True)
	data_crea=models.DateTimeField(auto_now_add=True, blank=True, null=True)
	data_mod= models.DateTimeField(auto_now=True, blank=True,null=True)
	modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='pratiche_modificate')
	history = HistoricalRecords()
    
	class Meta:

		verbose_name_plural="Pratiche"
		ordering = ['-data_prot_gen']
		

	def save(self, *args, **kwargs):
		if self.user and not self.user_name:
			self.user_name = str(self.user)
		super().save(*args, **kwargs)

	def __str__(self):
		return str(self.data_prot_gen.year) +'-'+ self.prot_gen +'-'+ self.tipo_pratica.name

	def get_absolute_url(self):       # ---> new function
		return reverse('pratica_detail', args=[str(self.id)])

	@property
	def particelle_info(self):
		"""Restituisce una stringa formattata con Foglio, Mappale e Subalterno."""
		# 'pratiche' è il related_name definito in Cataprat.pratica
		res = [
			f"F:{cp.particella.foglio} M:{cp.particella.mappale} (sub.{cp.subalterno})" 
			for cp in self.pratiche.all()
		]
		return ", ".join(res) if res else "---"

	def update_mpoly_pratica(self):
		"""
		Aggiorna la geometria mpoly_pratica unendo le geometrie mpoly 
		delle particelle associate (entrambi SRID 4326).
		Gestisce anche geometrie invalide (autointersezioni) riparandole con buffer(0).
		"""
		from django.contrib.gis.db.models import Union
		from django.contrib.gis.geos import GeometryCollection
		
		try:
			res = self.particella_pratica.aggregate(combined=Union('mpoly'))
			combined = res.get('combined')
		except Exception:
			geoms = [
				g for g in self.particella_pratica.values_list('mpoly', flat=True)
				if g is not None
			]
			fixed = []
			for g in geoms:
				try:
					if not g.valid:
						g = g.buffer(0)
					fixed.append(g)
				except Exception:
					pass
			combined = GeometryCollection(fixed).unary_union if fixed else None
		
		if combined:
			if combined.geom_type == 'Polygon':
				self.mpoly_pratica = MultiPolygon(combined)
			elif combined.geom_type == 'MultiPolygon':
				self.mpoly_pratica = combined
			elif combined.geom_type == 'GeometryCollection':
				polygons = [geom for geom in combined if geom.geom_type in ('Polygon', 'MultiPolygon')]
				if polygons:
					self.mpoly_pratica = MultiPolygon(polygons)
				else:
					self.mpoly_pratica = None
			else:
				self.mpoly_pratica = None
		else:
			self.mpoly_pratica = None
		self.save(update_fields=['mpoly_pratica'])




# diario

class Diario(models.Model):
	pratica = models.ForeignKey("Pratica", on_delete=models.CASCADE, related_name='eventi')
	user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
	data_crea=models.DateTimeField(auto_now_add=True, blank=True, null=True)
	data_mod= models.DateTimeField(auto_now=True, blank=True,null=True)

	description = models.TextField(null=True, blank=True)
	history = HistoricalRecords()

	class Meta:
		verbose_name_plural="Diari"
		ordering = ['-data_crea']
		

	def __str__(self):
		return self.description



# Images & Documents
# soluzione al problema dell'username
# https://www.geeksforgeeks.org/how-to-use-user-model-in-django/

def content_file_name(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s_%s.%s" % (instance.username.id, instance.document.id, ext)
    return os.path.join('uploads', filename)

tipo_posta = [
    ('e', 'entrata'),
    ('u', 'uscita'),
	('c','caricato')
	]

class Documento(models.Model):
	pratica = models.ForeignKey("Pratica", on_delete=models.CASCADE)
	posta = models.CharField(max_length=1, choices=tipo_posta, null=True, blank=True)
	prot = models.CharField('Prot.Gen.',max_length=20, null=True, blank=True)
	data_prot = models.DateField(null=True, blank=True)
	name = models.CharField(max_length=700, null=True)
	document = models.FileField(upload_to='protocollo/uploads/',null=True, blank=True)
	username = models.ForeignKey(User,on_delete=models.SET_NULL, blank=True, null=True)
	username_name = models.CharField(blank=True, help_text="Snapshot del nome utente al momento della creazione.", max_length=255, null=True)
	data_crea=models.DateTimeField(auto_now_add=True, blank=True, null=True)
	data_mod= models.DateTimeField(auto_now=True, blank=True,null=True)

	class Meta:
		verbose_name_plural="Documenti"
		ordering = ['id']
		

	def save(self, *args, **kwargs):
		if self.username and not self.username_name:
			self.username_name = str(self.username)
		super().save(*args, **kwargs)

	def __str__(self):
		return self.name

	def get_absolute_url(self):
		return reverse('documento_detail', args=[str(self.id)])

class DocumentoDownload(models.Model):
	documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='downloads')
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
	data_download = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name_plural = "Download documenti"
		ordering = ['-data_download']

	def __str__(self):
		return f"Download {self.documento_id} da {self.user}"


class IndiceDocumento(models.Model):
	"""Testo estratto e indicizzato di un documento allegato, per ricerca full-text rapida."""
	documento = models.OneToOneField(Documento, on_delete=models.CASCADE, related_name='indice_testo')
	testo = models.TextField(blank=True, default='')
	aggiornato_al = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Indice documento"
		verbose_name_plural = "Indici documenti"

	def __str__(self):
		return f"Indice {self.documento_id}"


@receiver(post_save, sender=Documento)
def aggiorna_indice_documento(sender, instance, created, **kwargs):
	"""Estrae e indicizza il testo di un documento appena caricato."""
	try:
		indice, _ = IndiceDocumento.objects.get_or_create(documento=instance)
	except IndiceDocumento.MultipleObjectsReturned:
		indice = IndiceDocumento.objects.filter(documento=instance).first()
	from .views import _estrai_testo_documento, _sanitizza_testo
	import os
	from django.conf import settings
	if instance.document and instance.document.name:
		filepath = os.path.join(settings.MEDIA_ROOT, instance.document.name)
		if os.path.exists(filepath) and os.path.isfile(filepath):
			testo = _estrai_testo_documento(filepath)
			testo = _sanitizza_testo(testo)
			if indice.testo != testo:
				indice.testo = testo
				indice.save(update_fields=['testo', 'aggiornato_al'])

class TipoSoggetto(models.Model):
	name = models.CharField(max_length=50)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
	history = HistoricalRecords()	

	class Meta:
			verbose_name_plural="TipiSoggetto"
			ordering = ['name']

	def __str__(self):
		return self.name

	def get_absolute_url(self):       # ---> new function
		return reverse('tipo_soggetto_detail', args=[str(self.id)])

class Anaprat(models.Model):
				
        
		tipo = models.ForeignKey(TipoSoggetto,on_delete=models.SET_NULL, blank=True, null=True, related_name='soggetti_tipo')
		pratica = models.ForeignKey(Pratica, on_delete=models.CASCADE, blank=True, null=True,related_name='pratiche_soggetti')
		soggetto = models.ForeignKey(Soggetto, on_delete=models.SET_NULL, blank=True, null=True, related_name='soggetti')
		user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
		history = HistoricalRecords()

		class Meta:
			# rende unici i seguenti campi
			constraints = [
				models.UniqueConstraint(fields=['pratica', 'soggetto', 'tipo'], name='anaprat_tipo'),
			]


class SostituzioneSoggetto(models.Model):
    pratica = models.ForeignKey(Pratica, on_delete=models.CASCADE, related_name='sostituzioni_soggetti')
    ex_soggetto = models.TextField('Soggetto sostituito')
    idsoggetto_ex = models.IntegerField('ID soggetto sostituito', null=True, blank=True)
    prot_gen = models.CharField(max_length=20)
    data_prot_gen = models.DateField()
    descrizione = models.TextField(null=True, blank=True)
    soggetto_subentrato = models.ForeignKey(Soggetto, on_delete=models.SET_NULL, blank=True, null=True, related_name='sostituzioni_subentrato')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    data_crea = models.DateTimeField(auto_now_add=True)
    data_mod = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Sostituzioni soggetti"
        ordering = ['-data_crea']

    def __str__(self):
        return f"Sostituzione per pratica {self.prot_gen}"


class Cataprat(models.Model):
	subalterno = models.CharField(max_length=50,default = '-')
	pratica = models.ForeignKey(Pratica, on_delete=models.SET_NULL, blank=True, null=True, related_name='pratiche')
	particella = models.ForeignKey(Particella, on_delete=models.SET_NULL, blank=True, null=True, related_name='particelle')
	user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
	history = HistoricalRecords()

	class Meta:
		# rende unici i seguenti campi
		constraints = [
            models.UniqueConstraint(fields=[ 'pratica','particella','subalterno'], name='cataprat_subalterno'),
        ]


# ---------------------------------------------------------------------------------------
# SIGNALS per la manutenzione di mpoly_pratica
# ---------------------------------------------------------------------------------------
from django.dispatch import receiver

@receiver(post_save, sender=Cataprat)
@receiver(post_delete, sender=Cataprat)
def update_pratica_on_cataprat_change(sender, instance, **kwargs):
    """
    Aggiorna la geometria della pratica quando viene aggiunta/rimossa una relazione con una particella.
    """
    if instance.pratica:
        instance.pratica.update_mpoly_pratica()

@receiver(post_save, sender=Particella)
def update_linked_pratiche_on_particella_change(sender, instance, **kwargs):
    """
    Se la geometria di una particella cambia, aggiorna tutte le pratiche collegate.
    """
    # Verifichiamo se mpoly è tra i campi aggiornati (per evitare loop infiniti o ricalcoli inutili)
    update_fields = kwargs.get('update_fields')
    if update_fields is None or 'mpoly' in update_fields:
        pratiche_collegate = instance.particelle_in.all()
        for pratica in pratiche_collegate:
            pratica.update_mpoly_pratica()

#########################################################################################
#####################				   GEODJANGO	  				#####################
#########################################################################################



class mw_pratiche(models.Model):
    id   = models.CharField(max_length=255, primary_key=True)
    prot_gen = models.CharField(max_length=255)
    data_prot_gen          = models.DateField()
    tipo_pratica_id         = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    mpoly    = models.MultiPolygonField(srid=4326)

    class Meta:
        managed = False
        db_table='protocollo_mw_pratiche'

    def __str__(self):
        return self.tipo_pratica_id


STATO_NOTA = [
    ('bozza', 'Bozza'),
    ('definita', 'Definita'),
    ('inviata', 'Inviata'),
]


class NotaOSM(models.Model):
    utente = models.CharField(max_length=150, blank=True)
    testo = models.TextField()
    lat = models.FloatField()
    lng = models.FloatField()
    geom = models.PointField(srid=4326, null=True, blank=True)
    allegato = models.FileField(upload_to='note_osm/', null=True, blank=True)
    stato = models.CharField(max_length=10, choices=STATO_NOTA, default='bozza')
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']
        verbose_name = 'Nota OpenStreetMap'
        verbose_name_plural = 'Note OpenStreetMap'

    def __str__(self):
        return f"Nota {self.id} - {self.utente} ({self.data:%d/%m/%Y %H:%M})"