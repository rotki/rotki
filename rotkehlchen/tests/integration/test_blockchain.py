from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH
from rotkehlchen.tests.utils.blockchain import mock_beaconchain, mock_etherscan_query
from rotkehlchen.types import SupportedBlockchain


def test_query_btc_balances(blockchain):
    blockchain.query_btc_balances()
    assert 'BTC' not in blockchain.totals.assets

    account = '3BZU33iFcAiyVyu2M2GhEpLNuh81GymzJ7'
    blockchain.add_blockchain_accounts(SupportedBlockchain.BITCOIN, accounts=[account])

    blockchain.query_btc_balances()
    assert blockchain.totals.assets[A_BTC].usd_value is not None
    assert blockchain.totals.assets[A_BTC].amount is not None


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_multiple_concurrent_ethereum_blockchain_queries(blockchain):
    """Test that if there is multiple concurrent ETH blockchain queries
    we don't end up double counting:
    (1) the DeFi balances (2) the protocol balances such as DSR / makerdao vaults etc.
    """
    addr1 = string_to_evm_address('0xe188c6BEBB81b96A65aa20dDB9e2aef62627fa4c')
    addr2 = string_to_evm_address('0x78a087fCf440315b843632cFd6FDE6E5adcCc2C2')
    etherscan_patch = mock_etherscan_query(
        eth_map={addr1: {A_ETH: 1, A_DAI: 1 * 10**18}, addr2: {A_ETH: 2}},
        etherscan=blockchain.ethereum.etherscan,
        original_requests_get=requests.get,
        original_queries=None,
        extra_flags=None,
    )
    evmtokens_max_chunks_patch = patch(
        'rotkehlchen.chain.evm.tokens.ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT',
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
                    token_address=A_DAI.resolve_to_evm_token().evm_address,
                    token_name='DAI',
                    token_symbol='DAI',
                    balance=Balance(amount=ONE, usd_value=ONE),
                ),
                underlying_balances=[DefiBalance(
                    token_address=A_DAI.resolve_to_evm_token().evm_address,
                    token_name='DAI',
                    token_symbol='DAI',
                    balance=Balance(amount=ONE, usd_value=ONE),
                )],
            )],
        }
        return blockchain.defi_balances

    defi_balances_mock = patch.object(
        blockchain,
        'query_defi_balances',
        wraps=mock_query_defi_balances,
    )

    def mock_add_defi_balances_to_account():
        """This function will make sure all greenlets end up hitting the balance addition
        at the same time thus double +++ counting balance ... in the way the code
        was written before"""
        gevent.sleep(2)  # make sure all greenlets stop here
        # and then let them all go in the same time in the adding
        for account, defi_balances in blockchain.defi_balances.items():
            blockchain._add_account_defi_balances_to_token(
                account=account,
                balances=defi_balances,
            )

    add_defi_mock = patch.object(
        blockchain,
        'add_defi_balances_to_account',
        wraps=mock_add_defi_balances_to_account,
    )

    with etherscan_patch, evmtokens_max_chunks_patch:
        blockchain.add_blockchain_accounts(
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=[addr1, addr2],
        )
        evmtokens = EvmTokens(database=blockchain.database, manager=blockchain.ethereum)
        evmtokens.detect_tokens(
            only_cache=False,
            addresses=[addr1, addr2],
        )

    assert addr1 in blockchain.accounts.eth

    with etherscan_patch, evmtokens_max_chunks_patch, defi_balances_mock, add_defi_mock, beaconchain_patch:  # noqa: E501
        greenlets = [
            # can't call query_ethereum_balances directly since we have to update totals
            gevent.spawn_later(0.01 * x, blockchain.query_balances, blockchain=SupportedBlockchain.ETHEREUM)  # noqa: E501
            for x in range(5)
        ]
        gevent.joinall(greenlets)

    assert blockchain.totals.assets[A_DAI].amount == 2
    assert blockchain.balances.eth[addr1].assets[A_DAI].amount == 2
