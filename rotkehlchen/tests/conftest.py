import datetime
import logging
import os
import re
import shutil
import sys
import tempfile
import warnings as test_warnings
from contextlib import suppress
from enum import auto
from http import HTTPStatus
from json import JSONDecodeError
from pathlib import Path
from subprocess import PIPE, Popen, check_output  # noqa: S404
from typing import TYPE_CHECKING, Any

import py
import pytest

from rotkehlchen.config import default_data_directory
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import TRACE, RotkehlchenLogsAdapter, add_logging_level, configure_logging
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from vcr import VCR


# Added here to prevent a warning about polars and forking which does not affect us
os.environ['POLARS_ALLOW_FORKING_THREAD'] = '1'
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TESTS_ROOT_DIR = Path(__file__).parent
SUBPROCESS_TIMEOUT = 30


class TestEnvironment(SerializableEnumNameMixin):
    __test__ = False  # tell pytest not to collect this class

    STANDARD = auto()  # test during normal development
    NIGHTLY = auto()  # all tests
    NFTS = auto()  # nft tests


add_logging_level('TRACE', TRACE)
configure_logging(default_args())
# sql instructions for global DB are customizable here:
# https://github.com/rotki/rotki/blob/eb5bef269207e8b84075ee36ce7c3804115ed6a0/rotkehlchen/tests/fixtures/globaldb.py#L33

from rotkehlchen.tests.fixtures import *  # noqa: F403

assert sys.version_info.major == 3, 'Need to use python 3 for rotki'
assert sys.version_info.minor == 11, 'Need to use python 3.11 for rotki'


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

    @pytest.fixture
    def tmpdir(request, tmpdir_factory):
        """Return a temporary directory path object
        which is unique to each test function invocation,
        created as a sub directory of the base temporary
        directory.  The returned object is a `py.path.local`_
        path object.
        # pytest-deadfixtures ignore
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

        now = datetime.datetime.now(tz=datetime.UTC)
        tmpdirname = tempfile.gettempdir()
        stack_path = Path(tmpdirname) / f'{now:%Y%m%d_%H%M}_stack.data'
        with open(stack_path, 'w', encoding='utf8') as stack_stream:
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
        reason=f'Not suitable environment {env} for current test',
    )


def get_cassette_dir(request: pytest.FixtureRequest) -> Path:
    """
    Directory structure for cassettes in each test file resembles the file's path
    e.g. for tests in       `tests/unit/decoders/test_aave.py`
         cassettes are in   `cassettes/unit/decoders/test_aave/`
    """
    return Path(request.node.path).relative_to(TESTS_ROOT_DIR).with_suffix('')


def is_etherscan_rate_limited(response: dict[str, Any]) -> bool:
    """Checks if etherscan is rate limited.
    Suppression is for errors parsing when response does not match etherscan"""
    rate_limited = False
    with suppress(JSONDecodeError, KeyError, UnicodeDecodeError, ValueError):
        body = jsonloads_dict(response['body']['string'])
        rate_limited = (
            int(body.get('status', 0)) == 0 and
            (body_result := body.get('result', None)) is not None and
            'rate limit reached' in body_result
        )
    return rate_limited


@pytest.fixture(scope='module', name='vcr')
def vcr_fixture(vcr: 'VCR') -> 'VCR':
    """
    Update VCR instance to discard error responses during the record mode.
    This target directly etherscan that is the service we are first focusing on
    # pytest-deadfixtures ignore
    """

    def before_record_response(response: dict[str, Any]) -> dict[str, Any] | None:
        if (
            ('RECORD_CASSETTES' in os.environ and response['status']['code'] != HTTPStatus.OK) or
            is_etherscan_rate_limited(response)
        ):
            return None

        return response

    vcr.before_record_response = before_record_response

    def beaconchain_matcher(r1, r2):
        """
        Special matcher to match the path of beaconcha.in validator query
        no matter the order of path args
        """
        if r1.uri.startswith('https://beaconcha.in/api/v1/validator/') and r2.uri.startswith('https://beaconcha.in/api/v1/validator/') and r1.uri[38:42] != 'eth1':  # noqa: E501
            return set(r1.uri[38:].split(',')) == set(r2.uri[38:].split(','))

        return r1.uri == r2.uri and r1.method == r2.method  # normal check

    def alchemy_api_matcher(r1, r2):
        """Match Alchemy price API paths, ignoring API key."""
        if (
            (base_url := 'https://api.g.alchemy.com/prices/v1/') and
            r1.uri.startswith(base_url) and
            r2.uri.startswith(base_url)
        ):
            # Extract everything after API key by finding second '/' after base_url
            path1 = r1.uri[r1.uri.find('/', len(base_url)) + 1:]
            path2 = r2.uri[r2.uri.find('/', len(base_url)) + 1:]
            return path1 == path2 and r1.method == r2.method
        return r1.uri == r2.uri and r1.method == r2.method

    def github_branch_matcher(r1, r2):
        """Match GitHub raw URLs, ignoring the branch part."""
        base_url = 'https://raw.githubusercontent.com/rotki/data/'
        if r1.uri.startswith(base_url) and r2.uri.startswith(base_url):
            # Extract path after the base URL
            path1 = r1.uri[len(base_url):].split('/')
            path2 = r2.uri[len(base_url):].split('/')
            # Compare everything except the branch (first part after base_url)
            return path1[1:] == path2[1:] and r1.method == r2.method
        return r1.uri == r2.uri and r1.method == r2.method

    vcr.register_matcher('alchemy_api_matcher', alchemy_api_matcher)
    vcr.register_matcher('beaconchain_matcher', beaconchain_matcher)
    vcr.register_matcher('github_branch_matcher', github_branch_matcher)
    return vcr


@pytest.fixture(scope='session')
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


def get_branch_distance(branch1: str, branch2: str) -> int:
    """Get the distance between branch1 and branch2 in number of commits"""
    merge_base = check_output(
        args=f'git merge-base {branch1} {branch2}',
        shell=True,
    ).decode('utf-8').strip()
    distance_to_branch1 = int(check_output(
        args=f'git rev-list --count {merge_base}..{branch1}',
        shell=True,
    ).decode('utf-8').strip())
    distance_to_branch2 = int(check_output(
        args=f'git rev-list --count {merge_base}..{branch2}',
        shell=True,
    ).decode('utf-8').strip())
    return distance_to_branch1 + distance_to_branch2


def find_closest_branch(target_branch: str) -> str:
    """Find the branch among develop and bugfixes that is closer to target_branch"""
    all_branches = ('develop', 'bugfixes', 'master')
    distances = {branch: get_branch_distance(branch, target_branch) for branch in all_branches}
    return min(distances, key=distances.get)  # type: ignore


@pytest.fixture(scope='session', name='vcr_base_dir')
def fixture_vcr_base_dir() -> Path:
    """Determine the base dir for vcr cassettes
    # pytest-deadfixtures ignore
    """
    depth_arg = ''  # In local environment we fetch all history to avoid making the local repo a shallow clone  # noqa: E501
    if 'CI' in os.environ:
        # the CI action Ensure VCR branch is fully rebased handles it. Do nothing
        # Also important since running this with xdist and -n X then this runs X
        # times and causes the CI to fail dueto inconsistencies and multi cloning
        return Path(os.environ['CASSETTES_DIR']) / 'cassettes'

    current_branch = os.environ.get('VCR_BRANCH')
    root_dir = default_data_directory().parent / 'test-caching'
    base_dir = root_dir / 'cassettes'

    # Clone repo if needed
    if (root_dir / '.git').exists() is False:
        if root_dir.exists():  # test-caching dir exists but is not a git repo
            shutil.rmtree(root_dir)  # that means accounting rules or other test-caching was pulled first. Delete and repull.  # noqa: E501

        cmd = f'git clone https://github.com/rotki/test-caching.git "{root_dir}"'
        log.debug(f'Cloning test caching repo to {root_dir}')
        os.popen(cmd).read()

    if current_branch is None:
        current_branch = os.popen('git rev-parse --abbrev-ref HEAD').read().rstrip('\n')
    log.debug(f'At VCR setup, {current_branch=} {root_dir=}')

    checkout_proc = Popen(f'cd "{root_dir}" && git fetch {depth_arg} origin && git checkout {current_branch}', env=dict(os.environ, LANG='en_US.UTF-8'), shell=True, stdout=PIPE, stderr=PIPE)  # noqa: E501
    _, stderr = checkout_proc.communicate(timeout=SUBPROCESS_TIMEOUT)

    if (
        len(stderr) != 0 and
        b'Already on' not in stderr and
        b'Switched to' not in stderr
    ):
        fallback_branch = find_closest_branch(current_branch)  # either master, develop or bugfixes but always the closest  # noqa: E501
        default_branch = os.environ.get('GITHUB_BASE_REF', os.environ.get('DEFAULT_VCR_BRANCH', fallback_branch))  # noqa: E501
        if default_branch == '' and 'CI' in os.environ:
            # In the case of the CI when the job is executed and not due to a PR then
            # GITHUB_BASE_REF is set to ''
            default_branch = 'develop'

        log.error(f'Could not find branch {current_branch} in {root_dir}. Defaulting to {default_branch}')  # noqa: E501
        checkout_proc = Popen(f'cd "{root_dir}" && git checkout {default_branch}', shell=True, stdout=PIPE, stderr=PIPE)  # noqa: E501
        _, stderr = checkout_proc.communicate(timeout=SUBPROCESS_TIMEOUT)
        if (
                len(stderr) != 0 and
                b'Already on' not in stderr and
                b'Switched to' not in stderr
        ):
            log.error(f'Could not find branch {default_branch} in {root_dir}. Bailing and leaving current branch')  # noqa: E501
            return base_dir
        current_branch = default_branch

    log.debug(f'VCR setup: Checked out test-caching {current_branch} branch')

    # see if we have any uncommitted work
    for diff_type in ('diff', 'diff --staged'):
        diff_result = os.popen(f'cd "{root_dir}" && git {diff_type}').read()
        if diff_result != '':
            log.debug('VCR setup: There is uncommitted work at the test-caching repository. Not modifying it')  # noqa: E501
            return base_dir

    # see if the branch is ahead of origin, meaning local is being worked on
    compare_result = os.popen(f'cd "{root_dir}" && git rev-list --left-right --count {current_branch}...origin/{current_branch}').read()  # noqa: E501
    result_split = compare_result.split()
    commits_ahead = 0 if len(result_split) == 0 else int(result_split[0])
    if commits_ahead > 0:
        log.debug(f'VCR setup: The local test-caching branch {current_branch} is {commits_ahead} commits ahead of the remote. Not modifying it.')  # noqa: E501
        return base_dir

    # since we got here reset to origin's equivalent branch
    reset_proc = Popen(f'cd "{root_dir}" && git reset --hard origin/{current_branch}', shell=True, stdout=PIPE, stderr=PIPE)  # noqa: E501
    _, stderr = reset_proc.communicate(timeout=SUBPROCESS_TIMEOUT)
    if len(stderr) != 0:
        prefix = 'Failed to '
        error = f' due to {stderr!r}'
    else:
        prefix = ''
        error = ''

    log.debug(f'VCR setup: {prefix}reset test caching branch: {current_branch} to match origin{error}')  # noqa: E501

    return base_dir


@pytest.fixture(scope='module')
def vcr_cassette_dir(request: pytest.FixtureRequest, vcr_base_dir) -> str:
    """
    Override pytest-vcr's bundled fixture to store cassettes outside source code
    # pytest-deadfixtures ignore
    """
    return str(vcr_base_dir / get_cassette_dir(request))
