import datetime
import logging
import os
import re
import sys
import tempfile
import warnings as test_warnings
from contextlib import suppress
from enum import auto
from http import HTTPStatus
from json import JSONDecodeError
from pathlib import Path
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Any, Optional

import py
import pytest

from rotkehlchen.config import default_data_directory
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import TRACE, RotkehlchenLogsAdapter, add_logging_level, configure_logging
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from vcr import VCR


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

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

        pytest.TempdirFactory.getbasetemp = getbasetemp
        with suppress(AttributeError):
            delattr(request.config._tmpdirhandler, '_basetemp')

    @pytest.fixture()
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


@pytest.fixture(autouse=True, scope='session', name='profiler')
def _fixture_profiler(request):
    profiler_instance = None
    stack_stream = None

    if request.config.option.profiler is None:
        yield  # no profiling
    elif request.config.option.profiler != 'flamegraph-trace':
        raise ValueError(f'Gave unknown profiler option: {request.config.option.profiler}')
    else:  # flamegraph profiler on
        from tools.profiling.sampler import (  # pylint: disable=import-outside-toplevel
            FlameGraphCollector,
            TraceSampler,
        )

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        tmpdirname = tempfile.gettempdir()
        stack_path = Path(tmpdirname) / f'{now:%Y%m%d_%H%M}_stack.data'
        with open(stack_path, 'w') as stack_stream:
            test_warnings.warn(UserWarning(
                f'Stack data is saved at: {stack_path}',
            ))
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


def is_etherscan_rate_limited(response: dict[str, Any]) -> bool:
    result = False
    with suppress(JSONDecodeError, KeyError):
        body = jsonloads_dict(response['body']['string'])
        result = int(body['status']) == 0 and 'rate limit reached' in body['result']
    return result


@pytest.fixture(scope='module', name='vcr')
def vcr_fixture(vcr: 'VCR') -> 'VCR':
    """
    Update VCR instance to discard error responses during the record mode.
    This target directly etherscan that is the service we are first focusing on
    # pytest-deadfixtures ignore
    """

    def before_record_response(response: dict[str, Any]) -> Optional[dict[str, Any]]:
        if (
            'RECORD_CASSETTES' in os.environ and
            response['status']['code'] != HTTPStatus.OK or
            is_etherscan_rate_limited(response)
        ):
            return None

        return response

    vcr.before_record_response = before_record_response
    return vcr


@pytest.fixture(scope='module')
def vcr_config() -> dict[str, Any]:
    """
    vcrpy config
    - record_mode: allow rewriting multiple cassettes using CASSETTE_REWRITE_PATH env variable
    - decode_compressed_response: True to correctly inspect the responses
    - ignore_localhost: Don't record queries made to localhost
    # pytest-deadfixtures ignore
    ^^^ this allows our fork of pytest-deadfixtures to ignore this fixture for usage detection
    since it cannot detect dynamic usage (request.getfixturevalue) in pytest-recording
    """
    if 'RECORD_CASSETTES' in os.environ:
        record_mode = 'once'
    else:
        record_mode = 'none'

    return {
        'record_mode': record_mode,
        'decode_compressed_response': True,
        'ignore_localhost': True,
    }


@pytest.fixture(scope='module')
def vcr_cassette_dir(request: pytest.FixtureRequest) -> str:
    """
    Override pytest-vcr's bundled fixture to store cassettes outside source code
    # pytest-deadfixtures ignore
    """
    if 'CI' in os.environ:
        current_branch = os.environ.get('GITHUB_HEAD_REF')  # get branch from github actions
        root_dir = Path(os.environ['CASSETTES_DIR'])
    else:
        current_branch = os.environ.get('VCR_BRANCH')
        root_dir = default_data_directory().parent / 'test-caching'
    base_dir = root_dir / 'cassettes'

    # Clone repo if needed
    if (root_dir / '.git').exists() is False:
        cmd = f'git clone https://github.com/rotki/test-caching.git "{root_dir}"'
        log.debug(f'Cloning test caching repo to {root_dir}')
        os.popen(cmd).read()

    if current_branch is None:
        current_branch = os.popen('git rev-parse --abbrev-ref HEAD').read().rstrip('\n')
    log.debug(f'At VCR setup, {current_branch=}')
    checkout_proc = Popen(f'cd "{root_dir}" && git fetch origin && git checkout {current_branch} && git reset --hard origin/{current_branch}', shell=True, stdout=PIPE, stderr=PIPE)  # noqa: E501
    _, stderr = checkout_proc.communicate(timeout=10)
    if (
        len(stderr) != 0 and
        b'Already on' not in stderr and
        b'Switched to' not in stderr
    ):
        default_branch = os.environ.get('GITHUB_BASE_REF', os.environ.get('DEFAULT_VCR_BRANCH', 'develop'))  # noqa: E501
        log.error(f'Could not find branch {current_branch} in {root_dir}. Defaulting to {default_branch}')  # noqa: E501
        checkout_proc = Popen(f'cd "{root_dir}" && git fetch origin && git checkout {default_branch} && git reset --hard origin/{default_branch}', shell=True, stdout=PIPE, stderr=PIPE)  # noqa: E501
        checkout_proc.wait()
        log.debug(f'VCR setup: Switched to test-caching branch: {default_branch}')
    else:
        log.debug(f'VCR setup: Switched to test-caching branch: {current_branch}')

    cassette_dir = get_cassette_dir(request)
    return str(base_dir / cassette_dir)
