from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa
import atexit
import weakref

weakref_finalize = weakref.finalize
atexit.register(weakref_finalize._exitfunc)
weakref_finalize._registered_with_atexit = True

import sys

import pytest

exit_code = pytest.main()
sys.exit(exit_code)
