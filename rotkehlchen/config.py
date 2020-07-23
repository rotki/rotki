import logging
import os
import platform
import shutil
from pathlib import Path

log = logging.getLogger(__name__)


def get_xdg_data_home() -> Path:
    directory = os.environ.get('XDG_DATA_HOME', None)
    if directory is None:
        home = os.path.expanduser("~")
        directory = os.path.join(home, '.local', 'share')

    return Path(directory)


def get_win32_appdata() -> Path:
    directory = os.environ.get('LOCALAPPDATA', None)
    if not directory:
        # In windows XP there is no localappdata
        directory = os.environ.get('APPDATA', None)
        if not directory:
            raise AssertionError('Could not detect an APPDATA directory')

    return Path(directory)


def old_data_directory() -> Path:
    home = os.path.expanduser("~")
    directory = os.path.join(home, '.rotkehlchen')
    return Path(directory)


def default_data_directory() -> Path:
    """Find the default data directory for Rotki for each different OS

    An interesting lirary that finds the data directories per OS is this:
    https://github.com/ActiveState/appdirs/blob/master/appdirs.py
    """
    if platform.system() == 'Linux':
        xdgconfig = get_xdg_data_home()
        datadir = xdgconfig / 'rotki' / 'data'
    elif platform.system() == 'Windows':
        appdata = get_win32_appdata()
        datadir = appdata / 'rotki' / 'data'
    elif platform.system() == 'Darwin':
        datadir = Path(os.path.expanduser('~/Library/Application Support/rotki/data'))
    else:
        raise AssertionError(f'Rotki running in unknown system: {platform.system()}')

    # If old data directory exists and new does not exist copy stuff
    old_dir = old_data_directory()
    if old_dir.exists() and not datadir.exists():
        log.info(f'First time using standard data directory. Copying from {old_dir} to {datadir}')
        shutil.copytree(old_dir, datadir)

    datadir.mkdir(parents=True, exist_ok=True)
    return datadir
