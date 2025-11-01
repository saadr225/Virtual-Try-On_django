from django.apps import AppConfig


class ClientApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api.client_api"
    verbose_name = "Client API (External)"
