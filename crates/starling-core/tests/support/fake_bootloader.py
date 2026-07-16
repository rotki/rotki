"""Python twin of `tests/support/fake_bootloader.rs`, used by the optional
Tier-1.5 integration test that bundles this script with pyinstaller --onedir.

Mode A (default): bootloader — write own pid to argv[1], spawn self as
grandchild with argv[2] as its pidfile, ignore graceful signals, loop.

Mode B (`--grandchild <pidfile>`): write own pid, ignore graceful signals,
loop.

The point is to mimic the runtime environment of the packaged rotki-core
(pyinstaller onedir, Python interpreter handling the signal) closely enough
that the same Job-Object / process-group machinery is exercised end-to-end.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def write_pid(path: str) -> None:
    # Atomic-ish write: tmp + rename, same as the Rust fixture.
    tmp = f'{path}.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(str(os.getpid()))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def ignore_graceful_signals() -> None:
    # On unix, SIGTERM is what the supervisor sends as the graceful signal.
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    # On windows, CTRL_BREAK_EVENT is delivered as SIGBREAK to python; default
    # raises KeyboardInterrupt. We want it ignored so the kill path is the
    # only way to reap us.
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal.SIG_IGN)


def loop_forever() -> None:
    while True:
        time.sleep(0.25)


def main() -> int:
    argv = sys.argv
    if len(argv) >= 3 and argv[1] == '--grandchild':
        write_pid(argv[2])
        ignore_graceful_signals()
        loop_forever()
        return 0

    if len(argv) < 3:
        sys.stderr.write(
            f'fake_bootloader.py: usage: {argv[0]} <own-pidfile> <grandchild-pidfile>\n',
        )
        return 2

    own_pidfile, grandchild_pidfile = argv[1], argv[2]
    write_pid(own_pidfile)

    # Spawn the grandchild as a copy of self. sys.executable points at the
    # pyinstaller-built exe in the bundled scenario, and at the python
    # interpreter when running this script directly.
    # Do NOT put the grandchild in its own console group on windows: it must
    # stay in the bootloader's group so the supervisor's CTRL_BREAK reaches it
    # (and it can then ignore it, just like the bootloader does).
    subprocess.Popen(  # noqa: S603 - intentional re-exec of self
        [sys.executable, '--grandchild', grandchild_pidfile],
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    ignore_graceful_signals()
    loop_forever()
    return 0


if __name__ == '__main__':
    sys.exit(main())
