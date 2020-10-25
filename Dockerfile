# This Dockerfile is for running the tests on a windows system where the
# TwinCat router can interfere with the tests. In the first instance tests should be run with tox.

ARG python_version=3.8

# Build python environment and setup pyads
FROM python:${python_version}
COPY . /pyads
WORKDIR /pyads
RUN python setup.py build
RUN python setup.py develop

# Test commands
RUN pip install pytest
CMD pytest
