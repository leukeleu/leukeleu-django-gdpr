from django.apps import AppConfig


class GdprConfig(AppConfig):
    name = "leukeleu_django_gdpr"
    verbose_name = "GDPR"

    def ready(self):
        # register checks
        from . import checks  # noqa: F401
