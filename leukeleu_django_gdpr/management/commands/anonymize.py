from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.utils.module_loading import import_string

from leukeleu_django_gdpr.anonymize import BaseAnonymizer
from leukeleu_django_gdpr.gdpr import get_pii_stats


def get_anonymizer():
    if hasattr(settings, "DJANGO_GDPR_ANONYMIZER_CLASS"):
        return import_string(settings.DJANGO_GDPR_ANONYMIZER_CLASS)()
    else:
        return BaseAnonymizer()


class Command(BaseCommand):
    """
    Goes through models and their fields and anonymizes the data if `pii: True`

    Currently, fields that are *not* required will still be anonymized.
    """

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("You can only run this command in DEBUG mode.")

        stats = get_pii_stats(save=False)
        unclassified_fields = stats.get(None, 0)
        if unclassified_fields:
            raise CommandError(
                f"There are still {unclassified_fields} unclassified PII fields. "
                "Run `manage.py gdpr` first and classify all fields."
            )

        get_anonymizer().anonymize()

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully anonymized data. Make sure to check it.",
            )
        )
