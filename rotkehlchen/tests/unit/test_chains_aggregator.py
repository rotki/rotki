from contextlib import ExitStack

import pytest

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.aggregator import ChainsAggregator, _module_name_to_class
from rotkehlchen.tests.utils.blockchain import setup_evm_addresses_activity_mock
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import AVAILABLE_MODULES_MAP, SupportedBlockchain


@pytest.mark.parametrize('ethereum_modules', [[]])
def test_module_activation(blockchain):
    for module_name in AVAILABLE_MODULES_MAP:
        expected_module_type = _module_name_to_class(module_name)
        module = blockchain.activate_module(module_name)
        assert isinstance(module, expected_module_type)
        assert blockchain.eth_modules[module_name] == module


@pytest.mark.parametrize('ethereum_modules', [AVAILABLE_MODULES_MAP.keys()])
def test_module_deactivation(blockchain):
    for module_name in AVAILABLE_MODULES_MAP:
        expected_module_type = _module_name_to_class(module_name)
        assert isinstance(blockchain.eth_modules[module_name], expected_module_type)
        blockchain.deactivate_module(module_name)
        assert module_name not in blockchain.eth_modules


@pytest.mark.parametrize('ethereum_accounts', [[]])
def test_detect_evm_accounts(blockchain: 'ChainsAggregator') -> None:
    """
    Tests that the detection of EVM accounts activity in chains where they are not tracked yet
    works as expected.
    """
    # Is a contract in ethereum mainnet and should not be added anywhere else despite it having
    # activity in other chains
    eth_addy_contract = make_evm_address()

    # Is an EOA in optimism. Has activity in all chains. Should be added to optimism, and avax
    addy_eoa_1 = make_evm_address()

    # Is an EOA in ethereum mainnet. Has activity only in ethereum and in optimism. Should be
    # added to optimism and should not be added to avax
    addy_eoa_2 = make_evm_address()
    # polygon and mainnet address
    addy_eoa_3 = make_evm_address()

    # Is an EOA that is initially already added everywhere. Has activity in all chains.
    # Since is already added, should not be added again.
    everywhere_addy = make_evm_address()

    initial_accounts_data = []
    addies_to_start_with = [
        (SupportedBlockchain.ETHEREUM, eth_addy_contract),
        (SupportedBlockchain.OPTIMISM, addy_eoa_1),
        (SupportedBlockchain.ETHEREUM, addy_eoa_2),
        (SupportedBlockchain.ETHEREUM, addy_eoa_3),
        (SupportedBlockchain.ETHEREUM, everywhere_addy),
        (SupportedBlockchain.OPTIMISM, everywhere_addy),
        (SupportedBlockchain.AVALANCHE, everywhere_addy),
        (SupportedBlockchain.POLYGON_POS, everywhere_addy),
    ]

    for chain, addy in addies_to_start_with:
        blockchain.modify_blockchain_accounts(
            blockchain=chain,
            accounts=[addy],
            append_or_remove='append',
        )
        initial_accounts_data.append(BlockchainAccountData(
            chain=chain,
            address=addy,
        ))

    with blockchain.database.user_write() as write_cursor:
        blockchain.database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=initial_accounts_data,
        )

    with ExitStack() as stack:
        setup_evm_addresses_activity_mock(
            stack=stack,
            chains_aggregator=blockchain,
            eth_contract_addresses=[eth_addy_contract, everywhere_addy],
            ethereum_addresses=[eth_addy_contract, everywhere_addy, addy_eoa_1, addy_eoa_2],
            optimism_addresses=[eth_addy_contract, everywhere_addy, addy_eoa_1, addy_eoa_2],
            avalanche_addresses=[eth_addy_contract, everywhere_addy, addy_eoa_1],
            polygon_pos_addresses=[everywhere_addy, addy_eoa_3],
        )

        blockchain.detect_evm_accounts()

    assert set(blockchain.accounts.eth) == {addy_eoa_1, addy_eoa_2, addy_eoa_3, eth_addy_contract, everywhere_addy}  # noqa: E501
    assert set(blockchain.accounts.optimism) == {addy_eoa_1, addy_eoa_2, everywhere_addy}
    assert set(blockchain.accounts.avax) == {addy_eoa_1, everywhere_addy}
    assert set(blockchain.accounts.polygon_pos) == {addy_eoa_3, everywhere_addy}

    # Also check the db
    expected_accounts_data = initial_accounts_data + [
        BlockchainAccountData(
            chain=SupportedBlockchain.ETHEREUM,
            address=addy_eoa_1,
        ),
        BlockchainAccountData(
            chain=SupportedBlockchain.AVALANCHE,
            address=addy_eoa_1,
        ),
        BlockchainAccountData(
            chain=SupportedBlockchain.OPTIMISM,
            address=addy_eoa_2,
        ),
        BlockchainAccountData(
            chain=SupportedBlockchain.POLYGON_POS,
            address=addy_eoa_3,
        ),
    ]
    accounts_in_db = []
    with blockchain.database.conn.read_ctx() as cursor:
        raw_accounts = blockchain.database.get_blockchain_accounts(cursor)
        for account in raw_accounts.eth:
            accounts_in_db.append(BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=account,
            ))
        for account in raw_accounts.optimism:
            accounts_in_db.append(BlockchainAccountData(
                chain=SupportedBlockchain.OPTIMISM,
                address=account,
            ))
        for account in raw_accounts.avax:
            accounts_in_db.append(BlockchainAccountData(
                chain=SupportedBlockchain.AVALANCHE,
                address=account,
            ))
        for account in raw_accounts.polygon_pos:
            accounts_in_db.append(BlockchainAccountData(
                chain=SupportedBlockchain.POLYGON_POS,
                address=account,
            ))

    assert set(accounts_in_db) == set(expected_accounts_data)
    assert len(accounts_in_db) == len(expected_accounts_data)
