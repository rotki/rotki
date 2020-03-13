import os
import sys
import traceback

import gevent
import pytest

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.typing import ExternalService, ExternalServiceApiCredentials
from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(scope='function')
def temp_etherscan(database, inquirer, function_scope_messages_aggregator, tmpdir_factory):
    api_key = os.environ.get('ETHERSCAN_API_KEY', None)
    if not api_key:
        pytest.fail('No ETHERSCAN_API_KEY environment variable found.')
    directory = tmpdir_factory.mktemp('data')
    msg_aggregator = MessagesAggregator()
    db = DBHandler(user_data_dir=directory, password='123', msg_aggregator=msg_aggregator)
    db.add_external_service_credentials(credentials=[
        ExternalServiceApiCredentials(service=ExternalService.ETHERSCAN, api_key=api_key),
    ])
    etherscan = Etherscan(database=db, msg_aggregator=msg_aggregator)
    return etherscan


def _handle_killed_greenlets(greenlet: gevent.Greenlet) -> None:

    tb = ''.join(traceback.format_tb(greenlet.exc_info[2]))
    message = ('Greenlet died with exception: {}.\n'
               'Exception Name: {}\nException Info: {}\nTraceback:\n {}'
               .format(
                   greenlet.exception,
                   greenlet.exc_info[0],
                   greenlet.exc_info[1],
                   tb,
               ))

    print(message)
    sys.exit(1)


@pytest.mark.skipif(
    'TRAVIS' in os.environ,
    reason='no real etherscan tests in Travis yet due to API key',
)
def test_maximum_rate_limit_reached(temp_etherscan):
    """
    Test that we can handle etherscan's rate limit repsponse properly

    Regression test for https://github.com/rotki/rotki/issues/772"
    """
    etherscan = temp_etherscan

    # Spam with concurrent requests for a bit. This triggers the problem
    count = 200
    while count > 0:
        greenlet = gevent.spawn(
            etherscan.get_account_balance,
            '0x25a63509FEF5D23FF226eb8004A3c1458D6F3AB8')
        greenlet.link_exception(_handle_killed_greenlets)
        greenlet = gevent.spawn(
            etherscan.eth_call,
            '0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4',
            '0xc455279100000000000000000000000027a2eaaa8bebea8d23db486fb49627c165baacb5',
        )
        greenlet.link_exception(_handle_killed_greenlets)
        gevent.sleep(0.001)
        count -= 1
