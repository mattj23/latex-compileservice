import logging
from celery import Celery

import latex.tasks
from latex.config import ConfigBase

celery = Celery(broker=ConfigBase.REDIS_URL, backend=ConfigBase.REDIS_URL)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    logging.info("Setting up periodic tasks")
    logging.info("task frequency = %i sec", int(ConfigBase.CLEAR_EXPIRED_INTERVAL_SEC))
    logging.info("instance key = %s", ConfigBase.INSTANCE_KEY)
    logging.info("working directory = %s", ConfigBase.WORKING_DIRECTORY)

    sender.add_periodic_task(int(ConfigBase.CLEAR_EXPIRED_INTERVAL_SEC),
                             latex.tasks.background_clear_expired.s(ConfigBase.WORKING_DIRECTORY,
                                                                    ConfigBase.INSTANCE_KEY),
                             name="Clear Expired Sessions")

