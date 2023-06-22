from unittest.mock import patch

import pytest

from rotkehlchen.chain.ethereum.modules.uniswap.uniswap import Uniswap
from rotkehlchen.premium.premium import Premium


@pytest.fixture()
def mock_uniswap(
        ethereum_inquirer,
        database,
        start_with_valid_premium,
        rotki_premium_credentials,
        function_scope_messages_aggregator,
) -> Uniswap:
    premium = Premium(rotki_premium_credentials) if start_with_valid_premium else None
    uniswap = Uniswap(
        ethereum_inquirer=ethereum_inquirer,
        database=database,
        premium=premium,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return uniswap
