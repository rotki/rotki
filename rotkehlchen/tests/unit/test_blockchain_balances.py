from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.balances import BlockchainBalances
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH, A_LQTY, A_LUSD, A_POLYGON_POS_MATIC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, make_evm_address
from rotkehlchen.tests.utils.xpubs import setup_db_for_xpub_tests_impl
from rotkehlchen.types import ChainID, EvmTokenKind, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator

OPTIMISM_OP_TOKEN = EvmToken.initialize(
    address=string_to_evm_address('0x4200000000000000000000000000000000000042'),
    chain_id=ChainID.OPTIMISM,
    token_kind=EvmTokenKind.ERC20,
)
OPTIMISM_USDC_TOKEN = EvmToken.initialize(
    address=string_to_evm_address('0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
    chain_id=ChainID.OPTIMISM,
    token_kind=EvmTokenKind.ERC20,
)

ETH_ADDRESS1 = string_to_evm_address('0xbB8311c7bAD518f0D8f907Cad26c5CcC85a06dC4')
ETH_ADDRESS2 = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')


@pytest.fixture(name='use_db')
def fixture_use_db():
    return False


@pytest.fixture(name='blockchain_balances')
def fixture_blockchain_balances(use_db, data_dir, username, sql_vm_instructions_cb):
    if use_db is True:
        db, _, xpub2, _, all_btc_addresses = setup_db_for_xpub_tests_impl(data_dir, username, sql_vm_instructions_cb)  # noqa: E501
        xpub_data = xpub2
        a = BlockchainBalances(db)
        for btc_addy in all_btc_addresses:
            a.btc[btc_addy] = Balance(amount=1, usd_value=1)
    else:
        a = BlockchainBalances(None)
        a.btc[UNIT_BTC_ADDRESS1] = Balance(amount=1, usd_value=1)
        a.bch[UNIT_BTC_ADDRESS1] = Balance(amount=1, usd_value=1)
        all_btc_addresses = (UNIT_BTC_ADDRESS1,)
        xpub_data = None

    address1 = make_evm_address()
    address2 = make_evm_address()
    a.eth[address1] = BalanceSheet()
    a.eth[address1].assets[A_ETH] = Balance(amount=1, usd_value=1)
    a.optimism[address2].assets[OPTIMISM_OP_TOKEN] = Balance(amount=1, usd_value=1)
    a.optimism[address2].assets[A_ETH] = Balance(amount=1, usd_value=1)

    return a, address1, address2, all_btc_addresses, xpub_data


def test_copy():
    a = BlockchainBalances(None)
    address = make_evm_address()
    a.eth[address] = BalanceSheet()
    a.eth[address].assets['ETH'] = Balance(amount=1, usd_value=1)
    b = a.copy()

    a.eth[address].assets['ETH'] += Balance(1, 1)

    assert a.eth[address].assets['ETH'] == Balance(2, 2)
    assert b.eth[address].assets['ETH'] == Balance(1, 1)


def test_recalculate_totals(blockchain_balances):
    a, address1, address2, _, _ = blockchain_balances
    assert a.recalculate_totals() == BalanceSheet(
        assets={
            OPTIMISM_OP_TOKEN: Balance(1, 1),
            A_ETH: Balance(2, 2),
            A_BTC: Balance(1, 1),
            A_BCH: Balance(1, 1),
        },
    )

    # do a change and see it's taken into account at recalculate
    a.eth[address2] = BalanceSheet()
    a.eth[address2].assets[A_ETH] = Balance(amount=1, usd_value=1)
    a.eth[address1].assets[A_ETH] = Balance(amount=4, usd_value=4)
    a.bch[UNIT_BTC_ADDRESS1] = Balance(amount=5, usd_value=5)
    a.optimism[address2].assets[OPTIMISM_USDC_TOKEN] = Balance(amount=100, usd_value=100)
    a.optimism[address2].assets.pop('ETH')
    assert a.recalculate_totals() == BalanceSheet(
        assets={
            OPTIMISM_OP_TOKEN: Balance(1, 1),
            OPTIMISM_USDC_TOKEN: Balance(100, 100),
            A_ETH: Balance(5, 5),
            A_BTC: Balance(1, 1),
            A_BCH: Balance(5, 5),
        },
    )


@pytest.mark.parametrize('use_db', [True])
def test_serialize(blockchain_balances):
    a, address1, address2, _, xpub_data = blockchain_balances
    optimism_chain_key = SupportedBlockchain.OPTIMISM.serialize()
    ethereum_chain_key = SupportedBlockchain.ETHEREUM.serialize()
    expected_serialized_dict = {
        SupportedBlockchain.BITCOIN.serialize(): {
            'standalone': {
                '12wxFzpjdymPk3xnHmdDLCTXUT9keY3XRd': {'amount': '1', 'usd_value': '1'},
                '16zNpyv8KxChtjXnE5nYcPqcXcrSQXX2JW': {'amount': '1', 'usd_value': '1'},
                '16zNpyv8KxChtjXnE5oYcPqcXcrSQXX2JJ': {'amount': '1', 'usd_value': '1'},
                '1LZypJUwJJRdfdndwvDmtAjrVYaHko136r': {'amount': '1', 'usd_value': '1'},
                '1MKSdDCtBSXiE49vik8xUG2pTgTGGh5pqe': {'amount': '1', 'usd_value': '1'}},
            'xpubs': [
                {
                    'addresses': {
                        'bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5': {'amount': '1', 'usd_value': '1'},  # noqa: E501
                        'bc1qnus7355ecckmeyrmvv56mlm42lxvwa4wuq5aev': {'amount': '1', 'usd_value': '1'},  # noqa: E501
                        'bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra': {'amount': '1', 'usd_value': '1'},  # noqa: E501
                        'bc1qr5r8vryfzexvhjrx5fh5uj0s2ead8awpqspalz': {'amount': '1', 'usd_value': '1'},  # noqa: E501
                        'bc1qup7f8g5k3h5uqzfjed03ztgn8hhe542w69wc0g': {'amount': '1', 'usd_value': '1'},  # noqa: E501
                    },
                    'derivation_path': 'm/0',
                    'xpub': xpub_data.xpub.xpub}]},
        ethereum_chain_key: {
            address1: {
                'assets': {
                    'ETH': {'amount': '1', 'usd_value': '1'},
                },
                'liabilities': {},
            },
        },
        optimism_chain_key: {
            address2: {
                'assets': {
                    'ETH': {'amount': '1', 'usd_value': '1'},
                    OPTIMISM_OP_TOKEN.serialize(): {'amount': '1', 'usd_value': '1'},
                },
                'liabilities': {},
            },
        },
    }
    assert a.serialize(given_chain=None) == expected_serialized_dict

    # change something and see it is also reflected in the serialized dict
    a.optimism[address2].assets[OPTIMISM_USDC_TOKEN] = Balance(amount=100, usd_value=100)
    expected_serialized_dict[optimism_chain_key][address2]['assets'][OPTIMISM_USDC_TOKEN.serialize()] = {'amount': '100', 'usd_value': '100'}  # noqa: E501
    a.eth[address1].assets.pop(A_ETH.identifier)
    expected_serialized_dict[ethereum_chain_key][address1] = {'assets': {}, 'liabilities': {}}
    assert a.serialize(given_chain=None) == expected_serialized_dict


@pytest.mark.parametrize('ethereum_accounts', [[ETH_ADDRESS1, ETH_ADDRESS2]])
@pytest.mark.parametrize('ethereum_modules', [['liquity']])
@pytest.mark.parametrize('should_mock_web3', [True])
@pytest.mark.parametrize('ethereum_mock_data', [{
    'eth_call': {
        '0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696': {
            '0x252dba4200000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000004678f0a6958e4d2bc4f1baf7bc52e8f3564f3fe400000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024c4552791000000000000000000000000bb8311c7bad518f0d8f907cad26c5ccc85a06dc4000000000000000000000000000000000000000000000000000000000000000000000000000000004678f0a6958e4d2bc4f1baf7bc52e8f3564f3fe400000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024c4552791000000000000000000000000c37b40abdb939635068d3c5f13e7faf686f03b6500000000000000000000000000000000000000000000000000000000': {  # noqa: E501
                # calling addr() on resolver for bruno.eth
                'latest': '0x0000000000000000000000000000000000000000000000000000000000fa75210000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000002000000000000000000000000033eafdb72b69bfbe6b5911edcbab41011e63c52300000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000',  # noqa: E501
            },
            '0xbce38bd70000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001a0000000000000000000000000a39739ef8b0231dbfa0dcda07d7e29faabcf4bb2000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000246ef64338000000000000000000000000bb8311c7bad518f0d8f907cad26c5ccc85a06dc400000000000000000000000000000000000000000000000000000000000000000000000000000000a39739ef8b0231dbfa0dcda07d7e29faabcf4bb2000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000246ef64338000000000000000000000000c37b40abdb939635068d3c5f13e7faf686f03b6500000000000000000000000000000000000000000000000000000000000000000000000000000000a39739ef8b0231dbfa0dcda07d7e29faabcf4bb2000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000246ef6433800000000000000000000000033eafdb72b69bfbe6b5911edcbab41011e63c52300000000000000000000000000000000000000000000000000000000': {  # noqa: E501
                # calling addr() on resolver for bruno.eth and coin type Bitcoin
                'latest': '0x000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000060000000000000000000000000000000000000000000000000000000000000016000000000000000000000000000000000000000000000000000000000000002600000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000004bb',  # noqa: E501
            },
            '0xbce38bd7000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000009000000000000000000000000000000000000000000000000000000000000012000000000000000000000000000000000000000000000000000000000000001c00000000000000000000000000000000000000000000000000000000000000260000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000003a0000000000000000000000000000000000000000000000000000000000000044000000000000000000000000000000000000000000000000000000000000004e0000000000000000000000000000000000000000000000000000000000000058000000000000000000000000000000000000000000000000000000000000006200000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002416934fc4000000000000000000000000bb8311c7bad518f0d8f907cad26c5ccc85a06dc4000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000249beab5c0000000000000000000000000bb8311c7bad518f0d8f907cad26c5ccc85a06dc4000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000248b9345ad000000000000000000000000bb8311c7bad518f0d8f907cad26c5ccc85a06dc4000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002416934fc4000000000000000000000000c37b40abdb939635068d3c5f13e7faf686f03b65000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000249beab5c0000000000000000000000000c37b40abdb939635068d3c5f13e7faf686f03b65000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000248b9345ad000000000000000000000000c37b40abdb939635068d3c5f13e7faf686f03b65000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002416934fc400000000000000000000000033eafdb72b69bfbe6b5911edcbab41011e63c523000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000249beab5c000000000000000000000000033eafdb72b69bfbe6b5911edcbab41011e63c523000000000000000000000000000000000000000000000000000000000000000000000000000000004f9fbb3f1e99b56e0fe2892e623ed36a76fc605d000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000248b9345ad00000000000000000000000033eafdb72b69bfbe6b5911edcbab41011e63c52300000000000000000000000000000000000000000000000000000000': {  # noqa: E501
                # calling addr() on resolver for bruno.eth and coin type Bitcoin
                'latest': '0x00000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000009000000000000000000000000000000000000000000000000000000000000012000000000000000000000000000000000000000000000000000000000000001a0000000000000000000000000000000000000000000000000000000000000022000000000000000000000000000000000000000000000000000000000000002a0000000000000000000000000000000000000000000000000000000000000032000000000000000000000000000000000000000000000000000000000000003a0000000000000000000000000000000000000000000000000000000000000042000000000000000000000000000000000000000000000000000000000000004a000000000000000000000000000000000000000000000000000000000000005200000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000e5de89ebb73fe2000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000cc6c67e55d6d06c9800000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000671456237cc29300000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000029a8276382addd6510400000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000012976d58da16038ed02000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000031f4bd761148ee2',  # noqa: E501
            },
            '0xbce38bd7000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000009000000000000000000000000000000000000000000000000000000000000012000000000000000000000000000000000000000000000000000000000000001c00000000000000000000000000000000000000000000000000000000000000260000000000000000000000000000000000000000000000000000000000000030000000000000000000000000000000000000000000000000000000000000003a0000000000000000000000000000000000000000000000000000000000000044000000000000000000000000000000000000000000000000000000000000004e00000000000000000000000000000000000000000000000000000000000000580000000000000000000000000000000000000000000000000000000000000062000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024389e92a5000000000000000000000000bb8311c7bad518f0d8f907cad26c5ccc85a06dc40000000000000000000000000000000000000000000000000000000000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024f5f1595d000000000000000000000000bb8311c7bad518f0d8f907cad26c5ccc85a06dc40000000000000000000000000000000000000000000000000000000000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000241cdc4700000000000000000000000000bb8311c7bad518f0d8f907cad26c5ccc85a06dc40000000000000000000000000000000000000000000000000000000000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024389e92a5000000000000000000000000c37b40abdb939635068d3c5f13e7faf686f03b650000000000000000000000000000000000000000000000000000000000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024f5f1595d000000000000000000000000c37b40abdb939635068d3c5f13e7faf686f03b650000000000000000000000000000000000000000000000000000000000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000241cdc4700000000000000000000000000c37b40abdb939635068d3c5f13e7faf686f03b650000000000000000000000000000000000000000000000000000000000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024389e92a500000000000000000000000033eafdb72b69bfbe6b5911edcbab41011e63c5230000000000000000000000000000000000000000000000000000000000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000024f5f1595d00000000000000000000000033eafdb72b69bfbe6b5911edcbab41011e63c5230000000000000000000000000000000000000000000000000000000000000000000000000000000066017d22b0f8556afdd19fc67041899eb65a21bb000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000241cdc470000000000000000000000000033eafdb72b69bfbe6b5911edcbab41011e63c52300000000000000000000000000000000000000000000000000000000': {  # noqa: E501
                # calling addr() on resolver for bruno.eth and coin type Bitcoin
                'latest': '0x00000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000009000000000000000000000000000000000000000000000000000000000000012000000000000000000000000000000000000000000000000000000000000001a0000000000000000000000000000000000000000000000000000000000000022000000000000000000000000000000000000000000000000000000000000002a0000000000000000000000000000000000000000000000000000000000000032000000000000000000000000000000000000000000000000000000000000003a0000000000000000000000000000000000000000000000000000000000000042000000000000000000000000000000000000000000000000000000000000004a00000000000000000000000000000000000000000000000000000000000000520000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000011bb8394a3922da4180000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000001644c9c43e2d557b860000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000c7225657a489ae317dd000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000',  # noqa: E501
            },
        },
    },
}])
def test_protocol_balances(blockchain: 'ChainsAggregator') -> None:
    """
    Test that liquity is injected in balances properly when querying module balances.
    ETH_ADDRESS1 has a DSProxy with deposits in liquity and ETH_ADDRESS2 doesn't have anything
    """
    blockchain._add_eth_protocol_balances(eth_balances=blockchain.balances.eth)
    # the proxy balances are added to the owner's
    assert blockchain.balances.eth[ETH_ADDRESS1].assets == {
        A_LQTY: Balance(
            amount=FVal('16535.272316119505457412'),
            usd_value=FVal('24802.9084741792581861180'),
        ),
        A_LUSD: Balance(
            amount=FVal('58774.021313242937366493'),
            usd_value=FVal('88161.0319698644060497395'),
        ),
    }
    assert ETH_ADDRESS2 not in blockchain.balances.eth


LLAMA_NODE = WeightedNode(
    node_info=NodeName(
        name='DefiLlama',
        endpoint='https://polygon.llamarpc.com',
        owned=False,
        blockchain=SupportedBlockchain.POLYGON_POS,
    ),
    active=True,
    weight=ONE,
)


@pytest.mark.vcr()
@pytest.mark.parametrize('polygon_pos_manager_connect_at_start', [[LLAMA_NODE]])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_native_token_balance(blockchain):
    """
    Test that for different blockchains different assets are used as native tokens.
    We test it by requesting a Polygon POS balance and checking MATIC balance.
    """
    def mock_default_call_order(skip_etherscan: bool = False):  # pylint: disable=unused-argument
        return [LLAMA_NODE]  # Keep only one node to remove randomness, and thus make it vcr'able

    with patch.object(
        blockchain.polygon_pos.node_inquirer,
        'default_call_order',
        mock_default_call_order,
    ):
        blockchain.polygon_pos.tokens.detect_tokens(
            only_cache=False,
            addresses=[string_to_evm_address('0x4bBa290826C253BD854121346c370a9886d1bC26')],
        )
        blockchain.query_polygon_pos_balances()
        assert blockchain.balances.polygon_pos == {
            '0x4bBa290826C253BD854121346c370a9886d1bC26': BalanceSheet(
                assets={
                    A_POLYGON_POS_MATIC: Balance(
                        amount=FVal('18.3848'),
                        usd_value=FVal('27.57720'),
                    ),
                    Asset('eip155:137/erc20:0x0B91B07bEb67333225A5bA0259D55AeE10E3A578'): Balance(  # Minerum  # noqa: E501
                        amount=FVal('300000'),
                        usd_value=FVal('450000.0'),
                    ),
                    Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'): Balance(  # USDC  # noqa: E501
                        amount=FVal('29.982'),
                        usd_value=FVal('44.9730'),
                    ),
                    Asset('eip155:137/erc20:0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619'): Balance(  # WETH  # noqa: E501
                        amount=FVal('0.009792189476215069'),
                        usd_value=FVal('0.0146882842143226035'),
                    ),
                },
                liabilities={},
            ),
        }
