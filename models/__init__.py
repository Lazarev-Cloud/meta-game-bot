"""
Initialize the models package.

Dynamically imports all model modules for their side effects (e.g., class definitions),
without explicitly registering any objects.
"""
import pathlib
from app.utils.module_loader import load_objects_from_package

# Dynamically load all modules in the models package for side effects (e.g., ORM model definitions),
# but do not register or collect any objects.
# Only modules other than '__init__' are loaded.
load_objects_from_package(
    package_path=pathlib.Path(__file__).parent,
    package_name=__name__,
    filter_func=lambda name, obj: False,
    key_func=lambda name, obj: name,
    log_prefix="📦 Model loaded"
)
