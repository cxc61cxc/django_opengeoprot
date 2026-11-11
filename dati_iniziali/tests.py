import csv
import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase

from dati_iniziali import io_csv
from protocollo.models import TipoPratica
from struttura_ente.models import Settore, Servizio, AttivitaUO

User = get_user_model()


class DatiInizialiTest(TestCase):
    """Esporta -> svuota il DB -> reimporta, verificando il round-trip."""

    def setUp(self):
        self.cartella = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.cartella, True)

        # Struttura dell'ente (settore 6: il segnale non crea gruppi)
        settore = Settore.objects.create(codice='settore 6', nome='Governo del Territorio')
        settore.storico_apri()
        servizio = Servizio.objects.create(settore=settore, codice='6.1', nome='Urbanistica')
        servizio.storico_apri()
        attivita = AttivitaUO.objects.create(servizio=servizio, nome='SUEP')
        attivita.storico_apri()
        altra_uo = AttivitaUO.objects.create(servizio=servizio, nome='Pianificazione')
        altra_uo.storico_apri()

        self.user = User.objects.create_user(username='m.rossi', password='x')

        self.tipo = TipoPratica.objects.create(
            name='scia',
            description='Segnalazione certificata di inizio attivita',
            settore=settore,
            servizio=servizio.versione_vigente,
            u_o=attivita.versione_vigente,
            visibile_solo_uo=True,
            user=self.user,
        )
        self.tipo.uo_visibili.set([
            attivita.versione_vigente,
            altra_uo.versione_vigente,
        ])

        self.permesso = Permission.objects.get(
            content_type__app_label='protocollo',
            codename='visualizza_tipo_pratica',
        )
        self.gruppo = Group.objects.create(name='prova_gruppo')
        self.gruppo.permissions.add(self.permesso)

    def _esporta(self):
        p_tipi = os.path.join(self.cartella, io_csv.FILE_TIPO_PRATICA)
        p_gruppi = os.path.join(self.cartella, io_csv.FILE_GRUPPI)
        n_tipi = io_csv.esporta_tipo_pratica(p_tipi)
        n_gruppi = io_csv.esporta_gruppi(p_gruppi)
        self.assertEqual(n_tipi, 1)
        self.assertEqual(n_gruppi, Group.objects.count())
        return p_tipi, p_gruppi

    def test_round_trip(self):
        p_tipi, p_gruppi = self._esporta()

        TipoPratica.objects.all().delete()
        Group.objects.all().delete()
        self.assertEqual(TipoPratica.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)

        report_gruppi = io_csv.carica_gruppi(p_gruppi)
        report_tipi = io_csv.carica_tipo_pratica(p_tipi)

        self.assertEqual(report_gruppi['creati'], 1)
        self.assertEqual(report_gruppi['avvisi'], [])
        self.assertEqual(report_tipi['creati'], 1)
        self.assertEqual(report_tipi['avvisi'], [])

        # gruppo ripristinato con gli stessi permessi
        gruppo = Group.objects.get(name='prova_gruppo')
        self.assertEqual(list(gruppo.permissions.all()), [self.permesso])

        # tipo pratica ripristinato con tutti i riferimenti risolti
        tipo = TipoPratica.objects.get(name='scia')
        self.assertEqual(tipo.description, self.tipo.description)
        self.assertEqual(tipo.settore.codice, 'settore 6')
        self.assertEqual(tipo.servizio.codice, '6.1')
        self.assertEqual(tipo.u_o.nome, 'SUEP')
        self.assertTrue(tipo.visibile_solo_uo)
        self.assertEqual(tipo.user.username, 'm.rossi')
        self.assertEqual(
            sorted(tipo.uo_visibili.values_list('nome', flat=True)),
            ['Pianificazione', 'SUEP'],
        )

    def test_secondo_caricamento_non_sovrascrive(self):
        p_tipi, p_gruppi = self._esporta()

        tipo = TipoPratica.objects.get(name='scia')
        tipo.description = 'modificato in locale'
        tipo.save(update_fields=['description'])
        gruppo = Group.objects.get(name='prova_gruppo')
        gruppo.permissions.clear()

        report_tipi = io_csv.carica_tipo_pratica(p_tipi)
        report_gruppi = io_csv.carica_gruppi(p_gruppi)

        self.assertEqual(report_tipi['presenti'], 1)
        self.assertEqual(report_tipi['aggiornati'], 0)
        self.assertEqual(
            TipoPratica.objects.get(name='scia').description,
            'modificato in locale',
        )
        # il gruppo era vuoto: i permessi vengono completati
        self.assertEqual(report_gruppi['presenti'], 1)
        self.assertEqual(report_gruppi['aggiornati'], 1)
        self.assertEqual(
            list(Group.objects.get(name='prova_gruppo').permissions.all()),
            [self.permesso],
        )

        # con --force il CSV prevale
        report_forzato = io_csv.carica_tipo_pratica(p_tipi, force=True)
        self.assertEqual(report_forzato['aggiornati'], 1)
        self.assertEqual(
            TipoPratica.objects.get(name='scia').description,
            self.tipo.description,
        )

    def test_riferimenti_mancanti_lasciano_vuoto_e_avvisano(self):
        percorso = os.path.join(self.cartella, io_csv.FILE_TIPO_PRATICA)
        with open(percorso, 'w', newline='', encoding=io_csv.ENCODING) as f:
            writer = csv.DictWriter(
                f, fieldnames=io_csv.COLONNE_TIPO_PRATICA, delimiter=io_csv.DELIMITER
            )
            writer.writeheader()
            writer.writerow({
                'id_orig': '900',
                'name': 'pratica nuova',
                'description': 'senza riferimenti',
                'settore': 'settore inesistente',
                'servizio': '9.9',
                'u_o': 'UO inesistente',
                'visibile_solo_uo': '1',
                'uo_visibili': 'UO inesistente',
                'user': 'utente inesistente',
            })

        report = io_csv.carica_tipo_pratica(percorso)
        self.assertEqual(report['creati'], 1)

        tipo = TipoPratica.objects.get(name='pratica nuova')
        self.assertIsNone(tipo.settore)
        self.assertIsNone(tipo.servizio)
        self.assertIsNone(tipo.u_o)
        self.assertIsNone(tipo.user)
        self.assertEqual(tipo.uo_visibili.count(), 0)

        testi = '\n'.join(report['avvisi'])
        self.assertIn('settore "settore inesistente" non trovato', testi)
        self.assertIn('servizio "9.9" non trovato', testi)
        self.assertIn('unita operativa "UO inesistente" non trovata', testi)
        self.assertIn('utente "utente inesistente" non trovato', testi)

    def test_dry_run_non_scrive(self):
        p_tipi, p_gruppi = self._esporta()
        TipoPratica.objects.all().delete()
        Group.objects.all().delete()

        report_tipi = io_csv.carica_tipo_pratica(p_tipi, dry_run=True)
        report_gruppi = io_csv.carica_gruppi(p_gruppi, dry_run=True)

        self.assertEqual(report_tipi['creati'], 1)
        self.assertEqual(report_gruppi['creati'], 1)
        self.assertEqual(TipoPratica.objects.count(), 0)
        self.assertEqual(Group.objects.count(), 0)

    def test_keep_ids_mantiene_id_e_riallinea_sequenza(self):
        p_tipi, _ = self._esporta()
        id_originale = self.tipo.id
        TipoPratica.objects.all().delete()

        report = io_csv.carica_tipo_pratica(p_tipi, keep_ids=True)
        self.assertEqual(report['creati'], 1)
        self.assertEqual(TipoPratica.objects.get(name='scia').id, id_originale)

        # la sequenza deve essere stata riallineata: il nuovo id e' superiore
        nuovo = TipoPratica.objects.create(name='altro')
        self.assertGreater(nuovo.id, id_originale)

    def test_permessi_sconosciuti_segnalati(self):
        percorso = os.path.join(self.cartella, io_csv.FILE_GRUPPI)
        with open(percorso, 'w', newline='', encoding=io_csv.ENCODING) as f:
            writer = csv.DictWriter(
                f, fieldnames=io_csv.COLONNE_GRUPPI, delimiter=io_csv.DELIMITER
            )
            writer.writeheader()
            writer.writerow({'name': 'gruppo prova', 'permessi': 'auth.add_user|foo.bar'})

        report = io_csv.carica_gruppi(percorso)
        gruppo = Group.objects.get(name='gruppo prova')
        self.assertEqual(report['creati'], 1)
        self.assertEqual(gruppo.permissions.count(), 1)
        self.assertTrue(any('foo.bar' in a for a in report['avvisi']))
