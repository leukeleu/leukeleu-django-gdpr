from setuptools import find_packages, setup

setup(
    name="django-gdpr",
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    zip_safe=False,
    url="https://bitbucket.org/leukeleu/django-gdpr/",
    author="Wouter de Vries (Leukeleu)",
    author_email="wdevries@leukeleu.nl",
    maintainer="Leukeleu",
    maintainer_email="info@leukeleu.nl",
    description="Django GDPR",
    long_description="Django Gee-dee-pee-arr",
    keywords=["gdpr", "django"],
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
    ],
    license="Proprietary",
    install_requires=["pyyaml"],
)
