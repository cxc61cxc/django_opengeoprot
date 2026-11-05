from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from protocollo.models import Particella
from catasto.models import Particelle
from edilizia_compat import normalize_foglio


class Command(BaseCommand):
    help = (
        'Carica la geometria (mpoly) delle particelle di protocollo '
        'che non l\'hanno, prelevandola da catasto_particelle.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra solo cosa verrebbe aggiornato, senza modifiche',
        )

    def handle(self, *args, **options):
        particelle_senza_geom = Particella.objects.filter(mpoly__isnull=True)
        totali = particelle_senza_geom.count()
        self.stdout.write(f'Particelle senza geometria: {totali}')

        aggiornate = 0
        saltate = 0
        errori = 0
        pratiche_aggiornate = set()

        for idx, p in enumerate(particelle_senza_geom.iterator(), start=1):
            foglio_norm = normalize_foglio(p.foglio) or p.foglio
            mappale_norm = p.mappale

            catasto_match = Particelle.objects.filter(
                foglio__iexact=foglio_norm,
                mappale__iexact=mappale_norm,
            ).first()

            if not catasto_match or catasto_match.mpoly is None:
                saltate += 1
                self.stdout.write(
                    f'  {idx}/{totali} SALTATA F:{p.foglio} M:{p.mappale} '
                    f'(nessun match in catasto o senza geometria)'
                )
                continue

            try:
                geom = catasto_match.mpoly
                if isinstance(geom, str):
                    geom = GEOSGeometry(geom)

                if geom and geom.srid and geom.srid != 4326:
                    geom.transform(4326)

                if geom and geom.geom_type == 'Polygon':
                    geom = MultiPolygon(geom)

                if geom and not geom.valid:
                    geom = geom.buffer(0)

                if options['dry_run']:
                    self.stdout.write(
                        f'  {idx}/{totali} AGGIORNA F:{p.foglio} M:{p.mappale} '
                        f'da catasto id={catasto_match.id}'
                    )
                else:
                    p.mpoly = geom
                    p.save(update_fields=['mpoly', 'data_mod'])
                    aggiornate += 1

                    for cp in p.particelle_in.all():
                        if cp.pratica_id:
                            pratiche_aggiornate.add(cp.pratica_id)

                if idx % 500 == 0 or idx == totali:
                    self.stdout.write(f'  Elaborate {idx}/{totali}')

            except Exception as e:
                errori += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  {idx}/{totali} ERRORE F:{p.foglio} M:{p.mappale}: {e}'
                    )
                )

        self.stdout.write(
            f'Geometrie caricate: {aggiornate} | Saltate: {saltate} | Errori: {errori}'
        )

        if not options['dry_run'] and pratiche_aggiornate:
            self.stdout.write(
                f'Aggiornamento mpoly_pratica per {len(pratiche_aggiornate)} pratiche...'
            )
            from protocollo.models import Pratica
            for pid in pratiche_aggiornate:
                try:
                    Pratica.objects.get(pk=pid).update_mpoly_pratica()
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  Pratica {pid}: {e}')
                    )
            self.stdout.write(self.style.SUCCESS('Fatto.'))
