.PHONY: help
help:
	@echo "The following commands are meant to be run inside the python container:"
	@echo
	@echo "  make test - Run lint"
	@echo "  make lint - Check syntax and style"
	@echo "  make lintfix - Automatically fix syntax and style issues"
	@echo "  make build - Build the package"
	@echo

GITHUB_ACTIONS ?= false

# Helper function to define a GitHub Actions group
define group
	@if [ "$(GITHUB_ACTIONS)" = "true" ]; then \
		echo "::group::$1"; \
	fi
endef

.PHONY: test
test: coveragetest

.PHONY: lint
lint:
	# Check syntax and style
	$(call group,Checking syntax and style)
	uv run ruff check
	uv run ruff format --check --diff
	$(call endgroup)

.PHONY: unittests
unittests:
	# Run unit tests with coverage
	uv run coverage run ./runtests.py

.PHONY: coveragetest
coveragetest: unittests
	# Generate coverage report and require minimum coverage
	uv run coverage report

.PHONY: coverage
coverage: unittests
	# Generate test coverage html report
	uv run coverage html
	@echo "Coverage report is located at ./var/htmlcov/index.html"

.PHONY: lintfix
lintfix:
	# Automatically fix syntax and style issues
	uv run ruff check --fix-only
	uv run ruff format

.PHONY: clean
clean:
	# Clean up build files
	$(call group,Cleaning up)
	rm -rf dist/*.whl dist/*.tar.gz
	$(call endgroup)

.PHONY: build
build: clean
	# Build the package
	$(call group,Building package)
	uv build
	$(call endgroup)
