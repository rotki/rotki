from gevent import monkey, queue  # isort:skip
monkey.patch_all()  # isort:skip

from subprocess import Popen
from urllib3.connectionpool import ConnectionPool
# Try to see if we will see no more deadlocks with this
# https://github.com/gevent/gevent/issues/1957#issuecomment-1902072588
ConnectionPool.QueueCls = queue.LifoQueue

import sys

import pytest

db_writer_process = Popen([sys.executable, '-m', 'rotkehlchen.db.drivers.server'])
exit_code = pytest.main()
db_writer_process.terminate()
sys.exit(exit_code)
