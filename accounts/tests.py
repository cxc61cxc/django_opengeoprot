from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from protocollo.models import Pratica, TipoPratica
from struttura_ente.models import (
    AttivitaUO,
    Servizio,
    Settore,
    StoricoAttivitaUO,
    StoricoServizio,
    StoricoSettore,
)


class RichiestaAccessoAuthorizationTest(TestCase):
    def setUp(self):
        settore = Settore.objects.create(
            codice='settore 6',
            nome='Governo del Territorio',
        )
        storico_settore = StoricoSettore.objects.create(
            settore=settore,
            codice='settore 6',
            nome='Governo del Territorio',
            data_inizio=timezone.now(),
        )
        servizio = Servizio.objects.create(
            settore=settore,
            codice='6.1',
            nome='Urbanistica',
        )
        storico_servizio = StoricoServizio.objects.create(
            servizio=servizio,
            settore_storico=storico_settore,
            codice='6.1',
            nome='Urbanistica',
            data_inizio=timezone.now(),
        )
        attivita_uo = AttivitaUO.objects.create(
            servizio=servizio,
            nome='Pianificazione urbanistica',
        )
        self.uo = StoricoAttivitaUO.objects.create(
            attivita=attivita_uo,
            servizio_storico=storico_servizio,
            nome='Pianificazione urbanistica',
            data_inizio=timezone.now(),
        )
        altra_attivita_uo = AttivitaUO.objects.create(
            servizio=servizio,
            nome='Edilizia privata',
        )
        altra_uo = StoricoAttivitaUO.objects.create(
            attivita=altra_attivita_uo,
            servizio_storico=storico_servizio,
            nome='Edilizia privata',
            data_inizio=timezone.now(),
        )

        tipo_pratica = TipoPratica.objects.create(
            name='test-uo-access',
            settore=settore,
            u_o=self.uo,
            visibile_solo_uo=True,
        )
        tipo_pratica.uo_visibili.add(self.uo)
        self.pratica = Pratica.objects.create(
            prot_gen='TEST-1',
            data_prot_gen=date.today(),
            tipo_pratica=tipo_pratica,
            oggetto='Pratica test',
        )

        gruppo = Group.objects.get_or_create(name='user_settore_6')[0]
        self.utente_uo = User.objects.create_user(
            username='utente-uo',
            password='password',
        )
        self.utente_uo.groups.add(gruppo)
        Profile.objects.create(
            user=self.utente_uo,
            settore=storico_settore,
            u_o=self.uo,
        )
        self.utente_altra_uo = User.objects.create_user(
            username='utente-altra-uo',
            password='password',
        )
        self.utente_altra_uo.groups.add(gruppo)
        Profile.objects.create(
            user=self.utente_altra_uo,
            settore=storico_settore,
            u_o=altra_uo,
        )
        self.utente_staff = User.objects.create_user(
            username='utente-staff',
            password='password',
            is_staff=True,
        )

    def test_utente_della_uo_visualizza_la_richiesta_accesso(self):
        self.client.force_login(self.utente_uo)

        response = self.client.get(
            reverse('accounts:richiesta_accesso', args=[self.pratica.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'Richiesta accesso Protocollo #{self.pratica.pk}',
        )

    def test_utente_di_un_altra_uo_non_visualizza_la_richiesta_accesso(self):
        self.client.force_login(self.utente_altra_uo)

        response = self.client.get(
            reverse('accounts:richiesta_accesso', args=[self.pratica.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_utente_staff_visualizza_la_richiesta_accesso(self):
        self.client.force_login(self.utente_staff)

        response = self.client.get(
            reverse('accounts:richiesta_accesso', args=[self.pratica.pk])
        )

        self.assertEqual(response.status_code, 200)
