from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Settore, Servizio, AttivitaUO
from accounts.permissions import is_manager, user_passes_test_403


@login_required
@user_passes_test_403(is_manager)
def settore_list(request):
    settori = Settore.objects.prefetch_related('servizi__attivita').all()
    return render(request, 'struttura_ente/settore_list.html', {'settori': settori})


@login_required
@user_passes_test_403(is_manager)
def settore_create(request):
    if request.method == 'POST':
        codice = (request.POST.get('codice') or '').strip()
        nome = (request.POST.get('nome') or '').strip()
        descrizione = request.POST.get('descrizione') or ''
        ordine = int(request.POST.get('ordine') or 0)
        atto_riferimento = (request.POST.get('atto_riferimento') or '').strip()
        if not codice or not nome:
            messages.error(request, 'Codice e nome sono obbligatori.')
        else:
            s, created = Settore.objects.get_or_create(
                codice=codice,
                defaults={'nome': nome, 'descrizione': descrizione, 'ordine': ordine},
            )
            if created:
                s.storico_apri(atto_riferimento=atto_riferimento)
                messages.success(request, f'Settore "{s}" creato.')
            else:
                s.nome = nome
                s.descrizione = descrizione
                s.ordine = ordine
                s.save()
                s.storico_apri(atto_riferimento=atto_riferimento)
                messages.success(request, f'Settore "{s}" aggiornato.')
            return redirect('struttura_ente:settore_list')
    return render(request, 'struttura_ente/settore_form.html', {'settore': None})


@login_required
@user_passes_test_403(is_manager)
def settore_edit(request, pk):
    settore = get_object_or_404(Settore, pk=pk)
    if request.method == 'POST':
        codice = (request.POST.get('codice') or '').strip()
        nome = (request.POST.get('nome') or '').strip()
        atto_riferimento = (request.POST.get('atto_riferimento') or '').strip()
        if not codice or not nome:
            messages.error(request, 'Codice e nome sono obbligatori.')
        else:
            settore.codice = codice
            settore.nome = nome
            settore.descrizione = request.POST.get('descrizione') or ''
            settore.ordine = int(request.POST.get('ordine') or 0)
            settore.save()
            settore.storico_apri(atto_riferimento=atto_riferimento)
            messages.success(request, 'Settore aggiornato. Storico registrato.')
            return redirect('struttura_ente:settore_list')
    vigente = settore.versione_vigente
    return render(request, 'struttura_ente/settore_form.html', {
        'settore': settore,
        'vigente': vigente,
    })


@login_required
@user_passes_test_403(is_manager)
def settore_delete(request, pk):
    settore = get_object_or_404(Settore, pk=pk)
    if request.method == 'POST':
        settore.delete()
        messages.success(request, 'Settore eliminato.')
        return redirect('struttura_ente:settore_list')
    return render(request, 'struttura_ente/settore_confirm_delete.html', {'settore': settore})


@login_required
@user_passes_test_403(is_manager)
def settore_storico(request, pk):
    settore = get_object_or_404(Settore, pk=pk)
    versioni = settore.versioni.all()
    return render(request, 'struttura_ente/settore_storico.html', {
        'settore': settore,
        'versioni': versioni,
    })


@login_required
@user_passes_test_403(is_manager)
def servizio_create(request, settore_pk):
    settore = get_object_or_404(Settore, pk=settore_pk)
    if request.method == 'POST':
        codice = (request.POST.get('codice') or '').strip()
        nome = (request.POST.get('nome') or '').strip()
        atto_riferimento = (request.POST.get('atto_riferimento') or '').strip()
        if not codice or not nome:
            messages.error(request, 'Codice e nome sono obbligatori.')
        else:
            s = Servizio.objects.create(
                settore=settore,
                codice=codice,
                nome=nome,
                descrizione=request.POST.get('descrizione') or '',
                ordine=int(request.POST.get('ordine') or 0),
            )
            settore.storico_apri(atto_riferimento=atto_riferimento)
            s.storico_apri(atto_riferimento=atto_riferimento)
            messages.success(request, f'Servizio "{s}" creato.')
        return redirect('struttura_ente:settore_list')
    return render(request, 'struttura_ente/servizio_form.html', {'settore': settore, 'servizio': None})


@login_required
@user_passes_test_403(is_manager)
def servizio_edit(request, pk):
    servizio = get_object_or_404(Servizio, pk=pk)
    if request.method == 'POST':
        codice = (request.POST.get('codice') or '').strip()
        nome = (request.POST.get('nome') or '').strip()
        atto_riferimento = (request.POST.get('atto_riferimento') or '').strip()
        if not codice or not nome:
            messages.error(request, 'Codice e nome sono obbligatori.')
        else:
            servizio.codice = codice
            servizio.nome = nome
            servizio.descrizione = request.POST.get('descrizione') or ''
            servizio.ordine = int(request.POST.get('ordine') or 0)
            servizio.save()
            servizio.settore.storico_apri(atto_riferimento=atto_riferimento)
            servizio.storico_apri(atto_riferimento=atto_riferimento)
            messages.success(request, 'Servizio aggiornato.')
            return redirect('struttura_ente:settore_list')
    return render(request, 'struttura_ente/servizio_form.html', {'settore': servizio.settore, 'servizio': servizio})


@login_required
@user_passes_test_403(is_manager)
def servizio_delete(request, pk):
    servizio = get_object_or_404(Servizio, pk=pk)
    if request.method == 'POST':
        servizio.delete()
        messages.success(request, 'Servizio eliminato.')
        return redirect('struttura_ente:settore_list')
    return render(request, 'struttura_ente/servizio_confirm_delete.html', {'servizio': servizio})


@login_required
@user_passes_test_403(is_manager)
def servizio_storico(request, pk):
    servizio = get_object_or_404(Servizio, pk=pk)
    versioni = servizio.versioni.all()
    return render(request, 'struttura_ente/servizio_storico.html', {
        'servizio': servizio,
        'versioni': versioni,
    })


@login_required
@user_passes_test_403(is_manager)
def attivita_create(request, servizio_pk):
    servizio = get_object_or_404(Servizio, pk=servizio_pk)
    if request.method == 'POST':
        nome = (request.POST.get('nome') or '').strip()
        atto_riferimento = (request.POST.get('atto_riferimento') or '').strip()
        if not nome:
            messages.error(request, 'Nome obbligatorio.')
        else:
            a = AttivitaUO.objects.create(
                servizio=servizio,
                nome=nome,
                descrizione=request.POST.get('descrizione') or '',
                ordine=int(request.POST.get('ordine') or 0),
            )
            servizio.settore.storico_apri(atto_riferimento=atto_riferimento)
            servizio.storico_apri(atto_riferimento=atto_riferimento)
            a.storico_apri(atto_riferimento=atto_riferimento)
            messages.success(request, f'Attivita "{a}" aggiunta.')
        return redirect('struttura_ente:settore_list')
    return render(request, 'struttura_ente/attivita_form.html', {'servizio': servizio, 'attivita': None})


@login_required
@user_passes_test_403(is_manager)
def attivita_edit(request, pk):
    attivita = get_object_or_404(AttivitaUO, pk=pk)
    if request.method == 'POST':
        nome = (request.POST.get('nome') or '').strip()
        atto_riferimento = (request.POST.get('atto_riferimento') or '').strip()
        if not nome:
            messages.error(request, 'Nome obbligatorio.')
        else:
            attivita.nome = nome
            attivita.descrizione = request.POST.get('descrizione') or ''
            attivita.ordine = int(request.POST.get('ordine') or 0)
            attivita.save()
            attivita.servizio.settore.storico_apri(atto_riferimento=atto_riferimento)
            attivita.servizio.storico_apri(atto_riferimento=atto_riferimento)
            attivita.storico_apri(atto_riferimento=atto_riferimento)
            messages.success(request, 'Attivita aggiornata.')
            return redirect('struttura_ente:settore_list')
    return render(request, 'struttura_ente/attivita_form.html', {'servizio': attivita.servizio, 'attivita': attivita})


@login_required
@user_passes_test_403(is_manager)
def attivita_delete(request, pk):
    attivita = get_object_or_404(AttivitaUO, pk=pk)
    if request.method == 'POST':
        attivita.delete()
        messages.success(request, 'Attivita eliminata.')
        return redirect('struttura_ente:settore_list')
    return render(request, 'struttura_ente/attivita_confirm_delete.html', {'attivita': attivita})


@login_required
@user_passes_test_403(is_manager)
def attivita_storico(request, pk):
    attivita = get_object_or_404(AttivitaUO, pk=pk)
    versioni = attivita.versioni.all()
    return render(request, 'struttura_ente/attivita_storico.html', {
        'attivita': attivita,
        'versioni': versioni,
    })