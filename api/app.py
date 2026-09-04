from flask import Flask, jsonify, request
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
import ipaddress
import json
import logging
import os
import yaml

from automation.network_manager import load_device_configs


load_dotenv()

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configuration"

API_KEY = os.getenv("API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

def require_api_key(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        supplied_key = request.headers.get("X-API-Key")

        if not API_KEY:
            logger.error("API_KEY environment variable is not configured")

            return jsonify({
                "error": "Server authentication is not configured"
            }), 500

        if supplied_key != API_KEY:
            logger.warning(
                "Unauthorised request to %s",
                request.path
            )

            return jsonify({
                "error": "Unauthorised"
            }), 401

        return function(*args, **kwargs)

    return decorated_function

def load_config_file(file_path):
    with open(file_path, "r") as file:
        if file_path.suffix == ".json":
            return json.load(file)

        if file_path.suffix in [".yaml", ".yml"]:
            return yaml.safe_load(file)

    return None


def save_config_file(file_path, device):
    with open(file_path, "w") as file:
        if file_path.suffix == ".json":
            json.dump(device, file, indent=4)

        elif file_path.suffix in [".yaml", ".yml"]:
            yaml.safe_dump(
                device,
                file,
                sort_keys=False
            )


def find_device_file(hostname):
    extensions = ["*.json", "*.yaml", "*.yml"]

    for extension in extensions:
        for file_path in CONFIG_DIR.rglob(extension):
            device = load_config_file(file_path)

            if (
                isinstance(device, dict)
                and device.get("hostname") == hostname
            ):
                return file_path, device

    return None, None

def validate_device(device, require_all_fields=True):
    errors = []

    if not isinstance(device, dict):
        return ["Request body must contain a JSON object"]

    if require_all_fields:
        required_fields = [
            "hostname",
            "ip_address"
        ]

        for field in required_fields:
            if not device.get(field):
                errors.append(
                    f"{field} is required"
                )

    hostname = device.get("hostname")

    if hostname is not None:
        if not isinstance(hostname, str):
            errors.append(
                "hostname must be a string"
            )

        elif not hostname.strip():
            errors.append(
                "hostname cannot be empty"
            )

    ip_address_value = device.get("ip_address")

    if ip_address_value:
        try:
            ipaddress.ip_address(ip_address_value)

        except ValueError:
            errors.append(
                "ip_address must be a valid IPv4 or IPv6 address"
            )

    return errors


def validate_environment(environment):
    valid_environments = {
        "office": "office_topology",
        "home": "home_topology",
        "cloud": "cloud"
    }

    return valid_environments.get(environment)

@app.route("/devices", methods=["GET"])
@require_api_key
def get_devices():
    devices = load_device_configs()

    logger.info(
        "Retrieved %s network devices",
        len(devices)
    )

    return jsonify(devices), 200

@app.route("/devices/<hostname>", methods=["GET"])
@require_api_key
def get_device(hostname):
    file_path, device = find_device_file(hostname)

    if device is None:
        logger.warning(
            "Device not found: %s",
            hostname
        )

        return jsonify({
            "error": "Device not found"
        }), 404

    logger.info(
        "Retrieved device: %s",
        hostname
    )

    return jsonify(device), 200

@app.route("/devices", methods=["POST"])
@require_api_key
def create_device():
    new_device = request.get_json(silent=True)

    if new_device is None:
        return jsonify({
            "error": "Valid JSON body is required"
        }), 400

    environment = new_device.pop(
        "environment",
        None
    )

    folder_name = validate_environment(environment)

    if folder_name is None:
        return jsonify({
            "error":
                "environment must be office, home or cloud"
        }), 400

    validation_errors = validate_device(new_device)

    if validation_errors:
        return jsonify({
            "errors": validation_errors
        }), 400

    hostname = new_device["hostname"]

    existing_file, existing_device = (
        find_device_file(hostname)
    )

    if existing_device is not None:
        return jsonify({
            "error": "Device already exists"
        }), 409

    target_directory = CONFIG_DIR / folder_name

    target_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        target_directory
        / f"{hostname.lower().replace(' ', '_')}.json"
    )

    save_config_file(
        output_file,
        new_device
    )

    logger.info(
        "Created device: %s in %s",
        hostname,
        environment
    )

    return jsonify(new_device), 201

@app.route("/devices/<hostname>", methods=["PUT"])
@require_api_key
def update_device(hostname):
    updated_data = request.get_json(silent=True)

    if updated_data is None:
        return jsonify({
            "error": "Valid JSON body is required"
        }), 400

    if "hostname" in updated_data:
        if updated_data["hostname"] != hostname:
            return jsonify({
                "error":
                    "Hostname cannot be changed using PUT"
            }), 400

    validation_errors = validate_device(
        updated_data,
        require_all_fields=False
    )

    if validation_errors:
        return jsonify({
            "errors": validation_errors
        }), 400

    file_path, device = find_device_file(hostname)

    if device is None:
        return jsonify({
            "error": "Device not found"
        }), 404

    device.update(updated_data)

    save_config_file(
        file_path,
        device
    )

    logger.info(
        "Updated device: %s",
        hostname
    )

    return jsonify(device), 200

@app.route("/devices/<hostname>", methods=["DELETE"])
@require_api_key
def delete_device(hostname):
    file_path, device = find_device_file(hostname)

    if device is None:
        return jsonify({
            "error": "Device not found"
        }), 404

    file_path.unlink()

    logger.info(
        "Deleted device: %s",
        hostname
    )

    return jsonify({
        "message":
            f"{hostname} deleted successfully"
    }), 200

@app.errorhandler(404)
def route_not_found(error):
    return jsonify({
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method not allowed"
    }), 405


@app.errorhandler(500)
def internal_server_error(error):
    logger.exception(
        "Unexpected server error"
    )

    return jsonify({
        "error": "Internal server error"
    }), 500

if __name__ == "__main__":
    app.run(debug=True)