import os
from latex import celery, create_app
from latex.config import ConfigBase

from celery import Celery
import latex.tasks
import logging


@celery.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    logging.info("Setting up periodic tasks")
    logging.info("instance key = %s", ConfigBase.INSTANCE_KEY)
    logging.info("working directory = %s", ConfigBase.WORKING_DIRECTORY)

    sender.add_periodic_task(60.0,
                             latex.tasks.background_clear_expired.s(ConfigBase.WORKING_DIRECTORY,
                                                                    ConfigBase.INSTANCE_KEY),
                             name="test-scheduled")


if __name__ == '__main__':
    app = create_app(os.getenv("FLASK_CONFIG") or 'default')
    app.app_context().push()
