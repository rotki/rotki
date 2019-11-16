from gevent import monkey  # isort:skip # noqa
monkey.patch_all()  # isort:skip # noqa

import pytest

pytest.main()
