#!/bin/bash

if [[ $IS_WORKER == 1 ]]
then
  echo "Setting this container to run a Celery worker"
  cd /var/www/app/ || exit
  exec celery worker -A worker.celery --beat --loglevel="$CELERY_LOG_LEVEL"
else
  echo "Setting this container to run the web service"
  exec python3 /var/www/app/wsgi.py
fi

