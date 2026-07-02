from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    import gevent

    from rotkehlchen.concurrency import CancellationToken


def request_cancellation(greenlet: 'gevent.Greenlet', reason: str) -> bool:
    """Request cooperative cancellation of a task greenlet.

    Returns True if the greenlet carries a cancellation token (set by whoever
    spawned it) and cancellation was requested, False otherwise. The greenlet
    dies with TaskCancelledError at its next checkpoint -- callers that need
    it gone must wait on it afterwards.
    """
    token: CancellationToken | None = getattr(greenlet, 'cancellation_token', None)
    if token is None:
        return False

    token.cancel(reason)
    return True


def get_greenlet_name(greenlet: Union['gevent.Greenlet', 'gevent.greenlet']) -> str:
    if greenlet.parent is None:
        greenlet_name = 'Main Greenlet'
    else:
        try:
            greenlet_name = greenlet.name
        except AttributeError:  # means it's a raw greenlet
            greenlet_name = f'Greenlet with id {id(greenlet)}'
    return greenlet_name
