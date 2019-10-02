# Contributing to pyads

Please follow these guidelines for contributing. Pull requests are welcome.

## Basic requirements

- Create a new [github issue](https://github.com/stlehmann/pyads/issues) for bugs
  or features. Search the ticket system first, to avoid filing a duplicate.
- Ensure code follows the [syntax and conventions](#Syntax-and-conventions).
- Code must pass tests. See [Testing](#Testing) for information on how to run and
 write unit tests.
- Commit messages should be informative.

## Pull request process:

- Fork us on [github](https://github.com/stlehmann/pyads).
- Clone your repository.
- Create a feature branch for your issue.
- Apply your changes:
  - Add them, and then commit them to your branch.
  - Run the tests until they pass.
  - When you feel you are finished, rebase your commits to ensure a simple
    and informative commit log.
- Create a pull request on github from your forked repository.

## Syntax and conventions

### Code formatting tools

Use [Black](https://github.com/psf/black) for formatting Python code.
Simply run `black <filename>` from the command line.

### Connection class
  
There is currently functions inside the `ads.py` file which seem duplicated
by methods inside the `Connection` class. Functions duplicated outside of the
class are for backwards compatibility. 

The `Connection` class`is the recommended way for users of pyads to interact
with a PLC:

    plc = pyads.Connection('127.0.0.1.1.1', pyads.PORT_SPS1)

New features should therefore focus on adding to the `Connection` class`.
Depreciation of duplicate functions is under ongoing review.

### Docstrings

Please use the [Python domain info field lists](https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html?highlight=%3Areturn%3A#info-field-lists)
for all docstrings. This way documentation can be auto-generated from docstrings.

example:

    def func(foo, bar):
       """Function purpose.

        :param int foo: description and type of the foo argument
        :param bar: description of the bar argument 
        :type bar: int

        :return: return description
        :rtype: int
       """
       return foo * bar
    
## Testing

The tests are located `tests` folder. Tests should be included for any new contributions.

### Tox

All the tests for pyads can be run using [tox](https://pypi.python.org/pypi/tox).
Simply use `pip install tox` and run `tox` from the root directory. See `tox.ini`
for available environments.

### unittest

Tests are written using [unittest](https://docs.python.org/3/library/unittest.html)
and can be individually run for each environment with the python built in library.

### Travis-CI

When creating a pull request (PR) on [Github], [Travis] will automatically run
the unit tests with the code in the PR and report back.

[Github]: https://github.com/stlehmann/pyads/pulls
[Travis]: https://travis-ci.org/stlehmann/pyads

## Documentation contributions

Sphinx is used to create the documentation from source files and docstrings in code.
You can build your documentation changes for testing using:

    pip install -r requirements.txt
    cd doc
    make html

The resulting html files are in `doc/build/html`.

Documentation is found on [read the docs](https://pyads.readthedocs.io/en/latest/)
and will automatically update when PRs are merged.

## Python 2
pyads is still supporting Python 2.7, please make contributions backwards compatible.
Support for Python 2.7 is under ongoing review.