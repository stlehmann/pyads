"""Script for linting the current project.

:author: Stefan Lehmann <stlm@posteo.de>
:license: MIT, see license file or https://opensource.org/licenses/MIT

:created on 2018-06-28 15:10:47
:last modified by: Stefan Lehmann
:last modified time: 2018-07-13 10:27:58

"""
import click
import subprocess


PACKAGE_NAME = 'pyads'


click.echo('\n--- Running Mypy ---')
res = subprocess.call(['mypy', PACKAGE_NAME])
if res == 0:
    click.echo(click.style('OK', fg='green'))

click.echo('\n--- Running Flake8 ---')
res = subprocess.call(['flake8', PACKAGE_NAME])
if res == 0:
    click.echo(click.style('OK', fg='green'))

click.echo('\n--- Running pydocstyle ---')
res = subprocess.call(['pydocstyle', PACKAGE_NAME])
if res == 0:
    click.echo(click.style('OK', fg='green'))
