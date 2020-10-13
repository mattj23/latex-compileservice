import json
from hashlib import md5

from flask import current_app as app
from flask import jsonify, url_for, redirect, request, Response, send_file
from werkzeug.exceptions import BadRequest, NotFound

from latex import session_manager
from latex.services.time_service import TimeService
from latex.tasks import background_run_compile
from latex.session import validate_conversion_data


@app.route("/api", methods=["GET"])
def api_home():
    form = {
        "create_session": {
            "href": url_for(get_sessions.__name__),
            "rel": ["create-form"],
            "method": "POST",
            "value": [
                {"name": "compiler", "required": True, "label": "compiler, use 'xelatex', 'pdflatex', or 'lualatex'"},
                {"name": "convert", "required": False, "label": "convert to image, can be none, or {'format': 'jpeg', "
                                                                "'dpi': 300} where format is 'jpeg', 'tiff', or 'png'"},
                {"name": "target", "required": True, "label": "main target file to run through the compiler"}
            ]
        }
    }

    return jsonify(form)


@app.route("/api/status", methods=['GET'])
def get_status():
    session_ids = session_manager.get_all_session_ids()
    sessions = {}
    for key in session_ids:
        session = session_manager.load_session(key)
        if session.status not in sessions.keys():
            sessions[session.status] = 1
        else:
            sessions[session.status] += 1

    return jsonify({"time": TimeService().now, "sessions": sessions})


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

    if "convert" in request.json:
        try:
            convert = validate_conversion_data(request.json["convert"])
        except ValueError as e:
            return BadRequest(e.args[0])
    else:
        convert = None

    session_handle = session_manager.create_session(compiler, target, convert)

    created_location = url_for(session_root.__name__, session_id=session_handle.key)
    return jsonify(session_handle.public), 201, {"location": created_location}


@app.route("/api/sessions/<session_id>/product", methods=["GET"])
def session_product(session_id: str):
    handle = session_manager.load_session(session_id)
    if handle is None:
        return BadRequest(f"session {session_id} could not be found")

    if handle.product is None:
        return NotFound()

    return send_file(handle.product)


@app.route("/api/sessions/<session_id>/log", methods=["GET"])
def session_log(session_id: str):
    handle = session_manager.load_session(session_id)
    if handle is None:
        return BadRequest(f"session {session_id} could not be found")

    if handle.log is None:
        return NotFound()

    return send_file(handle.log)


@app.route("/api/sessions/<session_id>", methods=["GET", "POST"])
def session_root(session_id: str):
    # Retrieve the session information
    handle = session_manager.load_session(session_id)
    if handle is None:
        return BadRequest(f"session {session_id} could not be found")

    # On a get request, we simply return the session information as we have it
    if request.method == "GET":
        # The base response is the public session data
        response = dict(handle.public)

        # If the session has a log or a product, we include a link to it
        if handle.product is not None:
            response['product'] = {"href": url_for(session_product.__name__, session_id=session_id)}
        if handle.log is not None:
            response['log'] = {"href": url_for(session_log.__name__, session_id=session_id)}

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

            # Check that the session isn't locked already
            if not handle.is_editable:
                return jsonify({"error": "session is not editable"}), 403

            # Check if conversion data has been supplied
            if "convert" in request.json:
                try:
                    handle.convert = validate_conversion_data(request.json["convert"])
                    session_manager.save_session(handle)
                except ValueError as e:
                    return BadRequest(e.args[0])

            # Session finalization
            if request.json.get("finalize", False):
                handle.finalize()

                args = (handle.key, session_manager.working_directory, session_manager.instance_key)
                if app.config["TESTING"]:
                    return jsonify(args)
                else:
                    task = background_run_compile.delay(*args)
                    return jsonify(handle.public), 202

        return BadRequest("POST data not understood")


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
        if not handle.is_editable:
            return jsonify({"error": "session is not editable"}), 403
        for name, file_item in request.files.items():
            with handle.source_files.open(file_item.filename, "wb") as file_handle:
                file_item.save(file_handle)

        return jsonify(handle.public["files"]), 201


@app.route("/api/sessions/<session_id>/templates", methods=["GET", "POST"])
def session_templates(session_id: str):
    # Retrieve the session information
    handle = session_manager.load_session(session_id)
    if handle is None:
        return BadRequest(f"session {session_id} could not be found")

    # On a get request, we simply return the session information as we have it
    if request.method == "GET":
        return jsonify(handle.public["templates"])

    # A post request allows files to be added to the session
    if request.method == "POST":
        if not request.is_json or not type(request.json) is dict:
            raise BadRequest("post data must be json dictionary")

        if not handle.is_editable:
            return jsonify({"error": "session is not editable"}), 403

        text = request.json.get("text", None)
        target = request.json.get("target", None)
        data = request.json.get("data")

        if text is None or type(text) is not str:
            raise BadRequest("Field 'text' must be supplied and be a valid string")

        if target is None or type(target) is not str:
            raise BadRequest("Field 'target' must be supplied and be a valid string")

        if data is None or type(data) is not dict:
            raise BadRequest("Field 'data' must be supplied and be a valid dictionary")

        md = md5(target.encode())
        with handle.template_files.open(md.hexdigest(), "w") as file_handle:
            file_handle.write(json.dumps({"text": text, "target": target, "data": data}))

        return jsonify(handle.public["templates"]), 201
