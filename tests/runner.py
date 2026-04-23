import shutil
import tempfile

from django.conf import settings
from django.test.runner import DiscoverRunner


class TestRunner(DiscoverRunner):
    """
    Assumes that the settings.(PRIVATE_)MEDIA_ROOT directories are temporary
    and can be removed after the tests.
    """

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.MEDIA_ROOT = tempfile.mkdtemp()
        settings.PRIVATE_MEDIA_ROOT = tempfile.mkdtemp()

    def teardown_test_environment(self, *args, **kwargs):
        shutil.rmtree(settings.MEDIA_ROOT)
        shutil.rmtree(settings.PRIVATE_MEDIA_ROOT)
        super().teardown_test_environment(*args, **kwargs)
