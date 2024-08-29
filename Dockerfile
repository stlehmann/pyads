# This Dockerfile is for running the tests on a windows system where the
# TwinCat router can interfere with the tests. In the first instance tests should be run with tox.

ARG python_version=3.12

# Build python environment and setup pyads
FROM python:${python_version}
COPY . /pyads
WORKDIR /pyads
RUN python -m pip install .

# Test commands
RUN pip install pytest
CMD pytest
