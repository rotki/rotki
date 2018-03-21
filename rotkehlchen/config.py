import os
import errno


def default_data_directory():
    home = os.path.expanduser("~")
    data_directory = os.path.join(home, '.rotkehlchen')
    try:
        os.makedirs(data_directory)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    return data_directory
