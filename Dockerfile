FROM ubuntu:bionic

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -qy --no-install-recommends \
    texlive-full \
    python-pygments gnuplot \
    make git

COPY requirements.txt ./requirements.txt

RUN apt-get install python3 python3-pip -y && \
    python3 -m pip install -r requirements.txt

RUN mkdir /working && \
    mkdir -p /var/www/app

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

COPY ./ /var/www/app

CMD ["python3", "/var/www/app/wsgi.py"]