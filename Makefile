.PHONY: test flaketest isorttest

test: flaketest isorttest coveragetest

devinstall:
	pip install --upgrade --upgrade-strategy eager -e .[test]

flaketest:
	# Check syntax and style
	flake8

unittests:
	# Run unit tests with coverage
	coverage run runtests.py

coveragetest: unittests
	# Generate coverage report and require minimum coverage
	coverage report

isorttest:
	# check isort
	isort . -c -w 120 -q --diff
