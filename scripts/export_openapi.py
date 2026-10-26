"""Utility script to export static openapi.json and openapi.yaml specifications."""

import json
import sys
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from app.main import app  # noqa: E402


def export_openapi():
    """Generate OpenAPI specification files in docs/ directory."""
    output_dir = Path(__file__).resolve().parent.parent / "docs"
    output_dir.mkdir(parents=True, exist_ok=True)

    openapi_data = app.openapi()

    # Write JSON
    json_path = output_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_data, f, indent=2)
    print(f"[OK] Successfully exported OpenAPI JSON to: {json_path}")

    # Write YAML
    yaml_path = output_dir / "openapi.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_data, f, sort_keys=False)
    print(f"[OK] Successfully exported OpenAPI YAML to: {yaml_path}")


if __name__ == "__main__":
    export_openapi()
