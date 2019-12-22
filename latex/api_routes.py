import os

from flask import current_app as app
from latex import session_manager
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

    session_handle = session_manager.create_session(compiler, target)

    created_location = url_for(session.__name__, session_id=session_handle.key)
    return jsonify(session_handle.public), 201, {"location": created_location}


@app.route("/api/sessions/<session_id>", methods=["GET", "POST"])
def session(session_id: str):
    # Retrieve the session information
    handle = session_manager.load_session(session_id)
    if handle is None:
        return BadRequest(f"session {session_id} could not be found")

    # On a get request, we simply return the session information as we have it
    if request.method == "GET":
        return jsonify(handle.public)

    # A post request allows additional information to be added to the session
    if request.method == "POST":
        return jsonify({"hi": "there"})


@app.route("/api/sessions/<session_id>/files", methods=["GET", "POST"])
def session_files(session_id: str):
    # Retrieve the session information
    handle = session_manager.load_session(session_id)
    if handle is None:
        return BadRequest(f"session {session_id} could not be found")

    # On a get request, we simply return the session information as we have it
    if request.method == "GET":
        return jsonify(handle.public["files"])

    # A post request allows files to be added to the session
    if request.method == "POST":
        for name, file_item in request.files.items():
            target_path = os.path.join(handle.source_directory, file_item.filename)
