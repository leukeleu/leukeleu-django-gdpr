# django-gdpr

## Installation

```
pip install <this repo url>
```

Add to INSTALLED_APPS:

```!python
INSTALLED_APPS [
    ...
    'gdpr',
    ...
]
```

## Usage:

- Put GDPR.yml in your project's root. Contains 
    - list of regexes of apps, models or fields to ignore.
    - `text:` section containing some prose.
- run: `python manage.py gdpr > GDPR.md`
