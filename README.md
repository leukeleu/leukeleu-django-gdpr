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

* for apps: the app's `label`, such as `admin` or `auth`.
* for models: the model's label, such as `admin.LogEntry` or `auth.Permission`
* for fields: the model's label followed by `.` followed by the field's name, such as
  `auth.User.username`.
  
Keep in mind that the items in the list are considered to be regexes which should 
_fully_ match the object's string representation. 

### Default excludes

By default, leukeleu-django-gdpr excludes fields of the following types:

*  AutoField
*  UUIDField
*  BooleanField
*  RelatedField

and the following models:

* ContentType

If you still want to include a field/model that would be excluded this way, you can put
an item in the `include:` list in the yaml file:

```
include:
- clients\.Client\.external_epd_uuid
- accounts\.Profile\.is_pregnant
```

## Checks

Leukeleu-django-gdpr adds a `gdpr.W001` check to the `check` command. This check will fail if
there are any `pii: null` values in the yaml file. To run the check, run:

```
./manage.py check
```

## Pipelines

To run this in Bitbucket Pipelines you need to ensure this package can be installed from
wherever this package is indexed. Run it with `--check` to make a (scheduled?) pipeline
fail if there are unclassified fields, which can happen if someone adds a field to a model
but forgets to mark it as (non-) PII in the gdpr.yml.

### Reports

When run from a Bitbucket Pipeline, leukeleu-django-gdpr can send the PII stats as a report to
Bitbucket. This will be visible in Pull Requests and Pipelines. Run with 
`--report-pipeline` to enable it.
