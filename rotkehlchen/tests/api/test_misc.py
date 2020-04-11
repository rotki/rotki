from typing import Any, Dict
from unittest.mock import patch

import requests

from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.utils.misc import get_system_spec


def test_query_version_when_up_to_date(rotkehlchen_api_server):
    """Test that endpoint to query the rotki version works if no new version is available"""
    expected_version = 'v1.1.0'

    def patched_get_system_spec() -> Dict[str, Any]:
        return {'rotkehlchen': expected_version}

    def patched_get_latest_release(_klass):
        return expected_version, f'https://github.com/rotki/rotki/releases/tag/{expected_version}'
    release_patch = patch(
        'rotkehlchen.externalapis.github.Github.get_latest_release',
        patched_get_latest_release,
    )
    version_patch = patch(
        'rotkehlchen.utils.version_check.get_system_spec',
        patched_get_system_spec,
    )

    with version_patch, release_patch:
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
    assert data['result']['our_version'] == expected_version
    assert data['result']['latest_version'] == expected_version
    assert data['result']['download_url'] is None


def test_query_ping(rotkehlchen_api_server):
    """Test that the ping endpoint works"""
    expected_result = True
    expected_message = ''

    response = requests.get(api_url_for(rotkehlchen_api_server, "pingresource"))
    assert_proper_response(response)
    response_json = response.json()
    assert len(response_json) == 2
    assert response_json['result'] == expected_result
    assert response_json['message'] == expected_message


def test_query_version_when_update_required(rotkehlchen_api_server):
    """Test that endpoint to query version works when a new version is available"""
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
    our_version = get_system_spec()['rotkehlchen']
    data = response.json()
    assert data['message'] == ''
    assert len(data['result']) == 3
    assert data['result']['our_version'] == our_version
    assert data['result']['latest_version'] == 'v99.99.99'
    assert 'v99.99.99' in data['result']['download_url']
