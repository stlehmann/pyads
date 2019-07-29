FROM python:3.7
COPY . /pyads
WORKDIR /pyads
RUN python setup.py build
RUN python setup.py develop
CMD python setup.py test
