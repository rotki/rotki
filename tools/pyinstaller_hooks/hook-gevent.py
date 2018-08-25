from pathlib import Path

import gevent


# This is temporarily needed until https://github.com/pyinstaller/pyinstaller/pull/3534 is fixed
def _get_gevent_imports():
    package_path = Path(gevent.__file__).parent

    imports = []
    imports.extend(
        'gevent.{}'.format(
            str(module.relative_to(package_path)).replace('.py', '').replace('/', '.'),
        )
        for module in package_path.glob('**/*.py')
    )
    imports.extend(
        'gevent.{}'.format(
            str(module.relative_to(package_path)).partition('.')[0].replace('/', '.'),
        )
        for module in package_path.glob('**/*.so')
    )

    return imports


hiddenimports = _get_gevent_imports()
