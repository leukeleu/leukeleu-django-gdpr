#!/usr/bin/env python
import os
import sys


def runtests():
    os.environ["DJANGO_SETTINGS_MODULE"] = "tests.test_settings"
    from django.core.management import execute_from_command_line

    argv = [sys.argv[0], "test", *sys.argv[1:]]
    execute_from_command_line(argv)


if __name__ == "__main__":
    runtests()
