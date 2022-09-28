from django.core.checks import Warning, register

from leukeleu_django_gdpr.gdpr import get_pii_stats


class Tags:
    confidentiality = "confidentiality"


W001 = Warning(
    "You have one or more model field(s) without a PII classification.",
    hint="Update gpdr.yml and mark all field with either pii: true or pii: false.",
    id="gdpr.W001",
)


@register(Tags.confidentiality)
def check_pii_stats(app_configs, **kwargs):
    """
    Make sure there are no model fields without a PII classification.
    """
    stats = get_pii_stats()

    if stats[None] > 0:
        return [W001]
    else:
        return []
