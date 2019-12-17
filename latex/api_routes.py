import json
import uuid

from flask import current_app as app
from latex import redis_client, time_service
from flask import jsonify, url_for, redirect, request
from werkzeug.exceptions import BadRequest


@app.route("/api", methods=["GET"])
def api_home():
    form = {
        "create_session": {
            "href": url_for(get_sessions.__name__),
            "rel": ["create-form"],
            "method": "POST",
            "value": [
                {"name": "compiler", "required": True, "label": "compiler, use 'xelatex' or 'pdflatex'"},
                {"name": "target", "required": True, "label": "main target file to run through the compiler"}
            ]
        }
    }

    return jsonify(form)


@app.route("/api/sessions", methods=["GET", "POST"])
def get_sessions():
    # No session listing is provided, a client must know the session they're trying to access information on in order
    # to access the resource. The session ID is provided to the client when they create the session, so here we just
    # redirect back to the create session form
    if request.method == "GET":
        return redirect(url_for(api_home.__name__))

    # Handle POST
    # The posted data for session creation should follow the format given in the form at the root /api endpoint, and
    # be given through json or form data.
    if not request.is_json or not type(request.json) is dict:
        raise BadRequest("post data must be json dictionary")

    compiler = request.json.get("compiler", None)
    target = request.json.get("target", None)

    if None in (compiler, target):
        raise BadRequest("both compiler and target must be specified")

    # Generate key for new session
    key = str(uuid.uuid4()).replace("-", "")[:12]

    # Create a session and return a unique URL which the client can use to access the resource
    session_data = {
        "compiler": compiler,
        "target": target,
        "creation": time_service.now,
        "href": url_for(session.__name__, session_id=key)
    }

    redis_key = f"session:{key}"
    redis_client.set(redis_key, json.dumps(session_data), ex=5)

    return jsonify(session_data)


@app.route("/api/sessions/<session_id>", methods=["GET", "POST"])
def session(session_id: str):
    # This is the
    return jsonify({"hi": "there"})
