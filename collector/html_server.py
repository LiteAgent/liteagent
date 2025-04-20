import os
import sys

from flask import Flask, abort, send_from_directory

from utils import logger

app = Flask(__name__, static_url_path="")

# Get the directory from the command-line argument
if len(sys.argv) != 2:
    logger.error("Invalid arguments! Usage: flask_server.py <webpage_directory>")
    sys.exit(1)

webpage_directory = os.path.abspath(sys.argv[1])


@app.route("/")
def serve_index():
    try:
        return send_from_directory(webpage_directory, "index.html")
    except FileNotFoundError:
        abort(404)


@app.route("/<path:filename>")
def serve_file(filename):
    try:
        return send_from_directory(webpage_directory, filename)
    except FileNotFoundError:
        abort(404)


if __name__ == "__main__":
    app.run(port=5001, debug=True)
