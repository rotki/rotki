from typing import Any, Union


def get_greenlet_name(greenlet: Union[Any, Any]) -> str:
    """Get name of a greenlet or thread for logging"""
    if greenlet.parent is None:
        greenlet_name = 'Main Greenlet'
    else:
        try:
            greenlet_name = greenlet.name
        except AttributeError:  # means it's a raw greenlet
            greenlet_name = f'Greenlet with id {id(greenlet)}'
    return greenlet_name
