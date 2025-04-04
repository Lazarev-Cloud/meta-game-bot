"""
Dynamic loader for objects from a specified Python package.

This module provides a utility function to import modules dynamically
from a given package path and collect objects that match a filter condition.
Useful for automatic registration patterns such as loading command handlers,
plugins, or route definitions.
"""
import importlib
import inspect
import logging
import pathlib
import pkgutil
from typing import Callable, Any

log = logging.getLogger(__name__)


def load_objects_from_package(
        package_path: pathlib.Path,
        package_name: str,
        filter_func: Callable[[str, Any], bool],
        key_func: Callable[[str, Any], str],
        on_load: Callable[[str, Any], None] | None = None,
        skip_modules: set[str] = None,
        log_prefix: str = "📦 Loaded"
) -> dict[str, Any]:
    """
    Load objects from modules within a given package.

    Args:
        package_path (pathlib.Path): Filesystem path to the package directory.
        package_name (str): Importable name of the package (e.g. 'app.utils').
        filter_func (Callable): A function that determines whether an object should be loaded.
            Signature: (name: str, obj: Any) -> bool.
        key_func (Callable): A function that determines the key name in the resulting dictionary.
            Signature: (name: str, obj: Any) -> str.
        on_load (Callable, optional): Optional callback to execute when an object is loaded.
            Signature: (key: str, obj: Any) -> None.
        skip_modules (set[str], optional): Set of module names to skip during import.
            Defaults to {"__init__", "base"}.
        log_prefix (str, optional): Prefix for log entries when an object is loaded.

    Returns:
        dict[str, Any]: A dictionary mapping keys (as returned by `key_func`) to loaded objects.
    """
    if skip_modules is None:
        skip_modules = {"__init__", "base"}

    result = {}

    for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
        if module_name in skip_modules or module_name.startswith("_"):
            continue

        module = importlib.import_module(f"{package_name}.{module_name}")

        for name, obj in inspect.getmembers(module):
            if filter_func(name, obj):
                key = key_func(name, obj)
                result[key] = obj
                if on_load:
                    on_load(key, obj)
                else:
                    log.info(
                        f"{log_prefix}: '{key}' -> {obj.__module__}.{obj.__name__ if hasattr(obj, '__name__') else obj}"
                    )

    return result
