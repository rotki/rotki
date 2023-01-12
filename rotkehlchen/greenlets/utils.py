from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    import gevent


def get_greenlet_name(greenlet: Union['gevent.Greenlet', 'gevent.greenlet']) -> str:
    if greenlet.parent is None:
        greenlet_name = 'Main Greenlet'
    else:
        try:
            greenlet_name = greenlet.name
        except AttributeError:  # means it's a raw greenlet
            greenlet_name = f'Greenlet with id {id(greenlet)}'
    return greenlet_name
