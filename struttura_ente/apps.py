from django.apps import AppConfig


class StrutturaEnteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'struttura_ente'

    def ready(self):
        import struttura_ente.signals
