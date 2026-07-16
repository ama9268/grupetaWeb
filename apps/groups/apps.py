from django.apps import AppConfig


class GroupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.groups'
    verbose_name = 'Grupetas'

    def ready(self):
        import apps.groups.signals  # noqa: F401
