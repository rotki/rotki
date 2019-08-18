import json
import os
from pathlib import Path

import pytest

from rotkehlchen.exchanges.binance import Binance, create_binance_symbols_to_pair
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


@pytest.fixture
def function_scope_binance(
        accounting_data_dir,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    binance = Binance(
        api_key=make_api_key(),
        secret=make_api_secret(),
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
