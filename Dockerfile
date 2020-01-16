FROM python:slim

ADD requirements.txt /requirements.txt

RUN pip3 install -r /requirements.txt

RUN mkdir /src/
WORKDIR /src/
ADD . /src/

RUN chmod +x /src/script.py
