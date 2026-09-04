from flask import Flask, jsonify, request
from pathlib import Path
import json

from automation.network_manager import load_device_configs

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configuration"


@app.route("/devices", methods=["GET"])
def get_devices():
    devices = load_device_configs()
    return jsonify(devices)


@app.route("/devices/<hostname>", methods=["GET"])
def get_device(hostname):
    devices = load_device_configs()

    for device in devices:
        if device.get("hostname") == hostname:
            return jsonify(device)

    return jsonify({"error": "Device not found"}), 404


@app.route("/devices", methods=["POST"])
def create_device():
    new_device = request.get_json()

    if not new_device:
        return jsonify({"error": "JSON body is required"}), 400

    hostname = new_device.get("hostname")

    if not hostname:
        return jsonify({"error": "Hostname is required"}), 400

    devices = load_device_configs()

    for device in devices:
        if device.get("hostname") == hostname:
            return jsonify({"error": "Device already exists"}), 409

    output_file = CONFIG_DIR / f"{hostname.lower()}.json"

    with open(output_file, "w") as file:
        json.dump(new_device, file, indent=4)

    return jsonify(new_device), 201


if __name__ == "__main__":
    app.run(debug=True)