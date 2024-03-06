# leukeleu-django-gdpr

## Installation

```
pip install leukeleu-django-gdpr
```

Add to INSTALLED_APPS:

```python
INSTALLED_APPS = [
    # ...
    'leukeleu_django_gdpr',
    # ...
]
```

## Configuration

By default, the `gdpr` management command will write `gdpr.yml` to `settings.BASE_DIR`.

To change the output directory (without changing `settings.BASE_DIR`) add
`DJANGO_GDPR_YML_DIR` to your settings:

```python
DJANGO_GDPR_YML_DIR = os.path.join(BASE_DIR, 'docs')
```

## Usage:

On first run, leukeleu-django-gdpr will generate a `gdpr.yml` file with a `models` list. This is
a list of models in your project, each containing a list of fields.

```
./manage.py gdpr
```

A file `gdpr.yml` is created in the project root directory. It should be added to
version control. Each model in the models list has the following structure:

```yaml
models:
  auth.User:
    name: User
    fields:
      username:
        name: Username
        description: String (up to %(max_length)s)
        help_text: Required. 150 characters or fewer. Letters, digits and @/./+/-/_
          only.
        required: true
        pii: null
      first_name:
        name: First Name
        description: String (up to %(max_length)s)
        help_text: ''
        required: false
        pii: null
```

Leukeleu-django-gdpr adds the `pii: null` to all fields. The objective is to replace all those
`null` values with the correct boolean value; `pii: true` if the field represents PII
data, `pii: false` otherwise.

When run again, leukeleu-django-gdpr will persist those values, allowing you to work your way to
eliminating all `pii: null`s.

Leukeleu-django-gdpr outputs counts of the `pii: ` values when run:

```
./manage.py gdpr
Checking...
No PII set     48
PII True       1
PII False      0
```

Run with `--check` to make the command exit with exit code 1 if 'No PII set' > 0 (the
yaml file will still be generated/updated).

You can prevent leukeleu-django-gdpr from writing (back) to the yaml file by running with the
`--dry-run` flag.

## Excluding/including

To exclude apps, models or fields from this process altogether, list them in the
`exclude:` list in the yaml file. Each item is a regex which should match an object's
string representation in the following formats;

* for apps: the app's `label`, e.g. `auth`.
* for models: the model's label, e.g. `auth.Permission`
* for fields: the model's label followed by `.` followed by the field's name, e.g.
  `auth.User.username`.

Keep in mind that the items in the list are considered to be regexes which should
_fully_ match the object's string representation.

### Default excludes

By default, leukeleu-django-gdpr excludes fields of the following types:

*  AutoField
*  UUIDField
*  BooleanField
*  RelatedField

and the following apps:

* django.contrib.admin
* django.contrib.contenttypes

If you still want to include a field/model that would be excluded this way, you can put
an item in the `include:` list in the yaml file:

```
include:
- clients\.Client\.external_epd_uuid
- accounts\.Profile\.is_pregnant
- admin\.LogEntry
```

Proxy models are always excluded. They are the same as the model they proxy,
so there is no benefit in including them.

## Anonymizing data

Leukeleu-django-gdpr comes with a `anonymize` management command, that
anonymizes all PII fields in the database. 

It is meant to be used in development only. It requires an additional 
dependency and setting `DEBUG = True`.

```
pip install leukeleu-django-gdpr[anonymize]
./manage.py anonymize
```

This command uses the `gdpr.yaml` file to anonymize **all fields marked 
as PII** in the database.

To change the configuration, you can create a subclass of `BaseAnonymizer`:

```python
# some_file.py

fake = Faker(["nl-NL"])


class Anonymizer(BaseAnonymizer):
    # Exclude rows
    # Default: superusers and staff users are excluded
    extra_qs_overrides = {
        "app.Model": Model._base_manager.exclude(some_field=...),
        ...
    }

    # Specify fake data for a field
    # Default: user's first_name and last_name are filled with random first/last names
    extra_field_overrides = {
        "app.Model.some_field": fake.word,
        "app.Model.some_other_field": lambda: "same value for every cell",
        ...
    }
    
    # Specify the fake data used for a field type
    # Use for custom fields or to overwrite defaults
    # Default: django builtin fields have "sensible" defaults
    extra_fieldtype_overrides = {
        "CustomPhoneNumberField": fake.phone_number,
      
        # Also specify a unique variant (append with ".unique")
        "CustomPhoneNumberField.unique": fake.unique.phone_number,
        ...
    }

    # Exclude fields
    # Default: no fields are excluded
    excluded_fields = [
        "app.SomeModel.some_field",
        ...
    ]
```

Then add this setting to your settings file:

```python
DJANGO_GDPR_ANONYMIZER_CLASS = "location.to.custom.Anonymizer"
```

## Checks

Leukeleu-django-gdpr adds a `gdpr.I001` check to the `check` command. This check will fail if
there are any `pii: null` values in the yaml file. To run the check, run:

```
./manage.py check
```

## CI/CD

Run the `check` command to make a (scheduled) CI/CD task fail if there are unclassified fields, 
which can happen if someone adds a field to a model but forgets to classify it in the `gdpr.yml`.
