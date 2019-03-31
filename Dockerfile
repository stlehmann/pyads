FROM python:alpine
RUN apk add build-base
COPY . /pyads
WORKDIR /pyads
RUN python setup.py build
RUN python setup.py develop
CMD python setup.py test
