import os
import pkgutil
import importlib

package_dir = os.path.dirname(__file__)
package_name = __name__  # 'app.models'

# Динамически импортируем каждый модуль внутри этой папки
for _, module_name, is_pkg in pkgutil.iter_modules([package_dir]):
    if not is_pkg:
        importlib.import_module(f"{package_name}.{module_name}")
