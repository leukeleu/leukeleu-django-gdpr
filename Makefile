.PHONY: test flaketest isorttest install-pipeline

test: flaketest isorttest

flaketest:
	# Check syntax and style
	flake8

isorttest:
	# check isort
	isort -rc . -c -w 120 -q --diff

##
# These targets are to be used by BitBucket pipelines
##

install-pipeline:
	pip install -r requirements_local.txt
