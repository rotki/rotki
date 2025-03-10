from gevent import monkey, queue, subprocess  # isort:skip
monkey.patch_all()  # isort:skip

import sys

from urllib3.connectionpool import ConnectionPool

# Try to see if we will see no more deadlocks with this
# https://github.com/gevent/gevent/issues/1957#issuecomment-1902072588
ConnectionPool.QueueCls = queue.LifoQueue

import pytest

def run_tests(db_writer_process):
    try:
        exit_code = pytest.main()
    finally:
        db_writer_process.kill()
    return exit_code

with subprocess.Popen(
    [sys.executable, '-m', 'rotkehlchen.db.drivers.server'],
) as db_writer_process:
    exit_code = run_tests(db_writer_process)

sys.exit(exit_code)
