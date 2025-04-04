"""
Initialization module for loading exception definitions.

Dynamically imports all exception modules from the current package
without registering any objects.
"""
import pathlib
from app.utils.module_loader import load_objects_from_package

# Dynamically load all modules in the current package for side effects (e.g., class definitions),
# but do not register or collect any objects.
# Only modules other than '__init__' are loaded.
load_objects_from_package(
    skip_modules={"__init__"},
    package_path=pathlib.Path(__file__).parent,
    package_name=__name__,
    filter_func=lambda name, obj: False,
    key_func=lambda name, obj: name,
    log_prefix="📦 Model loaded"
)
