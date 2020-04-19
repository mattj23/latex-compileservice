import json

from flask import current_app as app
from flask import jsonify, url_for, redirect, request
from werkzeug.exceptions import BadRequest

from latex import session_manager, task_queue
from latex.rendering import render_latex

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

    created_location = url_for(session_root.__name__, session_id=session_handle.key)
    return jsonify(session_handle.public), 201, {"location": created_location}


@app.route("/api/sessions/<session_id>", methods=["GET", "POST"])
def session_root(session_id: str):
    # Retrieve the session information
    handle = session_manager.load_session(session_id)
    if handle is None:
        return BadRequest(f"session {session_id} could not be found")

    # On a get request, we simply return the session information as we have it
    if request.method == "GET":
        response = dict(handle.public)
        form_info = {
            "add_file": {
                "href": url_for(session_files.__name__, session_id=session_id),
                "rel": ["create-form"],
                "method": "POST",
                "value": [
                    {"label": "upload file(s) with multipart/form-data, filename is used to specify path"}
                ]
            },
            "add_templates": {
                "href": url_for(session_templates.__name__, session_id=session_id),
                "rel": ["create-form"],
                "method": "POST",
                "value": [
                    {"name": "target", "required": True, "label": "target path/filename to render the template to"},
                    {"name": "text", "required": True, "label": "latex text to be rendered by jinja2"},
                    {"name": "data", "required": True, "label": "json dictionary to be rendered into the template"}
                ]
            },
            "finalize": {
                "href": url_for(session_root.__name__, session_id=session_id),
                "rel": ["edit-form"],
                "method": "POST",
                "value": [
                    {"name": "finalize", "required": False,
                     "label": "set true to finalize the session and release it to the compiler"}
                ]
            }
        }
        response.update(form_info)
        return jsonify(response)

    # A post request allows additional information to be added to the session
    if request.method == "POST":
        # Handle JSON data posted
        if request.is_json and isinstance(request.json, dict):

            # Session finalization
            if request.json.get("finalize", False) == True:
                handle.finalize()
                args = (handle.key, session_manager.working_directory, session_manager.instance_key)
                job = task_queue.enqueue_call(func=render_latex, args=args)

        return jsonify({"hi": "there"})


@app.route("/api/sessions/<session_id>/files", methods=["GET", "POST"])
def session_files(session_id: str):
    # Retrieve the session information
    session = session_manager.load_session(session_id)
    if session is None:
        return BadRequest(f"session {session_id} could not be found")

    # On a get request, we simply return the session information as we have it
    if request.method == "GET":
        return jsonify(session.public["files"])

    # A post request allows files to be added to the session
    if request.method == "POST":
        for name, file_item in request.files.items():
            with session.source_files.open(file_item.filename, "wb") as handle:
                file_item.save(handle)

        return jsonify(session.public["files"]), 201


@app.route("/api/sessions/<session_id>/templates", methods=["GET", "POST"])
def session_templates(session_id: str):
    # Retrieve the session information
    session = session_manager.load_session(session_id)
    if session is None:
        return BadRequest(f"session {session_id} could not be found")

    # On a get request, we simply return the session information as we have it
    if request.method == "GET":
        return jsonify(session.public["templates"])

    # A post request allows files to be added to the session
    if request.method == "POST":
        if not request.is_json or not type(request.json) is dict:
            raise BadRequest("post data must be json dictionary")

        text = request.json.get("text", None)
        target = request.json.get("target", None)
        data = request.json.get("data")

        if text is None or type(text) is not str:
            raise BadRequest("Field 'text' must be supplied and be a valid string")

        if target is None or type(target) is not str:
            raise BadRequest("Field 'target' must be supplied and be a valid string")

        if data is None or type(data) is not dict:
            raise BadRequest("Field 'data' must be supplied and be a valid dictionary")

        with session.template_files.open(target, "w") as handle:
            handle.write(json.dumps({"text": text, "target": target, "data": data}))

        return jsonify(session.public["templates"]), 201
