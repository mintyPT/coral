# Define the environment variable for the Python version manager
runner = uv run 

# Define the path to the pyproject.toml file (this is the default location)
PYPROJECT_TOML = pyproject.toml

# Define the default command for installing dependencies
install:
	$(runner) install

# Define the command for running tests with pytest
test:
	$(runner) pytest -vv

# Define the command for running ruff (formatter)
format:
	$(runner) ruff format .

# Define the command for running ruff (linting)
lint:
	$(runner) ruff check . --fix

# Define the command for running mypy (type checking)
type-check:
	$(runner) mypy --cache-fine-grained .

# Define a command to run all checks (linting, type-checking, and tests)
check: format lint type-check test

# Define the default target (what should happen if 'make' is run without any arguments)
.DEFAULT_GOAL := check