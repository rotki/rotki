import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.balances import BlockchainBalances
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BCH, A_BTC, A_ETH
from rotkehlchen.tests.utils.factories import UNIT_BTC_ADDRESS1, make_evm_address
from rotkehlchen.tests.utils.xpubs import setup_db_for_xpub_tests_impl
from rotkehlchen.types import ChainID, EvmTokenKind

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
    expected_serialized_dict = {
        'BTC': {
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
        'ETH': {
            address1: {
                'assets': {
                    'ETH': {'amount': '1', 'usd_value': '1'},
                },
                'liabilities': {},
            },
        },
        'OPTIMISM': {
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
    expected_serialized_dict['OPTIMISM'][address2]['assets'][OPTIMISM_USDC_TOKEN.serialize()] = {'amount': '100', 'usd_value': '100'}  # noqa: E501
    a.eth[address1].assets.pop('ETH')
    expected_serialized_dict['ETH'][address1] = {'assets': {}, 'liabilities': {}}
    assert a.serialize(given_chain=None) == expected_serialized_dict
