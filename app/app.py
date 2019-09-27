import os
from session import Session, new_session
import rendering

from flask import Flask, request, redirect, url_for, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from logging.config import dictConfig

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


@app.route("/api/1.0/session/<session_key>", methods=['GET'])
def get_session(session_key: str):
    # Try to find the session ID and retrieve the information
    session = Session(session_key)
    if not session.exists:
        return jsonify({"error": "no session with that key"})

    return jsonify(session.public)


@app.route("/api/1.0/session", methods=["POST"])
def create_session():
    if not request.files:
        return jsonify({"error": "no provided files"})

    compiler = request.form.get("compiler")
    target = request.form.get("target")

    if compiler not in rendering.COMPILERS:
        return jsonify({'error': f"no compiler '{compiler}' supported"})

    # Get the cleaned file names
    cleaned = {secure_filename(file.filename): file for file in request.files.values()}
    if target not in cleaned.keys():
        return jsonify({"error": f"target '{target}' was not one of the files sent"})

    # Create the session working directory
    session = new_session(compiler, target)
    session.create()
    app.logger.info("creating session %s", session.key)

    # Sanitize the file names and store them to the working directory
    for clean_name, file in cleaned.items():
        app.logger.info("file: {}".format(clean_name))
        file.save(os.path.join(session.directory, clean_name))

    # compile to pdf
    result = rendering.render_latex(session)

    with open(result.log, "r") as handle:
        if result.success:
            session.set_product(result.product)
            return jsonify({"success": True, "session_key": session.key, "log": handle.read()})
        else:
            return jsonify({"success": False, "session_key": session.key, "log": handle.read(),
                            "error": "error occurred while rendering"})


@app.route("/api/1.0/product/<session_key>", methods=['GET'])
def get_product(session_key: str):
    session = Session(session_key)
    if not session.product:
        return jsonify({'error': 'no session product found'})

    return send_from_directory(session.directory, session.product, as_attachment=True)


@app.route('/')
def hello_world():
    return "<h1>I'm in a docker container</h1>"


if __name__ == '__main__':
    app.logger.info("hello world, just checking in")
    app.run(host='0.0.0.0')
