import redis
from rq import Worker, Queue, Connection
from latex.config import ConfigBase


QUEUE_NAME = "latex_queue"
listen = [QUEUE_NAME]
redis_conn = redis.from_url(ConfigBase.REDIS_URL)


if __name__ == '__main__':
    with Connection(redis_conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
