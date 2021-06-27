"""Named this file typedefs since either typing or types seems to conflicts with
built-in files due to a mypy bug

https://github.com/python/mypy/issues/10722
https://github.com/python/mypy/issues/1876#issuecomment-782458452
"""

from enum import Enum


class WSMessageType(Enum):
    LEGACY = 1

    def __str__(self) -> str:
        return self.name.lower()  # pylint: disable=no-member
