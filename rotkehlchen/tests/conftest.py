import datetime
import re
import sys
import tempfile
from pathlib import Path

import py
import pytest

from rotkehlchen.logging import TRACE, add_logging_level, configure_logging
from rotkehlchen.tests.utils.args import default_args

add_logging_level('TRACE', TRACE)
configure_logging(default_args())
# sql instructions for global DB are customizable here:
# https://github.com/rotki/rotki/blob/eb5bef269207e8b84075ee36ce7c3804115ed6a0/rotkehlchen/tests/fixtures/globaldb.py#L33

from rotkehlchen.tests.fixtures import *  # noqa: F401,F403

# monkey patch web3's non-thread safe lru cache with our own version
from rotkehlchen.chain.ethereum import patch_web3  # isort:skip # pylint: disable=unused-import # lgtm[py/unused-import] # noqa

assert sys.version_info.major == 3, 'Need to use python 3 for rotki'
assert 9 == sys.version_info.minor, 'Need to use python 3.9 for rotki'


def pytest_addoption(parser):
    parser.addoption(
        '--initial-port',
        type=int,
        default=29870,
        help='Base port number used to avoid conflicts while running parallel tests.',
    )
    parser.addoption('--profiler', default=None, choices=['flamegraph-trace'])


if sys.platform == 'darwin':
    # On macOS the temp directory base path is already very long.
    # To avoid failures on ipc tests (ipc path length is limited to 104/108 chars on macOS/linux)
    # we override the pytest tmpdir machinery to produce shorter paths.

    @pytest.fixture(scope='session', autouse=True)
    def _tmpdir_short(request):
        """Shorten tmpdir paths"""
        from pytest import TempdirFactory  # pylint: disable=import-outside-toplevel

        def getbasetemp(self):
            """ return base temporary directory. """
            try:
                return self._basetemp
            except AttributeError:
                basetemp = self.config.option.basetemp
                if basetemp:
                    basetemp = py.path.local(basetemp)  # pylint: disable=no-member
                    if basetemp.check():
                        basetemp.remove()
                    basetemp.mkdir()
                else:
                    rootdir = py.path.local.get_temproot()  # pylint: disable=no-member
                    rootdir.ensure(dir=1)
                    basetemp = py.path.local.make_numbered_dir(  # pylint: disable=no-member
                        prefix='pyt',
                        rootdir=rootdir,
                    )
                self._basetemp = t = basetemp.realpath()
                self.trace('new basetemp', t)
                return t

        TempdirFactory.getbasetemp = getbasetemp
        try:
            delattr(request.config._tmpdirhandler, '_basetemp')
        except AttributeError:
            pass

    @pytest.fixture
    def tmpdir(request, tmpdir_factory):
        """Return a temporary directory path object
        which is unique to each test function invocation,
        created as a sub directory of the base temporary
        directory.  The returned object is a `py.path.local`_
        path object.
        """
        name = request.node.name
        name = re.sub(r'[\W]', '_', name)
        max_val = 1
        if len(name) > max_val:
            name = name[:max_val]
        return tmpdir_factory.mktemp(name, numbered=True)


@pytest.fixture(autouse=True, scope="session")
def profiler(request):
    profiler_instance = None

    if request.config.option.profiler == 'flamegraph-trace':
        from tools.profiling.sampler import (  # pylint: disable=import-outside-toplevel  # noqa: E501
            FlameGraphCollector,
            TraceSampler,
        )

        now = datetime.datetime.now()
        tmpdirname = tempfile.gettempdir()
        stack_path = Path(tmpdirname) / f'{now:%Y%m%d_%H%M}_stack.data'
        print(f'Stack data is saved at: {stack_path}')
        stack_stream = open(stack_path, 'w')
        flame = FlameGraphCollector(stack_stream)
        profiler_instance = TraceSampler(flame)

    yield

    if profiler_instance is not None:
        profiler_instance.stop()
