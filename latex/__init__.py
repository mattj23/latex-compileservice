import os
from flask import Flask
from flask_redis import FlaskRedis
from latex.config import ConfigBase, ProductionConfig

from latex.time_service import TimeService

# Globally accessible instances go here
redis_client = FlaskRedis()
time_service = TimeService()


# Application factory method
def create_app(config_data: ConfigBase = None) -> Flask:
    """
    Factory method for creating the Flask instance, allows a special configuration for
    unit testing to be injected in
    """
    app = Flask(__name__, instance_relative_config=True)

    if config_data is None:
        app.config.from_object(ProductionConfig())
    else:
        app.config.from_object(config_data)

    # Set up the internal services
    redis_client.init_app(app)
    time_service.init_app(app)

    with app.app_context():
        from . import api_routes
    return app


