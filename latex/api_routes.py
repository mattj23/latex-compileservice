from flask import current_app as app
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
    if request.method == "GET":
        return redirect(url_for(api_home.__name__))

    # Handle POST
    if not request.is_json or not type(request.json) is dict:
        raise BadRequest("post data must be json dictionary")

    compiler = request.json.get("compiler", None)
    target = request.json.get("target", None)

    if None in (compiler, target):
        raise BadRequest("both compiler and target must be specified")

    # Create a session and return a unique URL
    session_data = {
        "compiler": compiler,
        "target": target,
        "href": url_for(session.__name__, session_id="h23o234")
    }

    return jsonify(session_data)


@app.route("/api/sessions/<session_id>", methods=["GET", "POST"])
def session(session_id: str):
    return jsonify({"hi": "there"})
