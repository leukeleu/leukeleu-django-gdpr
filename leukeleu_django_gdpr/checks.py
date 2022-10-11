from django.core.checks import Info, register

from leukeleu_django_gdpr.gdpr import get_pii_stats


class Tags:
    confidentiality = "confidentiality"


I001 = Info(
    "You have one or more model field(s) without a PII classification.",
    hint="Update gpdr.yml and mark all field with either pii: true or pii: false.",
    id="gdpr.I001",
)


@register(Tags.confidentiality)
def check_pii_stats(app_configs, **kwargs):
    """
    Make sure there are no model fields without a PII classification.
    """
    stats = get_pii_stats()

    if stats[None] > 0:
        return [I001]
    else:
        return []
