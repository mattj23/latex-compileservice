#!/bin/bash

cd /var/www/app/ || exit

if [[ "$COMPONENT" == "web" ]]; then

  if [[ "$FLASK_ENV" == "production" ]]; then
    echo "Setting this container to run the web service using gunicorn"
    exec gunicorn --bind 0.0.0.0:5000 "latex:create_app()"

  else
    echo "Setting this container to run the development web service using wsgi"
    exec python3 wsgi.py
  fi

elif [[ "$COMPONENT" == "worker" ]]; then
  echo "Setting this container to run a Celery worker"
  exec celery worker -A worker.celery --loglevel="$CELERY_LOG_LEVEL"

elif [[ "$COMPONENT" == "scheduler" ]]; then
  echo "Setting this container to run a Celery beat scheduler"
  exec celery -A scheduler.celery beat --loglevel="$CELERY_LOG_LEVEL"

else
  echo "The contents of the COMPONENT environmental variable ('$COMPONENT') were unrecognized."

fi

