import uuid
from datetime import datetime

from flask import Flask
from flask_redis import FlaskRedis

from rq import Queue
from rq_scheduler import Scheduler
from latex.worker import redis_conn, QUEUE_NAME

from latex.config import ConfigBase, ProductionConfig
from latex.session import SessionManager, clear_expired_sessions
from latex.services.time_service import TimeService

# Globally accessible instances go here
redis_client = FlaskRedis()
time_service = TimeService()
session_manager = SessionManager(redis_client, time_service)
task_queue = Queue(QUEUE_NAME, connection=redis_conn)


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

    # Set up the internal services
    redis_client.init_app(app)
    time_service.init_app(app)
    session_manager.init_app(app, instance_id)

    # Set up the session cleaning task
    scheduler = Scheduler(QUEUE_NAME, connection=redis_conn)
    scheduler.schedule(
        scheduled_time=datetime.utcnow(),
        func=clear_expired_sessions,
        args=[session_manager.working_directory, session_manager.instance_key],
        interval=app.config["CLEAR_EXPIRED_INTERVAL_SEC"]
    )

    with app.app_context():
        from . import api_routes
    return app


