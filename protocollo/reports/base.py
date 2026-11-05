from collections import defaultdict
from django.db.models import Count, Q


class BaseReport:
    """
    Base class per report generici sulle pratiche.
    Fornisce metodi comuni di filtro, raggruppamento e aggregazione.
    """

    def __init__(self, queryset=None):
        from protocollo.models import Pratica
        self.queryset = queryset if queryset is not None else Pratica.objects.all()

    def filter_by_tipo_pratica(self, tipo_pratica_id):
        self.queryset = self.queryset.filter(tipo_pratica_id=tipo_pratica_id)
        return self

    def filter_by_stato(self, stato):
        self.queryset = self.queryset.filter(stato=stato)
        return self

    def filter_by_date_range(self, start_date=None, end_date=None):
        if start_date:
            self.queryset = self.queryset.filter(data_prot_gen__gte=start_date)
        if end_date:
            self.queryset = self.queryset.filter(data_prot_gen__lte=end_date)
        return self

    def total_count(self):
        return self.queryset.count()

    def group_by_field(self, field_name):
        """
        Raggruppa le pratiche per il campo indicato.
        Restituisce un dict: {valore_campo: queryset_pratiche}
        """
        values = self.queryset.values_list(field_name, flat=True).distinct().order_by(field_name)
        grouped = {}
        for val in values:
            if val is None:
                val_display = "Non definito"
            else:
                val_display = val
            grouped[val_display] = self.queryset.filter(**{field_name: val})
        return grouped

    def count_by_field(self, field_name):
        """
        Conta le pratiche per ogni valore del campo.
        Restituisce un list di tuple: (valore_campo, conteggio)
        """
        return (
            self.queryset.values(field_name)
            .annotate(count=Count('id'))
            .order_by('-count')
        )
