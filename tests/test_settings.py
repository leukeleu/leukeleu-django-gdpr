import logging
import os
import warnings

# Enable all warnings
warnings.resetwarnings()
# Warn only once per module
warnings.simplefilter("module")
# Redirect warnings output to the logging system
logging.captureWarnings(True)

# Disable all log output, except warnings
LOGGING = {
    "version": 1,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "null": {"class": "logging.NullHandler"},
    },
    "loggers": {
        "": {"handlers": ["null"]},
        "py.warnings": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PACKAGE_DIR)

SECRET_KEY = "django-insecure-test-secret-key"

USE_TZ = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "tests.custom_users",
    "leukeleu_django_gdpr",
]

AUTH_USER_MODEL = "custom_users.CustomUser"
