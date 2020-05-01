import logging

import pytest

from rotkehlchen.fval import FVal
from rotkehlchen.logging import LoggingSettings, RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@pytest.mark.parametrize('anonymized_logs', [True, False])
def test_log_anonymization(anonymized_logs, caplog):
    """Tests the implementation of sensitive log anonymization"""
    caplog.set_level(logging.INFO)
    LoggingSettings(anonymized_logs=anonymized_logs)
    log_keys = {
        'amount': 55,
        'cost': FVal('10.5'),
        'gas': 33333333333333,
        'fee': FVal('0.0001'),
        'timestamp': 1577003884,
        'eth_address': '0x52bc44d5378309ee2abf1539bf71de1b7d7be3b5',
        'eth_accounts': [
            '0x52bc44d5378309ee2abf1539bf71de1b7d7be3b5',
            '0xfeb0670822d4c9c8ae7b02dc7bf095251ce42ced',
        ],
        'tx_hash': '0x16dac02d1e3597eed3b6bc645b9d7c59554bb07c2a90219af1b761924d5ef7db',
    }
    log.info(
        'Testing anonymization',
        sensitive_log=True,
        **log_keys,
    )

    assert 'sensitive_log' not in caplog.text, 'The sensitive log attribute should be deleted'

    for key, value in log_keys.items():
        entry = f'{key}={str(value)}'
        if anonymized_logs:
            assert key + '=' in caplog.text
            msg = f'{key} entry should have been modified'
            assert entry not in caplog.text or entry + ',' not in caplog.text, msg
        else:
            msg = f'{key} entry should not have been modified'
            assert entry in caplog.text or entry + ',' in caplog.text
