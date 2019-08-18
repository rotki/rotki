import base64
import json
import os
from pathlib import Path

import pytest

from rotkehlchen.exchanges.binance import Binance, create_binance_symbols_to_pair
from rotkehlchen.tests.utils.factories import make_random_b64bytes


@pytest.fixture
def function_scope_binance(
        accounting_data_dir,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    binance = Binance(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        secret=base64.b64encode(make_random_b64bytes(128)),
        user_directory=accounting_data_dir,
        msg_aggregator=function_scope_messages_aggregator,
    )
    this_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = Path(this_dir).parent.parent / 'utils' / 'data' / 'binance_exchange_info.json'
    with json_path.open('r') as f:
        json_data = json.loads(f.read())

    binance._symbols_to_pair = create_binance_symbols_to_pair(json_data)
    binance.first_connection_made = True
    return binance
