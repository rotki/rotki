from contextlib import ExitStack
from unittest.mock import patch

import pytest
from packaging.version import Version

from rotkehlchen.db.updates import RotkiDataUpdater
from rotkehlchen.utils.version_check import VersionCheckResult


@pytest.fixture(name='our_version')
def fixture_our_version():
    """Allow mocking our rotki version since in CI version is 0 and hard to control"""
    return None


@pytest.fixture(name='data_updater')
def fixture_data_updater(messages_aggregator, database, our_version):
    """Initialize the DataUpdater object, optionally mocking our rotki version"""
    with ExitStack() as stack:
        if our_version is not None:
            stack.enter_context(patch('rotkehlchen.db.updates.get_current_version', return_value=VersionCheckResult(our_version=Version(our_version))))  # noqa: E501
        return RotkiDataUpdater(
            msg_aggregator=messages_aggregator,
            user_db=database,
        )
