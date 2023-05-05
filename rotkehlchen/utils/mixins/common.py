"""Functionality common in some mixins"""

from typing import Any


def function_sig_key(
        name: str,
        arguments_matter: bool,
        skip_ignore_cache: bool,
        *args: Any,
        **kwargs: Any,
) -> int:
    """Return a unique int identifying a function's call signature

    If arguments_matter is True then the function signature depends on the given arguments
    If skip_ignore_cache is True then the ignore_cache kwarg argument is not counted
    in the signature calculation
    """
    function_sig = name
    if arguments_matter:
        for arg in args:
            function_sig += str(arg)
        for argname, value in kwargs.items():
            if skip_ignore_cache and argname == 'ignore_cache':
                continue

            function_sig += str(value)

    return hash(function_sig)
