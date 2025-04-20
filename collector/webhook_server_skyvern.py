import json
from flask import Flask, jsonify, request
from os.path import join, dirname, realpath, exists
import os
import threading
import shutil

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.content_type != "application/json":
        return jsonify({"error": "Invalid content type"}), 400
    try:
        data = request.get_json()
        task_id = data.get("task_id")
        script_dir = dirname(realpath(__file__))
        skyvern_dir = join(
            script_dir, "agents/skyvern/skyvern/artifacts"
        )  # TODO Avoid hardcoding
        task_dir = join(skyvern_dir, task_id)
        if not exists(task_dir):
            return jsonify({"error": "Task directory does not exist"}), 404

        for item in os.listdir(task_dir):
            src_path = join(task_dir, item)
            dest_path = join(app.config["DB_DIRECTORY_PATH"], item)
            if os.path.isfile(src_path):
                with open(src_path, "r") as src_file:
                    content = src_file.read()
                with open(dest_path, "w") as dest_file:
                    dest_file.write(content)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dest_path)

        webhook_file_path = join(app.config["DB_DIRECTORY_PATH"], "webhook.txt")
        with open(webhook_file_path, "w") as f:
            json.dump(data, f, indent=4)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def create_webhook_server(db_directory_path):
    app.config["DB_DIRECTORY_PATH"] = db_directory_path
    server_thread = threading.Thread(
        target=app.run, kwargs={"host": "0.0.0.0", "port": 5001}
    )
    server_thread.daemon = True
    server_thread.start()


if __name__ == "__main__":
    create_webhook_server("./")
