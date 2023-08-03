from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa

import gc
import sys

import pytest

# gc.disable()

exit_code = pytest.main()
sys.exit(exit_code)
