# Repo Lasso Tests

It's recommended to create a virtual environment for testing:

    [[ -d .venv ]] || virtualenv .venv
    venv/bin/pip install -r requirements.txt
    venv/bin/pip install coverage

To run the tests:

    .venv/bin/python -m coverage run -m unittest discover -v

To generate coverage reports:

    .venv/bin/python -m coverage report
    .venv/bin/python -m coverage html
    .venv/bin/python -m coverage xml
