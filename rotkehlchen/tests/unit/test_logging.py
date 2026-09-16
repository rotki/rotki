import logging
import re
import subprocess  # noqa: S404  # isolate logging configuration from the test runner
import sys
from typing import Any

from rotkehlchen.logging import RotkehlchenLogsAdapter, SensitiveProtocolFilter


def test_sensitive_key_redaction(caplog) -> None:
    logger = logging.getLogger(__name__)
    log = RotkehlchenLogsAdapter(logger)

    with caplog.at_level(logging.DEBUG):
        test_data: dict[str, Any] = {
            'json_data': {
                'password': 'secret',
                'new_password': 'newsecret',
                'old_password': 'oldsecret',
                'credentials': {
                    'endpoint': 'https://bank.example/fints',
                    'username': 'testuser',
                    'pin': 'secret-pin',
                },
                'other_field': 'safe',
            },
            'other_arg': 'value',
            'username': 'top-level-user',
        }
        log.debug('Test message', **test_data)
        assert "'password': '[REDACTED]'" in (log_record := caplog.records[0]).message
        assert "'new_password': '[REDACTED]'" in log_record.message
        assert "'old_password': '[REDACTED]'" in log_record.message
        assert "'credentials': '[REDACTED]'" in log_record.message
        assert 'testuser' not in log_record.message
        assert 'secret-pin' not in log_record.message
        assert 'top-level-user' not in log_record.message
        assert "'other_field': 'safe'" in log_record.message


def test_stdout_logtarget() -> None:
    result = subprocess.run(
        [sys.executable, '-c', """
import logging
from argparse import Namespace
from rotkehlchen.logging import configure_logging

configure_logging(Namespace(
    loglevel='INFO', logtarget='stdout', max_logfiles_num=5, logfromothermodules=True,
))
logging.getLogger('rotkehlchen').info('stdout logging regression')
logging.getLogger('uvicorn.error').info('third-party logging regression')
"""],
        capture_output=True,
        text=True,
        check=True,
    )
    assert 'stdout logging regression' in result.stdout
    assert 'stdout logging regression' not in result.stderr
    assert len(lines := result.stdout.splitlines()) == 2
    for line in lines:
        assert re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z \[core\] INFO ', line)
        assert '\x1b' not in line
    assert 'uvicorn.error third-party logging regression' in lines[1]


def test_fints_wire_logs_are_filtered() -> None:
    log_filter = SensitiveProtocolFilter()

    assert log_filter.filter(logging.LogRecord(
        name='fints.connection',
        level=logging.DEBUG,
        pathname='',
        lineno=0,
        msg='wire message containing user credentials',
        args=(),
        exc_info=None,
    )) is False
    assert log_filter.filter(logging.LogRecord(
        name='rotkehlchen.banks.fints',
        level=logging.DEBUG,
        pathname='',
        lineno=0,
        msg='safe connector message',
        args=(),
        exc_info=None,
    )) is True
