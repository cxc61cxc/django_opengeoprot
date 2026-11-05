from django.shortcuts import render
from protocollo.models import *
from protocollo.views import can_edit
from coop.models import *
from ascensori.models import *
from prg.models import *
from idonall.models import *
from fotovoltaico.models import *
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q, Count
from datetime import datetime
from django.db.models import Count
from django.db.models.functions import ExtractYear



#pagina principale
@login_required
@user_passes_test(lambda u: u.groups.filter(name__in=['editor_settore_6', 'editor_settore_1','user_settore_6']).exists(), login_url='login')
def index(request):
	is_editor = can_edit(request.user)
	tp= TipoPratica.objects.all().order_by('name')

	
	# conteggio importi svincoli PEEP
	# Per non-rate: importo accettato = importo versato (unico versamento)
	# Per rate: contiamo i pagamenti effettivi (Scadenze.pagata=True)
	importo_non_rate = (AccettaImporto.objects
	    .filter(rateo=False)
	    .aggregate(total_non_rate=Sum('importo'))['total_non_rate'] or 0)
	importo_rate_pagato = (Scadenze.objects
	    .filter(pagata=True, importo_pagamento__isnull=False)
	    .aggregate(total_rate_pagato=Sum('importo_pagamento'))['total_rate_pagato'] or 0)
	importo_totale = importo_non_rate + importo_rate_pagato
	totale_svincoli = Pratica.objects.filter(tipo_pratica_id = 36).count()
	totale_svincoli_chiusi = Pratica.objects.filter(Q(tipo_pratica_id = 36) & Q(stato__in=['c', 'aa'])).count()
	totale_importo_comunicato = Pratica.objects.filter(Q(tipo_pratica_id = 36) & Q(stato__exact='ic')).count()
	totale_sospese = Pratica.objects.filter(Q(tipo_pratica_id = 36) & Q(stato__exact='s')).count()
	totale_notaio = Pratica.objects.filter(Q(tipo_pratica_id = 36) & Q(stato__exact='dn') ).count()
	totale_firma = Pratica.objects.filter(Q(tipo_pratica_id = 36)  & Q(stato__exact='af') ).count()
	totale_accettato = Pratica.objects.filter(Q(tipo_pratica_id = 36) & Q(stato__exact='ai') ).count()
	totale_incorso = Pratica.objects.filter(Q(tipo_pratica_id = 36) & Q(stato__exact='i') ).count()

	totale_convenzioni = AccettaImporto. objects.all().count() 
	
	# ricavo la data odierna
	today = datetime.now().date() # estrae la data attuale

	# conteggio patiche di svincolo per anno
	result_peep = Pratica.objects.filter(
									tipo_pratica_id=36
								).values(
									year=ExtractYear('data_prot_gen')
								).annotate(
									count=Count('id')
								).order_by('-year')
	
	# conteggio ascensori per anno
	result_ascensori = Pratica.objects.filter(
									tipo_pratica_id=38
								).values(
									year=ExtractYear('data_prot_gen')
								).annotate(
									count=Count('id')
								).order_by('-year')
	
	# conteggio cdu per anno
	result_cdu = Pratica.objects.filter(
									tipo_pratica_id=7
								).values(
									year=ExtractYear('data_prot_gen')
								).annotate(
									count=Count('id')
								).order_by('-year')

	print(result_peep,'result')
	# conteggio CDU
	cdu_anno = Cerdesurb.objects.filter(cdu_date__year=today.year).exclude(uso='Informativa')
	cdu_alla_firma = Cerdesurb.objects.filter(cdu_date__year=today.year,pratica__stato='af').exclude(uso='Informativa')
	cdu_sospesi = Cerdesurb.objects.filter(cdu_date__year=today.year,pratica__stato='ri').exclude(uso='Informativa')
	cdu_chiusi = Cerdesurb.objects.filter(cdu_date__year=today.year,pratica__stato__in=['c', 'aa']).exclude(uso='Informativa')
	print('totale cdu rilasciati', cdu_chiusi.count())

	# resoconto ascensori
	istanze_ascensori = Pratica.objects.filter(data_prot_gen__year=today.year, tipo_pratica_id = 38)
	print(istanze_ascensori.count(), 'ascensori')
	# matricole rilasciate nell'anno in corso
	matricole = Matricola.objects.filter(matricola_date__year=today.year)
	tot_matricole = matricole.count()
	print ('matricole878787', matricole)

	
	# interventi VVFF
	blocco_ascensore = Pratica.objects.filter(Q(oggetto__icontains = 'bloccato') & Q(tipo_pratica_id__exact = 38) & Q(data_prot_gen__year = today.year))
	print ('bloccati', blocco_ascensore.count())

	# verbali visita periodica con esito negativo
	negativi = Pratica.objects.filter(Q(oggetto__icontains = 'esito negativo') & Q(tipo_pratica_id__exact = 38) & Q(data_prot_gen__year = today.year))

	# IDONEITA' ALLOGGIATIVE
	idonall = Pratica.objects.filter(Q(tipo_pratica_id__exact = 26) & Q(data_prot_gen__year = today.year))
	try:
		idonall_sospesi = Pratica.objects.filter(Q(tipo_pratica_id__exact = 26) & Q(data_prot_gen__year = today.year) & Q(stato__iexact='ri'))
	except:
		idonall_sospesi = 0
	
	try:
		idonall_chiusi = Pratica.objects.filter(Q(tipo_pratica_id__exact = 26) & Q(data_prot_gen__year = today.year) & Q(stato__in=['c', 'aa']))
	except:
		idonall_chiusi = 0

	try:
		idonall_incorso = Pratica.objects.filter(Q(tipo_pratica_id__exact = 26) & Q(data_prot_gen__year = today.year) & Q(stato__in=['i', 'a']))
	except:
		idonall_incorso = 0
	print(idonall_incorso,'tdgd6666')
	# Idonall_chiusi = Idonall.objects.filter(idonall_date__year=today.year,pratica__stato='c')
	# FOTOVOLTAICO
	result = Pratica.objects.filter(
									tipo_pratica_id=14
								).values(
									year=ExtractYear('data_prot_gen')
								).annotate(
									count=Count('id')
								).order_by('-year')

	print(result,'result')

	

	context ={		
		'result':result,
		'result_peep':result_peep,
		'result_ascensori':result_ascensori,
		'result_cdu':result_cdu,
		'is_editor':is_editor,
		'tp':tp,
		'importo_totale':importo_totale,
		'totale_convenzioni':totale_convenzioni,
		'totale_svincoli':totale_svincoli,
		'totale_svincoli_chiusi':totale_svincoli_chiusi,
		'totale_importo_comunicato':totale_importo_comunicato,
		'totale_sospese':totale_sospese,
		'totale_notaio':totale_notaio,
		'totale_firma':totale_firma,
		'totale_accettato':totale_accettato,
		'totale_incorso':totale_incorso,

		'tot_matricole' : tot_matricole,

		'istanze_ascensori':istanze_ascensori.count(),
		'blocco_ascensore' : blocco_ascensore,
		'negativi' : negativi,
		'tot_cdu' : cdu_anno,
		'cdu_rilasciati' : cdu_chiusi,
		'cdu_alla_firma':cdu_alla_firma,
		'cdu_sospesi' : cdu_sospesi,
		'idonall':idonall,
		'idonall_sospesi':idonall_sospesi,
		'idonall_chiusi':idonall_chiusi,
		'idonall_incorso':idonall_incorso,
	}

	
	return render(request, 'home/index.html', context)


@login_required
def help(request):
    """Manuale utente del portale (raggiungibile dal link 'Aiuto' nel navbar)."""
    return render(request, 'home/help.html', {})
