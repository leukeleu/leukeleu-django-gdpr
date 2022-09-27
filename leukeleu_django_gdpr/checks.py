from django.core.checks import Warning, register

from leukeleu_django_gdpr.management.commands.gdpr import get_pii_stats


class Tags:
    confidentiality = "confidentiality"


W001 = Warning(
    "You have fields that need to be classified as either PII or non-PII.",
    hint="Please classify all fields in gpdr.yml by marking the pii property with True or False",
    id="leukeleu_django_gdpr.W001",
)


@register(Tags.confidentiality, deploy=True)
def check_pii_fields(app_configs, **kwargs):
    """
    Check that all fields have been classified as either PII or non-PII.
    """
    stats = get_pii_stats()

    if stats[None] > 0:
        return [W001]
    else:
        return []
