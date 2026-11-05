from protocollo.reports.base import BaseReport


class OsservatorioPoc2022Report(BaseReport):
    """
    Report per l'Osservatorio Permanente al POC 2022.
    Raccoglie tutte le pratiche con tipo_pratica_id=30,
    raggruppate per classe.
    """

    TIPO_PRATICA_ID = 30

    def __init__(self, queryset=None):
        super().__init__(queryset)
        self.filter_by_tipo_pratica(self.TIPO_PRATICA_ID)

    def get_classi_summary(self):
        """
        Restituisce un dict strutturato per classe:
        {
            classe_valore: {
                'count': numero_pratiche,
                'pratiche': queryset_pratiche
            },
            ...
        }
        """
        grouped = self.group_by_field('classe')
        summary = {}
        for classe_val, qs in grouped.items():
            summary[classe_val] = {
                'count': qs.count(),
                'pratiche': qs.order_by('-data_prot_gen'),
            }
        return summary

    def get_classi_counts(self):
        """
        Restituisce una lista di tuple (classe, conteggio) ordinata per classe.
        """
        counts = self.count_by_field('classe')
        return [(item['classe'], item['count']) for item in counts]

    def get_statistiche(self):
        """
        Restituisce statistiche generali sul report.
        """
        total = self.total_count()
        classi = self.get_classi_summary()
        return {
            'totale_pratiche': total,
            'numero_classi': len(classi),
            'classi': classi,
        }
