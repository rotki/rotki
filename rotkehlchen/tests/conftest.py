import datetime
import os
import re
import sys
import tempfile
import warnings as test_warnings
from contextlib import suppress
from enum import auto
from pathlib import Path
from typing import Any

import py
import pytest

from rotkehlchen.config import default_data_directory
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import TRACE, add_logging_level, configure_logging
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin


TESTS_ROOT_DIR = Path(__file__).parent


class TestEnvironment(SerializableEnumMixin):
    STANDARD = auto()  # test during normal development
    NIGHTLY = auto()  # all tests
    NFTS = auto()  # nft tests


add_logging_level('TRACE', TRACE)
configure_logging(default_args())
# sql instructions for global DB are customizable here:
# https://github.com/rotki/rotki/blob/eb5bef269207e8b84075ee36ce7c3804115ed6a0/rotkehlchen/tests/fixtures/globaldb.py#L33

from rotkehlchen.tests.fixtures import *  # noqa: F403

assert sys.version_info.major == 3, 'Need to use python 3 for rotki'
assert sys.version_info.minor == 9, 'Need to use python 3.9 for rotki'


def pytest_addoption(parser):
    parser.addoption(
        '--initial-port',
        type=int,
        default=29870,
        help='Base port number used to avoid conflicts while running parallel tests.',
    )
    parser.addoption(
        '--no-network-mocking',
        action='store_true',
        help='If set then all tests that are aware of their mocking the network will not do that. Use this in order to easily skip mocks and test that using the network, the remote queries are still working fine and mocks dont need any changing.',  # noqa: E501
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
        with suppress(AttributeError):
            delattr(request.config._tmpdirhandler, '_basetemp')

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
        test_warnings.warn(UserWarning(
            f'Stack data is saved at: {stack_path}',
        ))
        stack_stream = open(stack_path, 'w')
        flame = FlameGraphCollector(stack_stream)
        profiler_instance = TraceSampler(flame)

    yield

    if profiler_instance is not None:
        profiler_instance.stop()


def requires_env(allowed_envs: list[TestEnvironment]):
    """Conditionally run tests if the environment is in the list of allowed environments"""
    try:
        env = TestEnvironment.deserialize(os.environ.get('TEST_ENVIRONMENT', 'standard'))
    except DeserializationError:
        env = TestEnvironment.STANDARD

    return pytest.mark.skipif(
        'CI' in os.environ and env not in allowed_envs,
        reason=f'Not suitable envrionment {env} for current test',
    )


def get_cassette_dir(request: pytest.FixtureRequest) -> Path:
    """
    Directory structure for cassettes in each test file resembles the file's path
    e.g. for tests in           `tests/unit/decoders/test_aave.py`
         cassettes are in   `cassettes/unit/decoders/test_aave/`
    """
    return Path(request.node.path).relative_to(TESTS_ROOT_DIR).with_suffix('')


@pytest.fixture
def vcr_config(request: pytest.FixtureRequest, default_cassette_name: str) -> dict[str, Any]:
    """
    vcrpy config
    - record_mode: allow rewriting multiple cassettes using CASSETTE_REWRITE_PATH env variable
      e.g. `CASSETTE_REWRITE_PATH=unit/decoders` will rewrite all decoder cassettes
           `CASSETTE_REWRITE_PATH=*` will rewrite all cassettes
    - decode_compressed_response: decode if not in CI (for readability)
    # pytest-deadfixtures ignore
    ^^^ this allows our fork of pytest-deadfixtures to ignore this fixture for usage detection
    since it cannot detect dynamic usage (request.getfixturevalue) in pytest-recording
    """
    rewrite_path = os.environ.get('CASSETTE_REWRITE_PATH')
    cassette_dir = get_cassette_dir(request)
    cassette_path = cassette_dir / default_cassette_name

    if rewrite_path and (cassette_path.is_relative_to(rewrite_path) or rewrite_path == '*'):
        record_mode = 'rewrite'
    else:
        record_mode = 'once'

    decode_compressed_response = 'CI' not in os.environ

    return {
        'record_mode': record_mode,
        'decode_compressed_response': decode_compressed_response,
    }


@pytest.fixture(scope='module')
def vcr_cassette_dir(request: pytest.FixtureRequest) -> str:
    """Override pytest-recording's bundled fixture to store cassettes outside source code"""
    if 'CI' in os.environ:
        base_dir = Path.home() / '.cache' / '.rotkehlchen-cassettes-dir'
    else:
        base_dir = default_data_directory().parent / 'cassettes'
    cassette_dir = get_cassette_dir(request)
    return str(base_dir / cassette_dir)
