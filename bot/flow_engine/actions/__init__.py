import importlib
import pkgutil
import inspect
import pathlib
import logging
from .base import FlowActionType

log = logging.getLogger(__name__)

action_types = {}

package_name = __name__  # "flow_engine.actions"
package_path = pathlib.Path(__file__).parent

for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
    if module_name in {"base", "__init__"} or module_name.startswith("_"):
        continue

    module = importlib.import_module(f"{package_name}.{module_name}")

    for name, obj in inspect.getmembers(module):
        if (
            inspect.isclass(obj)
            and issubclass(obj, FlowActionType)
            and obj is not FlowActionType
        ):
            type_name = obj.__name__.removesuffix("Action").lower()
            action_types[type_name] = obj
            log.info(f"🔧 ActionType registered: '{type_name}' -> {obj.__module__}.{obj.__name__}")
