"""
Initialize the actions subpackage.

This subpackage defines reusable action components used within the flow engine.
"""
import pathlib
from app.utils.module_loader import load_objects_from_package
from .base import FlowActionType

# Dictionary mapping action type keys to FlowActionType subclasses,
# automatically populated by scanning the actions subpackage.
action_types = load_objects_from_package(
    package_path=pathlib.Path(__file__).parent,
    package_name=__name__,

    filter_func=lambda name, obj: isinstance(obj, type) and issubclass(obj, FlowActionType)
    and obj is not FlowActionType,

    key_func=lambda name, obj: obj.__name__.removesuffix("Action").lower(),
    log_prefix="🔧 ActionType registered"
)
