import yaml
from pathlib import Path
from typing import Dict, Any


def load_openapi_spec(spec_path: Path) -> Dict[str, Any]:
    """Load and parse an OpenAPI specification file.

    Args:
        spec_path: Path to the OpenAPI YAML file

    Returns:
        Parsed OpenAPI specification as dictionary
    """
    if not spec_path.exists():
        raise FileNotFoundError(f"OpenAPI spec file not found at {spec_path}")

    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)

    return spec


def validate_zephyr_spec(spec: Dict[str, Any]) -> bool:
    """Validate that the OpenAPI spec is for Zephyr Scale API.

    Args:
        spec: Parsed OpenAPI specification

    Returns:
        True if valid, False otherwise
    """
    # Check if it's an OpenAPI spec
    if "openapi" not in spec:
        return False

    # Check if it's for Zephyr Scale
    info = spec.get("info", {})
    title = info.get("title", "").lower()
    description = info.get("description", "").lower()

    return "zephyr" in title or "zephyr" in description


def extract_api_endpoints(spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract API endpoints from the OpenAPI spec.

    Args:
        spec: Parsed OpenAPI specification

    Returns:
        Dictionary of endpoints with their details
    """
    endpoints = {}
    paths = spec.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete"]:
                endpoint_id = f"{method.upper()} {path}"
                endpoints[endpoint_id] = {
                    "path": path,
                    "method": method,
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "parameters": details.get("parameters", []),
                    "responses": details.get("responses", {}),
                }

    return endpoints
