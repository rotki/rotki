import operator
from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.constants.assets import A_BTC, A_DAI
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.blockchain import mock_beaconchain, mock_etherscan_query
from rotkehlchen.typing import SupportedBlockchain


def test_query_btc_balances(blockchain):
    blockchain.query_btc_balances()
    assert 'BTC' not in blockchain.totals.assets

    account = '3BZU33iFcAiyVyu2M2GhEpLNuh81GymzJ7'
    blockchain.modify_btc_account(account, 'append', operator.add)

    blockchain.query_btc_balances()
    assert blockchain.totals.assets[A_BTC].usd_value is not None
    assert blockchain.totals.assets[A_BTC].amount is not None


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_multiple_concurrent_ethereum_blockchain_queries(blockchain):
    """Test that if there is multiple concurrent ETH blockchain queries
    we don't end up double counting:
    (1) the DeFi balances (2) the protocol balances such as DSR / makerdao vaults etc.
    """
    addr1 = '0xe188c6BEBB81b96A65aa20dDB9e2aef62627fa4c'
    addr2 = '0x78a087fCf440315b843632cFd6FDE6E5adcCc2C2'
    etherscan_patch = mock_etherscan_query(
        eth_map={addr1: {'ETH': 1, 'DAI': 1 * 10**18}, addr2: {'ETH': 2}},
        etherscan=blockchain.ethereum.etherscan,
        original_requests_get=requests.get,
        original_queries=[],
    )
    ethtokens_max_chunks_patch = patch(
        'rotkehlchen.chain.ethereum.tokens.ETHERSCAN_MAX_TOKEN_CHUNK_LENGTH',
        new=800,
    )
    beaconchain_patch = mock_beaconchain(
        blockchain.beaconchain,
        original_queries=None,
        original_requests_get=requests.get,
    )

    def mock_query_defi_balances():
        blockchain.defi_balances = {
            addr1: [DefiProtocolBalances(
                protocol=DefiProtocol('a', 'b', 'c', 1),
                balance_type='Asset',
                base_balance=DefiBalance(
                    token_address=A_DAI.ethereum_address,
                    token_name='DAI',
                    token_symbol='DAI',
                    balance=Balance(amount=FVal(1), usd_value=(1)),
                ),
                underlying_balances=[DefiBalance(
                    token_address=A_DAI.ethereum_address,
                    token_name='DAI',
                    token_symbol='DAI',
                    balance=Balance(amount=FVal(1), usd_value=(1)),
                )],
            )],
        }
        return blockchain.defi_balances

    defi_balances_mock = patch.object(
        blockchain,
        'query_defi_balances',
        wraps=mock_query_defi_balances,
    )

    def mock_add_defi_balances_to_token_and_totals():
        """This function will make sure all greenlets end up hitting the balance addition
        at the same time thus double +++ counting balance ... in the way the code
        was written before"""
        gevent.sleep(2)  # make sure all greenlets stop here
        # and then let them all go in the same time in the adding
        for account, defi_balances in blockchain.defi_balances.items():
            blockchain._add_account_defi_balances_to_token_and_totals(
                account=account,
                balances=defi_balances,
            )

    add_defi_mock = patch.object(
        blockchain,
        'add_defi_balances_to_token_and_totals',
        wraps=mock_add_defi_balances_to_token_and_totals,
    )

    with etherscan_patch, ethtokens_max_chunks_patch:
        blockchain.add_blockchain_accounts(
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[addr1, addr2],
        )
    assert addr1 in blockchain.accounts.eth

    with etherscan_patch, ethtokens_max_chunks_patch, defi_balances_mock, add_defi_mock, beaconchain_patch:  # noqa: E501
        greenlets = [
            gevent.spawn_later(0.01 * x, blockchain.query_ethereum_balances, False)
            for x in range(5)
        ]
        gevent.joinall(greenlets)

    assert blockchain.totals.assets['DAI'].amount == 2
    assert blockchain.balances.eth[addr1].assets['DAI'].amount == 2
