"""A module with miscellaneous functions that do not depend on db/drivers/gevent.py
due. Needed in packaging since that code has log.trace and should only be
imported if trace level has been setup"""

import re

from pysqlcipher3 import dbapi2 as sqlcipher


def get_sqlcipher_version_string() -> str:
    """Retrieve SQLCipher version used by the app"""
    conn = sqlcipher.connect(':memory:')  # pylint: disable=no-member
    version = conn.execute('PRAGMA cipher_version;').fetchone()[0]
    conn.close()
    return version


def detect_sqlcipher_version() -> int:
    """Returns the major part of the version for SQLCipher"""
    version = get_sqlcipher_version_string()
    if not (match := re.search(r'(\d+).(\d+).(\d+)', version)):
        raise ValueError(f'Could not process the version returned by SQLCipher: {version}')

    return int(match.group(1))
