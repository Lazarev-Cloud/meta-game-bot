import json
import pathlib
import re
import logging

log = logging.getLogger(__name__)

_locales = {}
_locales_dir = pathlib.Path(__file__).parent.parent / "locales"


def load_translations():
    _locales.clear()
    for file in _locales_dir.glob("*.json"):
        lang = file.stem
        with open(file, "r", encoding="utf-8") as f:
            _locales[lang] = json.load(f)
            log.info(f"🌐 Locale loaded: '{lang}' with {len(_locales[lang])} keys")

    if not _locales:
        log.warning("⚠️ No locale files found in 'locales/' directory.")
    else:
        log.info(f"✅ Total languages loaded: {len(_locales)} → {', '.join(_locales.keys())}")


def t(key: str, lang: str = "ru", **kwargs) -> str:
    value = _locales.get(lang, {}).get(key, key)
    return _render_template(value, kwargs)


def _render_template(template: str, data: dict) -> str:
    return re.sub(r"{{\s*(\w+)\s*}}", lambda m: str(data.get(m.group(1), m.group(0))), template)
