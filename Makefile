.PHONY: test flaketest isorttest install-pipeline

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

clean:
	# Remove build/dist dirs
	rm -rf build dist

build: test clean
	# Test, clean and build
	python setup.py build sdist bdist_wheel

devrelease: build
	# Build and upload to devpi staging
	twine upload -r devpi --repository-url https://devpi.leukeleu.nl/leukeleu/dev/ dist/*

release: build
	# Build and upload to devpi live
	twine upload -r devpi --repository-url https://devpi.leukeleu.nl/leukeleu/prod/ dist/*

##
# These targets are to be used by BitBucket pipelines
##

install-pipeline:
	pip install -r requirements_local.txt
