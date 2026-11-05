from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from istruttoria_poc.forms import IstruttoriaForm, IstrCommForm, IstrConsForm
from istruttoria_poc.models import Istruttoria, IstrComm, IstrCons
from protocollo.models import Pratica

User = get_user_model()

CASI = (
    (Istruttoria, IstruttoriaForm, 'data_istr_poc', 'istruttoria_detail', 'istruttoria_delete'),
    (IstrComm, IstrCommForm, 'data_commissione', 'istrcomm_detail', 'istrcomm_delete'),
    (IstrCons, IstrConsForm, 'data_consiglio', 'istrcons_detail', 'istrcons_delete'),
)


class IstruttoriaPocTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='istruttore', password='x')
        self.staff = User.objects.create_user(username='staff', password='x', is_staff=True)
        self.pratica = Pratica.objects.create(
            prot_gen='2026/0001',
            data_prot_gen=date(2026, 1, 15),
            oggetto='Pratica di prova',
        )
        self.client.force_login(self.user)

    def test_visualizzazione_non_crea_il_record(self):
        for model, _form, _data, url_name, _delete in CASI:
            with self.subTest(modello=model.__name__):
                self.client.get(reverse(f'istruttoria_poc:{url_name}', args=[self.pratica.pk]))
                self.assertFalse(model.objects.filter(pratica=self.pratica).exists())

    def test_salvatagging_imposta_utente_e_data(self):
        for model, _form, campo_data, url_name, _delete in CASI:
            with self.subTest(modello=model.__name__):
                url = reverse(f'istruttoria_poc:{url_name}', args=[self.pratica.pk])
                risposta = self.client.post(url, {'testo': 'Testo prova', campo_data: '2026-02-01'})
                self.assertRedirects(risposta, reverse('protocollo:pratica_detail_url', args=[self.pratica.pk]))

                oggetto = model.objects.get(pratica=self.pratica)
                self.assertEqual(oggetto.testo, 'Testo prova')
                self.assertEqual(oggetto.user, self.user)
                self.assertEqual(oggetto.data_val, date(2026, 2, 1))
                self.assertTrue(oggetto.compilata)
                self.assertTrue(oggetto.history.exists())

    def test_testo_obbligatorio(self):
        for model, _form, campo_data, url_name, _delete in CASI:
            with self.subTest(modello=model.__name__):
                url = reverse(f'istruttoria_poc:{url_name}', args=[self.pratica.pk])
                risposta = self.client.post(url, {'testo': '   ', campo_data: '2026-02-01'})
                self.assertEqual(risposta.status_code, 200)
                self.assertTrue(risposta.context['form'].errors)
                self.assertFalse(model.objects.filter(pratica=self.pratica).exists())

    def test_visualizza_errori_del_modulo(self):
        url = reverse('istruttoria_poc:istruttoria_detail', args=[self.pratica.pk])
        risposta = self.client.post(url, {'testo': '', 'data_istr_poc': ''})
        self.assertContains(risposta, 'Correggi gli errori del modulo.')
        self.assertTrue(risposta.context['form'].errors)

    def test_eliminazione_negata_ai_non_autore(self):
        """Un utente loggato che non ha redatto il testo non puo azzerarlo."""
        for model, _form, _data, _url, delete_name in CASI:
            with self.subTest(modello=model.__name__):
                oggetto = model.objects.create(
                    pratica=self.pratica,
                    testo='Da eliminare',
                    user=self.staff,
                )
                url = reverse(f'istruttoria_poc:{delete_name}', args=[self.pratica.pk])
                self.client.post(url)
                oggetto.refresh_from_db()
                self.assertEqual(oggetto.testo, 'Da eliminare')
                model.objects.all().delete()

    def test_eliminazione_consentita_all_autore(self):
        for model, _form, _data, _url, delete_name in CASI:
            with self.subTest(modello=model.__name__):
                model.objects.create(pratica=self.pratica, testo='Da eliminare', user=self.user)
                url = reverse(f'istruttoria_poc:{delete_name}', args=[self.pratica.pk])
                self.client.post(url)
                oggetto = model.objects.get(pratica=self.pratica)
                self.assertFalse(oggetto.testo)
                self.assertIsNone(oggetto.data_val)
                self.assertIsNone(oggetto.user)
                model.objects.all().delete()

    def test_eliminazione_consentita_allo_staff(self):
        for model, _form, _data, _url, delete_name in CASI:
            with self.subTest(modello=model.__name__):
                oggetto = model.objects.create(
                    pratica=self.pratica,
                    testo='Da eliminare',
                    user=self.user,
                )
                data_field = model.data_field
                setattr(oggetto, data_field, date(2026, 2, 1))
                oggetto.save()

                self.client.force_login(self.staff)
                url = reverse(f'istruttoria_poc:{delete_name}', args=[self.pratica.pk])
                self.client.post(url)
                self.client.force_login(self.user)

                oggetto.refresh_from_db()
                self.assertFalse(oggetto.testo)
                self.assertIsNone(oggetto.data_val)
                self.assertIsNone(oggetto.user)
                self.assertTrue(oggetto.vuota)

    def test_eliminazione_richiama_il_metodo_post(self):
        Istruttoria.objects.create(pratica=self.pratica, testo='Da eliminare', user=self.user)
        self.client.force_login(self.staff)
        url = reverse('istruttoria_poc:istruttoria_delete', args=[self.pratica.pk])
        risposta = self.client.get(url)
        self.assertRedirects(risposta, reverse('istruttoria_poc:istruttoria_detail', args=[self.pratica.pk]))

    def test_get_absolute_url(self):
        for model, _form, _data, url_name, _delete in CASI:
            with self.subTest(modello=model.__name__):
                oggetto = model(pratica=self.pratica)
                self.assertEqual(
                    oggetto.get_absolute_url(),
                    reverse(f'istruttoria_poc:{url_name}', args=[self.pratica.pk]),
                )


class FormDataDefaultTestCase(TestCase):
    def test_data_di_default_a_oggi(self):
        for model, form_class, campo_data, _url, _delete in CASI:
            with self.subTest(modello=model.__name__):
                form = form_class(instance=model(pratica=None))
                self.assertEqual(
                    form.fields[campo_data].initial,
                    timezone.now().date(),
                )

    def test_data_di_default_sovrascritta(self):
        istanza = Istruttoria(pratica=None, data_istr_poc=date(2026, 3, 3))
        form = IstruttoriaForm(instance=istanza)
        self.assertIsNone(form.fields['data_istr_poc'].initial)
