# Stub created after looking at Crypto/Random/__init__.py
from typing import Any


class _UrandomRNG(object):

    def read(self, n: int) -> bytes:
        ...


def new(*args: Any, **kwargs: Any) -> _UrandomRNG:
    ...
