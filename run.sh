#!/bin/bash

if [[ "$COMPONENT" == "web" ]]; then

  echo "Setting this container to run the web service"
  exec python3 /var/www/app/wsgi.py

elif [[ "$COMPONENT" == "worker" ]]; then

  echo "Setting this container to run a Celery worker"
  cd /var/www/app/ || exit
  exec celery worker -A worker.celery --loglevel="$CELERY_LOG_LEVEL"

elif [[ "$COMPONENT" == "scheduler" ]]; then

  echo "Setting this container to run a Celery beat scheduler"
  cd /var/www/app/ || exit
  exec celery -A scheduler.celery beat --loglevel="$CELERY_LOG_LEVEL"

else
  echo "The contents of the COMPONENT environmental variable ('$COMPONENT') were unrecognized."

fi

