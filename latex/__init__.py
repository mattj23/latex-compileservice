import os
import uuid
from datetime import datetime

from flask import Flask
from flask_redis import FlaskRedis
from celery import Celery

from latex.config import ConfigBase, ProductionConfig
from latex.session import SessionManager, clear_expired_sessions
from latex.services.time_service import TimeService

import logging
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

# Globally accessible instances go here
celery = Celery(__name__, backend=ConfigBase.REDIS_URL, broker=ConfigBase.REDIS_URL)
redis_client = FlaskRedis()
time_service = TimeService()
session_manager = SessionManager(redis_client, time_service)


# Application factory method
def create_app(config_data: ConfigBase = None) -> Flask:
    """
    Factory method for creating the Flask instance, allows a special configuration for
    unit testing to be injected in
    """
    instance_id = str(uuid.uuid4()).replace("-", "")[:10]

    app = Flask(__name__, instance_relative_config=True)

    if config_data is None:
        app.config.from_object(ProductionConfig())
    else:
        app.config.from_object(config_data)

    celery.conf.update(app.config)

    logging.info(f"Creating new app with instance_id={instance_id}")

    # Write the environmental variables out to the log
    env_output = ["Current environmental variables:"]
    for k, v in app.config.items():
        env_output.append(f"  - {k}={v}")
    logging.info("\n".join(env_output))

    # Set up the internal services
    redis_client.init_app(app)
    time_service.init_app(app)
    session_manager.init_app(app, instance_id)

    with app.app_context():
        from . import api_routes
    return app


