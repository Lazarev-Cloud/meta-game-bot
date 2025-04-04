"""
Localization and translation utility.

Loads translation files from the `locales/` directory and provides
a simple translation function with template variable substitution.
"""


import json
import pathlib
import re
import logging

log = logging.getLogger(__name__)

_locales = {}
_locales_dir = pathlib.Path(__file__).parent.parent / "locales"


def load_translations():
    """
    Load all translation files from the 'locales/' directory.

    Each JSON file is expected to contain key-value pairs for a specific language.
    Loaded translations are stored in the internal `_locales` dictionary.

    Logs:
        - Each successfully loaded language and number of keys.
        - A warning if no locales are found.
    """
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
    """
    Retrieve a translated string by key for the specified language.

    Args:
        key (str): The translation key.
        lang (str, optional): The language code (default is "ru").
        **kwargs: Optional template variables to interpolate in the translation.

    Returns:
        str: The translated and rendered string if available; otherwise returns the key itself.
    """
    value = _locales.get(lang, {}).get(key, key)
    return _render_template(value, kwargs)


def _render_template(template: str, data: dict) -> str:
    """
    Replace template variables in the form of {{ variable }} with values from the data dictionary.

    Args:
        template (str): The string containing placeholders.
        data (dict): Dictionary with values to substitute.

    Returns:
        str: The rendered string with variables replaced.
    """
    return re.sub(r"{{\s*(\w+)\s*}}", lambda m: str(data.get(m.group(1), m.group(0))), template)
