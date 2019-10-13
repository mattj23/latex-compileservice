import os
from flask import Flask
from latex.config import ConfigBase, ProductionConfig

# Globally accessible instances go here


# Application factory method
def create_app(config: ConfigBase = None) -> Flask:
    """
    Factory method for creating the Flask instance, allows a special configuration for
    unit testing to be injected in
    """
    app = Flask(__name__, instance_relative_config=True)

    if config is None:
        app.config.from_object(ProductionConfig())
    else:
        app.config.from_object(config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    with app.app_context():
        from . import api_routes
    return app


