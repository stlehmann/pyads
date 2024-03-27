# Contributing to pyads

Please follow these guidelines for contributing. Pull requests are welcome.

## Basic requirements

- Create a new [github issue](https://github.com/stlehmann/pyads/issues) for bugs
  or features. Search the ticket system first, to avoid filing a duplicate.
- Ensure code follows the [Syntax and conventions](#Syntax-and-conventions).
- Code must pass tests. See [Testing](#Testing) for information on how to run and
 write unit tests.
- Commit messages should be informative.
- Use the [Pull request process](#Pull-request-process).
- Address only one issue per PR. If you want to make additional fixes e.g. on import statements, style or documentation 
which are not directly related to your issue please create an additional PR that addresses these small fixes.

## Pull request process

- Fork us on [github](https://github.com/stlehmann/pyads).
- Clone your repository.
- Create a feature branch for your issue.
- Keep PRs small (if possible), this makes reviews easier and your PR can be merged faster.
- Apply your changes:
  - Add them, and then commit them to your branch.
  - Run the tests until they pass.
  - When you feel you are finished, rebase your commits to ensure a simple
    and informative commit log.
  - Add an entry to the [Changelog](https://github.com/stlehmann/pyads/blob/master/CHANGELOG.md).
- Create a pull request on github from your forked repository.

## Syntax and conventions

### Code formatting tools

Use [Black](https://github.com/psf/black) for formatting Python code.
Simply run `black <filename>` from the command line.

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

### CI

When creating a pull request (PR) on [Github], Github CI will automatically run
the unit tests with the code in the PR and report back.

[Github]: https://github.com/stlehmann/pyads/pulls

### Testing issues on Windows

There are known issues when running tests using a Windows development environment with
TwinCat installed; TwinCat can cause issues with the ADS Test Server. If running tests
using tox causes problems, tests can be run using Docker instead.

To run the tests on Windows with TwinCAT installed, make sure TwinCAT is not running. 
Either stop all services and process manually, or run 
`C:\TwinCAT\TcSwitchRuntime\TcSwitchRuntime.exe` and click 'disable'.

#### Docker

With Docker installed docker images can be built and run for any python version.
The following commands will build an image using python3.8, then tests will run when the
container starts:

```
docker build --build-arg python_version=3.8 -t container_name .
docker run --rm container_name
```

The container is deleted automatically after running so that multiple containers don't
build up on the system. To rerun the tests after making changes to pyads, any docker images
will need to be rebuilt.

### Linux Subsystem

Instead of using Docker, the Linux Subsystem for Windows also allows you to run the tests. 
See for example: https://docs.microsoft.com/en-us/windows/wsl/install-win10

With the subsystem installed, open a Linux shell in your clone directory and run:

1. `sudo apt install python3 python3-pip`
1. `cd adslib && make && sudo make install && cd ..`
1. `python3 -m pip install tox`
1. `python3 -m tox -e py38` (Ubuntu 20.04 with Python 3.8)

## Documentation contributions

Sphinx is used to create the documentation from source files and docstrings in code.
You can build your documentation changes for testing using:

    pip install -r requirements.txt
    cd doc
    make html

The resulting html files are in `doc/build/html`.

Documentation is found on [read the docs](https://pyads.readthedocs.io/en/latest/)
and will automatically update when PRs are merged.