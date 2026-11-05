from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from protocollo.models import Pratica
from .models import Istruttoria, IstrComm, IstrCons
from .forms import IstruttoriaForm, IstrCommForm, IstrConsForm


def _puo_eliminare(user, oggetto=None):
    """L'autore del contenuto puo azzerarlo; staff e superuser sempre."""
    if user.is_staff or user.is_superuser:
        return True
    return oggetto is not None and oggetto.user_id == user.id


def _dettaglio(request, pratica_id, model, form_class, template, etichetta, url_dettaglio, url_elimina):
    """Rendering e salvataggio condivisi da istruttoria, commissione e consiglio."""
    pratica = get_object_or_404(Pratica, pk=pratica_id)
    oggetto = model.objects.filter(pratica=pratica).first()
    if oggetto is None:
        oggetto = model(pratica=pratica)

    edit = request.GET.get('edit') == '1' or not oggetto.compilata

    if request.method == 'POST':
        form = form_class(request.POST, instance=oggetto)
        if form.is_valid():
            istanza = form.save(commit=False)
            istanza.pratica = pratica
            istanza.user = request.user
            istanza.save()
            messages.success(request, f'{etichetta} salvata.')
            return redirect('protocollo:pratica_detail_url', pk=pratica_id)
        edit = True
        messages.error(request, 'Correggi gli errori del modulo.')
    else:
        form = form_class(instance=oggetto)

    return render(request, template, {
        'pratica': pratica,
        'istruttoria': oggetto,
        'form': form,
        'edit': edit,
        'etichetta': etichetta,
        'url_dettaglio': url_dettaglio,
        'url_elimina': url_elimina,
        'puo_eliminare': _puo_eliminare(request.user, oggetto),
    })


def _elimina(request, pratica_id, model, etichetta, url_dettaglio):
    pratica = get_object_or_404(Pratica, pk=pratica_id)
    oggetto = get_object_or_404(model, pratica=pratica)

    if not _puo_eliminare(request.user, oggetto):
        messages.error(
            request,
            f'Solo chi ha redatto {etichetta.lower()} o un amministratore possono eliminarla.',
        )
        return redirect(url_dettaglio, pratica_id=pratica_id)

    if not oggetto.compilata:
        messages.warning(request, f'{etichetta} non presente.')
        return redirect(url_dettaglio, pratica_id=pratica_id)

    oggetto.svuota()
    messages.success(request, f'{etichetta} eliminata.')
    return redirect('protocollo:pratica_detail_url', pk=pratica_id)


@login_required
def istruttoria_detail(request, pratica_id):
    return _dettaglio(
        request, pratica_id, Istruttoria, IstruttoriaForm,
        'istruttoria_poc/istruttoria_detail.html', 'Istruttoria',
        'istruttoria_poc:istruttoria_detail', 'istruttoria_poc:istruttoria_delete',
    )


@login_required
def istruttoria_delete(request, pratica_id):
    if request.method != 'POST':
        return redirect('istruttoria_poc:istruttoria_detail', pratica_id=pratica_id)
    return _elimina(request, pratica_id, Istruttoria, 'Istruttoria', 'istruttoria_poc:istruttoria_detail')


@login_required
def istrcomm_detail(request, pratica_id):
    return _dettaglio(
        request, pratica_id, IstrComm, IstrCommForm,
        'istruttoria_poc/istrcomm_detail.html', 'Commissione',
        'istruttoria_poc:istrcomm_detail', 'istruttoria_poc:istrcomm_delete',
    )


@login_required
def istrcomm_delete(request, pratica_id):
    if request.method != 'POST':
        return redirect('istruttoria_poc:istrcomm_detail', pratica_id=pratica_id)
    return _elimina(request, pratica_id, IstrComm, 'Commissione', 'istruttoria_poc:istrcomm_detail')


@login_required
def istrcons_detail(request, pratica_id):
    return _dettaglio(
        request, pratica_id, IstrCons, IstrConsForm,
        'istruttoria_poc/istrcons_detail.html', 'Consiglio',
        'istruttoria_poc:istrcons_detail', 'istruttoria_poc:istrcons_delete',
    )


@login_required
def istrcons_delete(request, pratica_id):
    if request.method != 'POST':
        return redirect('istruttoria_poc:istrcons_detail', pratica_id=pratica_id)
    return _elimina(request, pratica_id, IstrCons, 'Consiglio', 'istruttoria_poc:istrcons_detail')
