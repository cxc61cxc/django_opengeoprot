class CatastoRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'catasto' and model._meta.model_name == 'particelle':
            return 'anagrafe'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'catasto' and model._meta.model_name == 'particelle':
            return 'anagrafe'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'catasto' and model_name == 'particelle':
            return db == 'anagrafe'
        return None
