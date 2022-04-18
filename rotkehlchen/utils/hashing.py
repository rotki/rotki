import hashlib
from pathlib import Path

from rotkehlchen.errors.misc import SystemPermissionError


def file_md5(filepath: Path) -> str:
    """Gets the hexadecimal string representation of the md5 hash of filepath

    Before calling the function, caller has to make sure path exists and is a file

    May raise:
    - SystemPermissionError if the file can't be accessed for some reason
    """
    md5_hash = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            # Read and update hash in chunks of 4K
            for byte_block in iter(lambda: f.read(4096), b''):
                md5_hash.update(byte_block)
    except PermissionError as e:
        raise SystemPermissionError(f'Failed to open: {filepath}. {str(e)}') from e

    return md5_hash.hexdigest()
