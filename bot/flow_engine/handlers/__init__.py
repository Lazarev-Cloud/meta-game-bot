import importlib
import pkgutil
import inspect
import pathlib
import logging

log = logging.getLogger(__name__)

handler_registry = {}

package_name = __name__  # "flow_engine.handlers"
package_path = pathlib.Path(__file__).parent

for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
    if module_name.startswith("_"):
        continue

    module = importlib.import_module(f"{package_name}.{module_name}")

    for name, obj in inspect.getmembers(module):
        if inspect.iscoroutinefunction(obj):
            handler_registry[name] = obj
            log.info(f"⚙️ Handler registered: '{name}' -> {module.__name__}.{name}")
