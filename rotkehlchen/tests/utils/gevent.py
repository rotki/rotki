import socket

from gevent import monkey


def ensure_gevent_patches() -> None:
    """Ensure gevent monkey patches are active for socket/select/time modules.

    Some pytest plugins (or imported test utilities) can restore stdlib modules
    after gevent has already been patched. When that happens, parts of the test
    stack may run with blocking stdlib primitives instead of gevent-cooperative
    ones, which can cause flaky behavior (timeouts, hanging waits, or server
    startup races).

    We call this helper in two places on purpose:
    1) per-test setup hook, to recover from plugin interference across tests.
    2) API server creation path, as a last-mile safeguard before binding/listening.
    """
    if not socket.socket.__module__.startswith('gevent'):
        monkey.patch_socket()
    if not monkey.is_module_patched('select'):
        monkey.patch_select()
    if not monkey.is_module_patched('time'):
        monkey.patch_time()
