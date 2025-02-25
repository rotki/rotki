from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.ethereum.modules.liquity.trove import Liquity
from rotkehlchen.fval import FVal
from rotkehlchen.types import Price

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


TEST_ACCOUNTS = [
    # For mint/redeem
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    # For borrowing/liquidations
    '0xC440f3C87DC4B6843CABc413916220D4f4FeD117',
    # For mint/redeem + comp
    '0xF59D4937BF1305856C3a267bB07791507a3377Ee',
    # For repay
    '0x65304d6aff5096472519ca86a6a1fea31cb47Ced',
]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [TEST_ACCOUNTS])
def test_liquity_tcr_non_exact_int(ethereum_inquirer: 'EthereumInquirer'):
    liquity = Liquity(
        ethereum_inquirer=ethereum_inquirer,
        database=ethereum_inquirer.database,
        premium=None,
        msg_aggregator=ethereum_inquirer.database.msg_aggregator,
    )
    tcr = liquity._calculate_total_collateral_ratio(
        eth_price=Price(FVal('3014.3297469828553224123')),
    )
    assert tcr == FVal('559.5721380010671944')
