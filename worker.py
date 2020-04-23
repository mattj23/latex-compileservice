import os
from latex import celery, create_app

from celery import Celery
import latex.tasks


if __name__ == '__main__':
    app = create_app(os.getenv("FLASK_CONFIG") or 'default')
    app.app_context().push()
