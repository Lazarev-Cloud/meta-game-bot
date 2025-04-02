import importlib
import inspect
import logging
import pathlib
import pkgutil
from typing import Callable, Any, Literal

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
    Универсальный загрузчик объектов из модулей пакета.

    - `filter_func(name, obj)` — фильтрация нужных объектов (например, isclass + issubclass)
    - `key_func(name, obj)` — ключ в результирующем словаре (например, `obj.__name__.lower()`)
    - `on_load(key, obj)` — побочный эффект (например, логгирование)
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
