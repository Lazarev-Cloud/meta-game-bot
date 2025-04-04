"""
Utility for loading flow configuration files.

Currently supports loading configuration from JSON files.
Future enhancements may include YAML support.
"""
import json
from pathlib import Path


def load_flow_config(path: str | Path) -> dict:
    """
    Load a flow configuration from a JSON file.

    Args:
        path (str | Path): Path to the JSON configuration file.

    Raises:
        FileNotFoundError: If the specified file does not exist.

    Returns:
        dict: Parsed configuration dictionary.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Flow config not found at: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

# TODO: Make flow.json validation function.
