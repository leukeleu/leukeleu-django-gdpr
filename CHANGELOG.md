History
-------

* 1.4.0 (2022-12-22)

  * Updated include/exclude logic. Includes now take precedence over excludes.
  * django.contrib.admin models are now excluded by default.
  * Inherited fields are now identified as the ChildModel.field_name instead of the ParentModel.field_name.
    This means it's possible to include/exclude inherited fields by using the ChildModel.field_name.

* 1.3.1 (2022-12-08)
  
  * Fix serialization of SafeString values

* 1.3.0 (2022-12-08)

  * Add an option to override gdpr.yml output directory
  * Omit proxy models
  * Removed support for Bitbucket Pipelines reporting

* 1.2.1 (2022-11-30)

  * Remove default app config (deprecated in Django 3.2)

* 1.2.0 (2022-10-11)

  * Convert check level from warning to info

* 1.1.1 (2022-10-06)

  * Remove tests from distribution

* 1.1.0 (2022-09-28)

  * Integrate with Django's `check` command

* 1.0.2 (2022-09-16)

  * Fix missing dependency on pyyaml

* 1.0.1 (2022-09-16)

  * Fix missing dependency on requests

* 1.0.0 (2022-09-16)

  * Initial public release as leukeleu-django-gdpr
