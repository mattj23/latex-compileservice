FROM ubuntu:bionic

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -qy --no-install-recommends \
    texlive-full \
    python-pygments gnuplot \
    make git python3 python3-pip

COPY requirements.txt ./requirements.txt

RUN python3 -m pip install -r requirements.txt

RUN mkdir /working && \
    mkdir -p /var/www/app

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV CELERY_LOG_LEVEL=info
ENV COMPONENT=web
ENV FLASK_ENV=production

COPY ./ /var/www/app

CMD /var/www/app/run.sh