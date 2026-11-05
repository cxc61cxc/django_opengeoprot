class QwenMapRouter:
    """
    Router per usare il database 'qwen_map' solo per l'app 'qwen_map'.

    - Letture e scritture dei modelli qwen_map -> database 'qwen_map'
    - Migrazioni qwen_map -> solo su database 'qwen_map'
    - Le altre app restano sul database default
    """

    route_app_label = "qwen_map"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.route_app_label:
            return "qwen_map"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.route_app_label:
            return "qwen_map"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Evita relazioni cross-database non supportate.

        Se entrambi gli oggetti sono nella stessa app, permette la relazione.
        Se uno dei due è qwen_map e l'altro no, la blocca.
        """
        if obj1._meta.app_label == obj2._meta.app_label:
            return True

        if (
            obj1._meta.app_label == self.route_app_label
            or obj2._meta.app_label == self.route_app_label
        ):
            return False

        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        L'app qwen_map migra solo sul database qwen_map.
        Le altre app non migrano sul database qwen_map.
        """
        if app_label == self.route_app_label:
            return db == "qwen_map"

        if db == "qwen_map":
            return False

        return None