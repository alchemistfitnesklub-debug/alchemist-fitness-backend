# klub_app/apps.py
from django.apps import AppConfig

class KlubAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'klub_app'

    def ready(self):
        import klub_app.signals  # UKLONJEN KOMENTAR – SIGNALE AKTIVNE