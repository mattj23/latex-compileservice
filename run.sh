#!/bin/bash

if [[ $IS_WORKER == 1 ]]
then
  echo "Setting this container to run a RQ worker"
  pwd
  exec python3 /var/www/app/worker.py
else
  echo "Setting this container to run the web service"
  exec python3 /var/www/app/wsgi.py
fi

