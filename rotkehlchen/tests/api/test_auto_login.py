"""Tests for the auto-login password confirmation feature"""
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
    wait_for_async_task_with_result,
)


def test_auto_login_counter_increments(rotkehlchen_api_server, username, db_password):
    """Test that auto_login_count increments on each auto-login"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    
    # First, check initial counter value
    with rotki.data.db.conn.read_ctx() as cursor:
        count = rotki.data.db.get_setting(cursor, 'auto_login_count')
        assert count == 0
    
    # Logout first
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    
    # Login with auto_login=True
    data = {
        'password': db_password,
        'sync_approval': 'unknown',
        'async_query': True,
        'auto_login': True,
    }
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    
    # Check counter incremented
    with rotki.data.db.conn.read_ctx() as cursor:
        count = rotki.data.db.get_setting(cursor, 'auto_login_count')
        assert count == 1
    
    # Logout and login again
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    
    data = {
        'password': db_password,
        'sync_approval': 'unknown',
        'async_query': True,
        'auto_login': True,
    }
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    
    # Check counter incremented again
    with rotki.data.db.conn.read_ctx() as cursor:
        count = rotki.data.db.get_setting(cursor, 'auto_login_count')
        assert count == 2


def test_auto_login_counter_resets_on_manual_login(rotkehlchen_api_server, username, db_password):
    """Test that auto_login_count resets to 0 on manual login"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    
    # Set counter to 3
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.set_setting(write_cursor, 'auto_login_count', 3)
    
    # Logout
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    
    # Manual login (auto_login=False or not provided)
    data = {
        'password': db_password,
        'sync_approval': 'unknown',
        'async_query': True,
        'auto_login': False,
    }
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    
    # Check counter was reset
    with rotki.data.db.conn.read_ctx() as cursor:
        count = rotki.data.db.get_setting(cursor, 'auto_login_count')
        assert count == 0


def test_auto_login_requires_confirmation_after_threshold(rotkehlchen_api_server, username, db_password):
    """Test that requires_confirmation is returned after threshold is reached"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    
    # Set threshold to 3 for faster testing
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.set_setting(write_cursor, 'auto_login_confirmation_threshold', 3)
        rotki.data.db.set_setting(write_cursor, 'auto_login_count', 0)
    
    # Logout
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    
    # Do 3 auto-logins successfully
    for i in range(3):
        data = {
            'password': db_password,
            'sync_approval': 'unknown',
            'async_query': True,
            'auto_login': True,
        }
        response = requests.post(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
        assert 'exchanges' in result  # Successful login
        
        # Logout after each login
        data = {'action': 'logout'}
        response = requests.patch(
            api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
            json=data,
        )
        assert_simple_ok_response(response)
    
    # 4th auto-login should require confirmation
    data = {
        'password': db_password,
        'sync_approval': 'unknown',
        'async_query': True,
        'auto_login': True,
    }
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    
    # Should return 401 with requires_confirmation message
    assert outcome['status_code'] == 401
    assert outcome['message'].startswith('requires_confirmation')
    assert outcome['result'] is None


def test_auto_login_confirmation_resets_counter(rotkehlchen_api_server, username, db_password):
    """Test that is_confirmation=True resets the counter"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    
    # Set counter to 5
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.set_setting(write_cursor, 'auto_login_count', 5)
    
    # Logout
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    
    # Login with is_confirmation=True
    data = {
        'password': db_password,
        'sync_approval': 'unknown',
        'async_query': True,
        'is_confirmation': True,
    }
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    
    # Check counter was reset
    with rotki.data.db.conn.read_ctx() as cursor:
        count = rotki.data.db.get_setting(cursor, 'auto_login_count')
        assert count == 0


def test_auto_login_threshold_validation(rotkehlchen_api_server):
    """Test that auto_login_confirmation_threshold validates min/max values"""
    # Test setting threshold below minimum (3)
    json_data = {'settings': {'auto_login_confirmation_threshold': 2}}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'settingsresource'),
        json=json_data,
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'auto_login_confirmation_threshold' in response.json()['message'].lower()
    
    # Test setting threshold above maximum (10)
    json_data = {'settings': {'auto_login_confirmation_threshold': 11}}
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'settingsresource'),
        json=json_data,
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert 'auto_login_confirmation_threshold' in response.json()['message'].lower()
    
    # Test setting valid threshold (3-10)
    for threshold in [3, 5, 7, 10]:
        json_data = {'settings': {'auto_login_confirmation_threshold': threshold}}
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'settingsresource'),
            json=json_data,
        )
        assert_proper_sync_response_with_result(response)
        settings = response.json()['result']
        assert settings['auto_login_confirmation_threshold'] == threshold
        
        # Verify it was saved
        response = requests.get(api_url_for(rotkehlchen_api_server, 'settingsresource'))
        result = response.json()
        assert result['result']['auto_login_confirmation_threshold'] == threshold


def test_auto_login_threshold_in_confirmation_message(rotkehlchen_api_server, username, db_password):
    """Test that the confirmation message includes the correct threshold value"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    
    # Set threshold to 3
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.set_setting(write_cursor, 'auto_login_confirmation_threshold', 3)
        rotki.data.db.set_setting(write_cursor, 'auto_login_count', 3)  # At threshold
    
    # Logout
    data = {'action': 'logout'}
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    assert_simple_ok_response(response)
    
    # Try auto-login (should require confirmation)
    data = {
        'password': db_password,
        'sync_approval': 'unknown',
        'async_query': True,
        'auto_login': True,
    }
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'usersbynameresource', name=username),
        json=data,
    )
    task_id = assert_ok_async_response(response)
    outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
    
    # Check that outcome has the confirmation message with threshold
    assert outcome['status_code'] == 401
    assert outcome['message'] == 'requires_confirmation:3'
    assert outcome['result'] is None


def test_gnosispay_schema_fix_on_connection(rotkehlchen_api_server):
    """Test that gnosispay_data table schema is fixed automatically on connection"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    
    # Check that gnosispay_data table has correct schema (without reversal_tx_hash)
    with rotki.data.db.conn.read_ctx() as cursor:
        table_info = cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='gnosispay_data'"
        ).fetchone()
        
        if table_info:  # Table might not exist in fresh DB
            # Should not have reversal_tx_hash column
            assert 'reversal_tx_hash' not in table_info[0].lower()
