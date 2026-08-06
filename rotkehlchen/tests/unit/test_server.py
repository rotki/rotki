from __future__ import annotations

import ctypes
import os
import threading
from argparse import Namespace
from ctypes import wintypes
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.server import RotkehlchenServer


def test_register_windows_console_ctrl_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    set_console_ctrl_handler = MagicMock(return_value=1)
    kernel32 = SimpleNamespace(SetConsoleCtrlHandler=set_console_ctrl_handler)
    callback_type = MagicMock(side_effect=lambda handler: handler)
    winfunctype = MagicMock(return_value=callback_type)
    win_dll = MagicMock(return_value=kernel32)
    monkeypatch.setattr(ctypes, 'WINFUNCTYPE', winfunctype, raising=False)
    monkeypatch.setattr(ctypes, 'WinDLL', win_dll, raising=False)

    server = object.__new__(RotkehlchenServer)
    server._register_windows_console_ctrl_handler()

    winfunctype.assert_called_once_with(wintypes.BOOL, wintypes.DWORD)
    win_dll.assert_called_once_with('kernel32', use_last_error=True)
    assert set_console_ctrl_handler.argtypes == (callback_type, wintypes.BOOL)
    assert set_console_ctrl_handler.restype == wintypes.BOOL
    set_console_ctrl_handler.assert_called_once_with(server._windows_console_ctrl_handler, True)


def test_windows_console_ctrl_handler_waits_for_shutdown() -> None:
    server = object.__new__(RotkehlchenServer)
    server._shutdown_requested = threading.Event()
    server.stop_event = threading.Event()
    handler_thread = threading.Thread(
        target=server._handle_windows_console_ctrl,
        args=(2,),
    )

    handler_thread.start()
    try:
        assert server._shutdown_requested.wait(timeout=1) is True
        assert handler_thread.is_alive() is True
    finally:
        server.stop_event.set()
        handler_thread.join(timeout=1)

    assert handler_thread.is_alive() is False


def test_wait_for_windows_shutdown_calls_shutdown() -> None:
    server = object.__new__(RotkehlchenServer)
    server._shutdown_requested = threading.Event()
    server._shutdown_requested.set()
    server.stop_event = threading.Event()

    with (
        patch.object(os, 'name', 'nt'),
        patch.object(server, 'shutdown', side_effect=server.stop_event.set) as shutdown,
    ):
        server._wait_for_shutdown()

    shutdown.assert_called_once_with()


def test_shutdown_signals_completion_after_error() -> None:
    server = object.__new__(RotkehlchenServer)
    server._shutdown_requested = threading.Event()
    server._shutdown_lock = threading.Lock()
    server.stop_event = threading.Event()
    server.api_server = MagicMock()
    server.api_server.stop.side_effect = OSError

    with pytest.raises(OSError):
        server.shutdown()

    assert server._shutdown_requested.is_set() is True
    assert server.stop_event.is_set() is True


def test_main_logs_shutdown_error_and_exits_nonzero() -> None:
    server = object.__new__(RotkehlchenServer)
    server.args = Namespace(api_host='127.0.0.1', rest_api_port=4242)
    server.api_server = MagicMock()

    with (
        patch.object(server, '_register_windows_console_ctrl_handler'),
        patch('rotkehlchen.server.signal.signal'),
        patch('rotkehlchen.server.importlib.metadata.version', return_value='test'),
        patch('rotkehlchen.server.get_sqlcipher_version_string', return_value='test'),
        patch('rotkehlchen.server.log') as log,
        patch.object(server, '_wait_for_shutdown', side_effect=OSError('shutdown failed')),
        patch('rotkehlchen.server.os._exit') as exit_process,
    ):
        server.main()

    log.exception.assert_called_once_with('Backend shutdown failed')
    exit_process.assert_called_once_with(1)
