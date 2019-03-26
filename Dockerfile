FROM python:alpine
RUN apk add build-base
COPY . /pyads
WORKDIR /pyads
RUN cd src ; make clean ; make ; cd .. ; cp src/*.so pyads
RUN python setup.py develop
CMD python setup.py test
