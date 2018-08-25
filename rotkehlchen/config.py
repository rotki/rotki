import os
import errno

from rotkehlchen.typing import FilePath


def default_data_directory() -> FilePath:
    home = os.path.expanduser("~")
    data_directory = os.path.join(home, '.rotkehlchen')
    try:
        os.makedirs(data_directory)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    return FilePath(data_directory)
