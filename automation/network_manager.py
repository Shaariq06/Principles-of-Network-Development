import json
import yaml
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configuration"
RELATIONSHIPS_FILE = BASE_DIR / "relationships" / "network_relationships.yaml"


def load_json(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def load_yaml(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def load_device_configs():
    devices = []

    for file_path in CONFIG_DIR.rglob("*"):
        if file_path.suffix == ".json":
            devices.append(load_json(file_path))

        elif file_path.suffix in [".yaml", ".yml"]:
            devices.append(load_yaml(file_path))

    return devices


def load_relationships():
    return load_yaml(RELATIONSHIPS_FILE)


def get_hostname(device):
    if isinstance(device, dict):
        return device.get("hostname")
    return None


def display_devices(devices):
    print("\nDevices loaded:")
    for device in devices:
        hostname = get_hostname(device)

        if hostname:
            print(f"- {hostname}")

def get_hostnames(devices):
    hostnames = set()

    for device in devices:
        if isinstance(device, dict):
            hostname = device.get("hostname")

            if hostname:
                hostnames.add(hostname)

    return hostnames


def find_referenced_devices(data):
    referenced_devices = set()

    if isinstance(data, dict):
        for key, value in data.items():
            if key == "hostname" and isinstance(value, str):
                referenced_devices.add(value)

            elif key in ["connects_to", "communicates_with"]:
                if isinstance(value, list):
                    referenced_devices.update(value)

            else:
                referenced_devices.update(
                    find_referenced_devices(value)
                )

    elif isinstance(data, list):
        for item in data:
            referenced_devices.update(
                find_referenced_devices(item)
            )

    return referenced_devices


def validate_relationships(devices, relationships):
    configured_devices = get_hostnames(devices)

    referenced_devices = find_referenced_devices(
        relationships["network_relationships"]
    )

    print("\nRelationship validation:")
    print("------------------------")

    errors = 0

    for hostname in sorted(referenced_devices):
        if hostname in configured_devices:
            print(f"✓ {hostname}")
        else:
            print(f"✗ {hostname} - configuration not found")
            errors += 1

    print()

    if errors == 0:
        print("All network relationships are valid.")
    else:
        print(f"{errors} relationship error(s) found.")

def display_network_summary(devices):
    counts = {
        "routers": 0,
        "switches": 0,
        "pcs": 0,
        "laptops": 0,
        "phones": 0,
        "printers": 0,
        "firewalls": 0,
        "servers": 0
    }

    for device in devices:
        hostname = device.get("hostname", "")

        if hostname.startswith("R") or hostname == "HR1":
            counts["routers"] += 1

        elif hostname.startswith("SW"):
            counts["switches"] += 1

        elif hostname.startswith("PC"):
            counts["pcs"] += 1

        elif hostname.startswith("Laptop") or hostname == "HL1":
            counts["laptops"] += 1

        elif hostname.startswith("IP Phone") or hostname == "HP1":
            counts["phones"] += 1

        elif hostname.startswith("Printer"):
            counts["printers"] += 1

        elif hostname.endswith("-FW"):
            counts["firewalls"] += 1

        elif hostname.endswith("-SERVER"):
            counts["servers"] += 1

    print("\nNetwork Summary")
    print("---------------")
    print(f"Routers: {counts['routers']}")
    print(f"Switches: {counts['switches']}")
    print(f"PCs: {counts['pcs']}")
    print(f"Laptops: {counts['laptops']}")
    print(f"IP Phones: {counts['phones']}")
    print(f"Printers: {counts['printers']}")
    print(f"Firewalls: {counts['firewalls']}")
    print(f"Servers: {counts['servers']}")
    print(f"Total devices: {len(devices)}")

def main():
    devices = load_device_configs()
    relationships = load_relationships()

    print("Network Configuration Manager")
    print("-----------------------------")
    print(f"Configuration files loaded: {len(devices)}")

    display_devices(devices)

    print("\nNetwork environments:")
    for environment in relationships["network_relationships"]:
        print(f"- {environment}")

    display_network_summary(devices)
    validate_relationships(devices, relationships)


if __name__ == "__main__":
    main()