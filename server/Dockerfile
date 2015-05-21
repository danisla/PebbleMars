# Dockerfile to run either the python scraper or the api.

FROM python:2.7.9

ADD requirements.txt /tmp/

RUN pip install -r /tmp/requirements.txt

WORKDIR /opt/app

ADD *.py /opt/app/

RUN chmod +x /opt/app/*.py

RUN mkdir -p /opt/app/images_raw
RUN mkdir -p /opt/app/images_processed

ENTRYPOINT ["python", "main.py"]
