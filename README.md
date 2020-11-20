# django-gdpr

## Installation

```
pip install django-gdpr -i devpi.leukeleu.nl
```

Add to INSTALLED_APPS:

```python
INSTALLED_APPS = [
    # ...
    'gdpr',
    # ...
]
```

## Usage:

- Put GDPR.yml in your project's root. Contains 
    - list of regexes of apps, models or fields to ignore.
- run: `python manage.py gdpr --check`
