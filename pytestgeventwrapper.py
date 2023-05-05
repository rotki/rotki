from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa

import sys

import pytest

exit_code = pytest.main()
sys.exit(exit_code)
