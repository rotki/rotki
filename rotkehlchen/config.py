import logging
import os
import platform
import shutil
from pathlib import Path

log = logging.getLogger(__name__)


def get_xdg_config_home() -> Path:
    directory = os.environ.get('XDG_CONFIG_HOME', None)
    if directory is None:
        home = os.path.expanduser("~")
        directory = os.path.join(home, '.config')

    return Path(directory)


def old_data_directory() -> Path:
    home = os.path.expanduser("~")
    directory = os.path.join(home, '.rotkehlchen')
    return Path(directory)


def default_data_directory() -> Path:
    if platform.system() == 'Linux':
        xdgconfig = get_xdg_config_home()
        datadir = xdgconfig / 'rotki' / 'data'
    elif platform.system() == 'Windows':
        # TODO
        pass
    elif platform.system() == 'Darwin':
        # TODO
        pass
    else:
        raise AssertionError(f'Rotki running in unknown system: {platform.system()}')

    # If old data directory exists and new does not exist copy stuff
    old_dir = old_data_directory()
    if old_dir.exists() and not datadir.exists():
        log.info(f'First time using standard data directory. Copying from {old_dir} to {datadir}')
        shutil.copytree(old_dir, datadir)

    datadir.mkdir(parents=True, exist_ok=True)
    return datadir
