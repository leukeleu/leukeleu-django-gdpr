from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    is_pregnant = models.BooleanField(
        default=False, help_text=_("Is the user pregnant?")
    )

    date_of_birth = models.DateField(_("Date of birth"), null=True, blank=True)
    bsn = models.CharField(_("BSN"), max_length=9, null=True, blank=True)


class SpecialUser(CustomUser):
    speciality = models.CharField(
        _("Speciality"),
        max_length=255,
        null=True,
        blank=True,
        help_text=mark_safe(
            _(
                "Speciality of the user. <a href='https://example.com' target='_blank'>More info</a>"
            )
        ),
    )


class ExclusiveUser(CustomUser):
    is_exclusive = models.BooleanField(
        default=False, help_text=_("Is the user exclusive?")
    )


class ProxyUser(CustomUser):
    class Meta:
        proxy = True
