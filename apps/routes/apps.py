from django.apps import AppConfig


class RoutesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.routes"

    def ready(self):
        import apps.routes.signals  # noqa: F401
