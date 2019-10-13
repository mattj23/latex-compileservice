from flask import current_app as app
from flask import jsonify


@app.route("/api/sessions", methods=['GET'])
def get_sessions():
    return jsonify({"hi": "hi there!"})

