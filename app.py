import os

from flask import Flask, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from logging.config import dictConfig
import uuid

working_directory = "/working"

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})
app = Flask(__name__)

@app.route("/session", methods=['GET', "POST"])
def create_session():
    if request.method == "POST":
        if not request.files:
            return jsonify({"error": "no provided files"})

        # Create the session working directory
        session_id = uuid.uuid4()
        app.logger.info("creating session %s", session_id)
        session_directory = os.path.join(working_directory, str(session_id))

        cleaned = []
        for file in request.files.values():
            cleaned_filename = secure_filename(file.filename)
            cleaned.append(cleaned_filename)
            app.logger.info("file: {}".format(file))
            file.save(os.path.join(session_directory, cleaned_filename))


        return jsonify({"session_id": session_id, "files": cleaned})

@app.route('/')
def hello_world():
    return "<h1>I'm in a docker container</h1>"


if __name__ == '__main__':
    app.logger.info("hello world, just checking in")
    app.run(host='0.0.0.0')

