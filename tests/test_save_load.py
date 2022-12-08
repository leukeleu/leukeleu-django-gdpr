import shutil
import tempfile

from django.test import TestCase

from leukeleu_django_gdpr.gdpr import Serializer, get_gdpr_yml_path, read_data


class TestSerializerDataRoundTrip(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir)

    def test_load_serializer_data(self):
        with self.settings(DJANGO_GDPR_YML_DIR=self.tmp_dir):
            serializer = Serializer()
            serializer.generate_models_list()
            with open(get_gdpr_yml_path(), "w") as f:
                serializer.save(f)

            self.assertEqual(serializer.models, read_data().get("models"))
