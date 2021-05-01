"""Functionality common in some mixins"""

from typing import Any


def function_sig_key(name: str, arguments_matter: bool, *args: Any, **kwargs: Any) -> int:
    """Return a unique int identifying a function's call signature"""
    function_sig = name
    if arguments_matter:
        for arg in args:
            function_sig += str(arg)
        for _, value in kwargs.items():
            function_sig += str(value)

    return hash(function_sig)
