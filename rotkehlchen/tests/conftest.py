import re
import sys

import py
import pytest

from rotkehlchen.config import default_data_directory
from rotkehlchen.globaldb.handler import GlobalDBHandler

GlobalDBHandler(default_data_directory())

from rotkehlchen.tests.fixtures import *  # noqa: F401,F403

# monkey patch web3's non-thread safe lru cache with our own version
from rotkehlchen.chain.ethereum import patch_web3  # isort:skip # pylint: disable=unused-import # lgtm[py/unused-import] # noqa


def pytest_addoption(parser):
    parser.addoption(
        '--initial-port',
        type=int,
        default=29870,
        help='Base port number used to avoid conflicts while running parallel tests.',
    )


if sys.platform == 'darwin':
    # On macOS the temp directory base path is already very long.
    # To avoid failures on ipc tests (ipc path length is limited to 104/108 chars on macOS/linux)
    # we override the pytest tmpdir machinery to produce shorter paths.

    @pytest.fixture(scope='session', autouse=True)
    def _tmpdir_short(request):
        """Shorten tmpdir paths"""
        from _pytest.tmpdir import TempdirFactory  # pylint: disable=import-outside-toplevel

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
