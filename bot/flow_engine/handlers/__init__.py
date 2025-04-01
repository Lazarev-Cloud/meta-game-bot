import pathlib
from app.utils.module_loader import load_objects_from_package


handler_registry = load_objects_from_package(
    package_path=pathlib.Path(__file__).parent,
    package_name=__name__,
    filter_func=lambda name, obj: callable(obj) and getattr(obj, "__code__", None) and obj.__code__.co_flags & 0x80,
    key_func=lambda name, obj: name,
    log_prefix="⚙️ Handler registered"
)
