import subprocess
from unittest.mock import patch

import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.utils.misc import get_system_spec


def test_query_version(rotkehlchen_api_server):
    """Test that endpoint to query the rotki version works fine"""

    # Test for the case that the version is up to date
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            "versionresource",
        ),
    )
    assert_proper_response(response)

    our_version = get_system_spec()['rotkehlchen']
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 3
    assert data['result']['our_version'] == our_version
    cmd = ['git', 'describe', '--abbrev=0', '--tags']
    expected_latest = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    expected_latest = expected_latest[:-1].decode()
    assert data['result']['latest_version'] == expected_latest
    assert data['result']['download_url'] is None

    # Test for the case that a newer version exists
    def patched_get_latest_release(_klass):
        new_latest = 'v99.99.99'
        return new_latest, f'https://github.com/rotki/rotki/releases/tag/{new_latest}'
    release_patch = patch(
        'rotkehlchen.externalapis.github.Github.get_latest_release',
        patched_get_latest_release,
    )
    with release_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                "versionresource",
            ),
        )
    assert_proper_response(response)
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 3
    assert data['result']['our_version'] == our_version
    assert data['result']['latest_version'] == 'v99.99.99'
    assert 'v99.99.99' in data['result']['download_url']
