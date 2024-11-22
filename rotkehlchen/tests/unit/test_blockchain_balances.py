from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.balances import BlockchainBalances
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH, A_LQTY, A_LUSD, A_POLYGON_POS_MATIC
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, make_evm_address
from rotkehlchen.tests.utils.xpubs import setup_db_for_xpub_tests_impl
from rotkehlchen.types import ChainID, ChecksumEvmAddress, EvmTokenKind, SupportedBlockchain

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

    yield a, address1, address2, all_btc_addresses, xpub_data
    if use_db is True:
        db.logout()


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
        '0xA39739EF8b0231DbFA0DcdA07d7e29faAbCf4bb2': {  # since it queries the total collateral ratio also  # noqa: E501
            '0xb82f263d00000000000000000000000000000000000000000000000014d1120d7b160000': {
                'latest': '0x0000000000000000000000000000000000000000000000000000000000000001',
            },
        },
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


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_native_token_balance(
        blockchain: 'ChainsAggregator',
        polygon_pos_accounts: list[ChecksumEvmAddress],
):
    """
    Test that for different blockchains different assets are used as native tokens.
    We test it by requesting a Polygon POS balance and checking MATIC balance.
    """
    address = polygon_pos_accounts[0]
    sorted_call_order = sorted(blockchain.polygon_pos.node_inquirer.default_call_order())  # type: ignore

    def mock_default_call_order(skip_etherscan: bool = False):  # pylint: disable=unused-argument
        # return sorted_call_order to remove randomness, and thus make it vcr'able
        return sorted_call_order

    usdc = EvmToken('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359')
    weth = EvmToken('eip155:137/erc20:0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619')
    usdt = EvmToken('eip155:137/erc20:0xc2132D05D31c914a87C6611C10748AEb04B58e8F')
    pol = A_POLYGON_POS_MATIC.resolve_to_evm_token()

    with (
        patch.object(blockchain.polygon_pos.node_inquirer, 'default_call_order', mock_default_call_order),  # noqa: E501
        patch(
            'rotkehlchen.globaldb.handler.GlobalDBHandler.get_token_detection_data',
            new=lambda *args, **kwargs: [EvmTokenDetectionData(
                identifier=pol.identifier,
                address=pol.evm_address,
                decimals=pol.decimals,  # type: ignore
            ), EvmTokenDetectionData(
                identifier=usdc.identifier,
                address=usdc.evm_address,
                decimals=usdc.decimals,  # type: ignore
            ), EvmTokenDetectionData(
                identifier=weth.identifier,
                address=weth.evm_address,
                decimals=weth.decimals,  # type: ignore
            ), EvmTokenDetectionData(
                identifier=usdt.identifier,
                address=usdt.evm_address,
                decimals=usdt.decimals,  # type: ignore
            )],
        ),
    ):
        blockchain.polygon_pos.tokens.detect_tokens(
            only_cache=False,
            addresses=[address],
        )
        blockchain.query_polygon_pos_balances()
        balances = blockchain.balances.polygon_pos[address].assets
        assert balances == {
            pol: Balance(
                amount=FVal('8.204435619126641457'),
                usd_value=FVal('12.3066534286899621855'),
            ),
            usdc: Balance(
                amount=FVal('0.33078'),
                usd_value=FVal('0.496170'),
            ),
            weth: Balance(
                amount=FVal('0.007712106620416874'),
                usd_value=FVal('0.0115681599306253110'),
            ),
            usdt: Balance(
                amount=FVal('0.074222'),
                usd_value=FVal('0.1113330'),
            ),
        }
