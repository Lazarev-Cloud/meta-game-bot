import json
from pathlib import Path


def load_flow_config(path: str | Path) -> dict:
    """
    Загружает flow-конфигурацию из JSON-файла.
    В будущем можно добавить поддержку YAML.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Flow config not found at: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
