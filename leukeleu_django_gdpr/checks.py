from django.core.checks import Warning, register

from leukeleu_django_gdpr.management.commands.gdpr import get_pii_stats


class Tags:
    confidentiality = "confidentiality"


W001 = Warning(
    "You have fields that have not been marked as PII or not.",
    hint="Please mark all fields as PII or not.",
    id="leukeleu_django_gdpr.W001",
)


@register(Tags.confidentiality, deploy=True)
def check_pii_fields(app_configs, **kwargs):
    """
    Check that all fields have been marked as PII or not.
    """
    stats = get_pii_stats()

    if stats[None] > 0:
        return [W001]
    else:
        return []
