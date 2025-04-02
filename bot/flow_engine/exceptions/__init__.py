import pathlib
from app.utils.module_loader import load_objects_from_package

# Просто импортируем все ошибки, не регистрируем ничего.
load_objects_from_package(
    skip_modules={"__init__"},
    package_path=pathlib.Path(__file__).parent,
    package_name=__name__,
    filter_func=lambda name, obj: False,  # не ищем объекты
    key_func=lambda name, obj: name,
    log_prefix="📦 Model loaded"
)
