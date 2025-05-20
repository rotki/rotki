import logging

from rotkehlchen.logging import RotkehlchenLogsAdapter


def test_sensitive_key_redaction(caplog):
    logger = logging.getLogger(__name__)
    log = RotkehlchenLogsAdapter(logger)

    with caplog.at_level(logging.DEBUG):
        test_data = {
            'json_data': {
                'username': 'testuser',
                'password': 'secret',
                'new_password': 'newsecret',
                'old_password': 'oldsecret',
                'other_field': 'safe',
            },
            'other_arg': 'value',
        }
        log.debug('Test message', **test_data)
        assert "'password': '[REDACTED]'" in (log_record := caplog.records[0]).message
        assert "'new_password': '[REDACTED]'" in log_record.message
        assert "'old_password': '[REDACTED]'" in log_record.message
