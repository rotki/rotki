import json
from collections.abc import Iterator
from contextlib import ExitStack
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.etherscan_like import HasChainActivity
from rotkehlchen.types import deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.fixture(name='check_all_indexers', params=[
    [(blockscout_patch := patch(
        target='rotkehlchen.externalapis.blockscout.Blockscout._query_and_process',
        side_effect=RemoteError('BOOM'),
    )), (routescan_patch := patch(
        target='rotkehlchen.externalapis.routescan.Routescan._query',
        side_effect=RemoteError('BOOM'),
    ))],  # blockscout and routescan patched, uses etherscan
    [(etherscan_patch := patch(
        target='rotkehlchen.externalapis.etherscan.Etherscan._query',
        side_effect=RemoteError('BOOM'),
    )), routescan_patch],  # etherscan and routescan patched, uses blockscout
    [etherscan_patch, blockscout_patch],  # etherscan and blockscout patched, uses routescan.
])
def fixture_check_all_indexers(request: pytest.FixtureRequest) -> Iterator[None]:
    """Run the test once for each indexer (etherscan, blockscout, routescan).
    Each run patches the all the other indexers to fail, forcing fallback to the target indexer,
    and ensuring a failure if the target indexer fails.
    """
    with ExitStack() as stack:
        for indexer_patch in request.param:
            stack.enter_context(indexer_patch)
        yield


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_contract_abi(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    """Check that all the indexers properly retrieve the abi of a verified contract and return
    None for a non-contract address.
    """
    assert ethereum_inquirer.get_contract_abi(
        chain_id=ethereum_inquirer.chain_id,
        address=string_to_evm_address('0x5a464C28D19848f44199D003BeF5ecc87d090F87'),
    ) == json.loads('[{"inputs":[{"internalType":"address","name":"vat_","type":"address"},{"internalType":"address","name":"dog_","type":"address"},{"internalType":"address","name":"cat_","type":"address"},{"internalType":"address","name":"spot_","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"AddIlk","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"usr","type":"address"}],"name":"Deny","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"what","type":"bytes32"},{"indexed":false,"internalType":"address","name":"data","type":"address"}],"name":"File","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"},{"indexed":false,"internalType":"bytes32","name":"what","type":"bytes32"},{"indexed":false,"internalType":"address","name":"data","type":"address"}],"name":"File","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"},{"indexed":false,"internalType":"bytes32","name":"what","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"data","type":"uint256"}],"name":"File","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"},{"indexed":false,"internalType":"bytes32","name":"what","type":"bytes32"},{"indexed":false,"internalType":"string","name":"data","type":"string"}],"name":"File","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"NameError","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"usr","type":"address"}],"name":"Rely","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"RemoveIlk","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"SymbolError","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"UpdateIlk","type":"event"},{"inputs":[{"internalType":"address","name":"adapter","type":"address"}],"name":"add","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"cat","outputs":[{"internalType":"contract CatLike","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"class","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"count","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"dec","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"usr","type":"address"}],"name":"deny","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"dog","outputs":[{"internalType":"contract DogLike","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"},{"internalType":"bytes32","name":"what","type":"bytes32"},{"internalType":"uint256","name":"data","type":"uint256"}],"name":"file","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"},{"internalType":"bytes32","name":"what","type":"bytes32"},{"internalType":"string","name":"data","type":"string"}],"name":"file","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"what","type":"bytes32"},{"internalType":"address","name":"data","type":"address"}],"name":"file","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"},{"internalType":"bytes32","name":"what","type":"bytes32"},{"internalType":"address","name":"data","type":"address"}],"name":"file","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"gem","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"pos","type":"uint256"}],"name":"get","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"name":"ilkData","outputs":[{"internalType":"uint96","name":"pos","type":"uint96"},{"internalType":"address","name":"join","type":"address"},{"internalType":"address","name":"gem","type":"address"},{"internalType":"uint8","name":"dec","type":"uint8"},{"internalType":"uint96","name":"class","type":"uint96"},{"internalType":"address","name":"pip","type":"address"},{"internalType":"address","name":"xlip","type":"address"},{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"symbol","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"info","outputs":[{"internalType":"string","name":"name","type":"string"},{"internalType":"string","name":"symbol","type":"string"},{"internalType":"uint256","name":"class","type":"uint256"},{"internalType":"uint256","name":"dec","type":"uint256"},{"internalType":"address","name":"gem","type":"address"},{"internalType":"address","name":"pip","type":"address"},{"internalType":"address","name":"join","type":"address"},{"internalType":"address","name":"xlip","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"join","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"list","outputs":[{"internalType":"bytes32[]","name":"","type":"bytes32[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"start","type":"uint256"},{"internalType":"uint256","name":"end","type":"uint256"}],"name":"list","outputs":[{"internalType":"bytes32[]","name":"","type":"bytes32[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"pip","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"pos","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"_ilk","type":"bytes32"},{"internalType":"address","name":"_join","type":"address"},{"internalType":"address","name":"_gem","type":"address"},{"internalType":"uint256","name":"_dec","type":"uint256"},{"internalType":"uint256","name":"_class","type":"uint256"},{"internalType":"address","name":"_pip","type":"address"},{"internalType":"address","name":"_xlip","type":"address"},{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_symbol","type":"string"}],"name":"put","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"usr","type":"address"}],"name":"rely","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"remove","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"removeAuth","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"spot","outputs":[{"internalType":"contract SpotLike","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"update","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"vat","outputs":[{"internalType":"contract VatLike","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"wards","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"bytes32","name":"ilk","type":"bytes32"}],"name":"xlip","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"}]')  # noqa: E501
    assert ethereum_inquirer.get_contract_abi(
        chain_id=ethereum_inquirer.chain_id,
        address=string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306'),
    ) is None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_contract_creation_hash(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    """Check that all the indexers properly retrieve the abi of a verified contract and return
    None for a non-contract address.
    """
    assert ethereum_inquirer.get_contract_creation_hash(
        chain_id=ethereum_inquirer.chain_id,
        address=string_to_evm_address('0x5a464C28D19848f44199D003BeF5ecc87d090F87'),
    ) == deserialize_evm_tx_hash('0x02525186f0153965677e3e206bf07c667718f90de8561937d2eea531bfd9b951')  # noqa: E501
    assert ethereum_inquirer.get_contract_creation_hash(
        chain_id=ethereum_inquirer.chain_id,
        address=string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306'),
    ) is None


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_has_activity(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    """Check that all indexers properly return the correct account activity."""
    assert ethereum_inquirer.has_activity(
        chain_id=ethereum_inquirer.chain_id,
        account=string_to_evm_address('0x56a1A34F0d33788ebA53e2706854A37A5F275536'),
    ) == HasChainActivity.TRANSACTIONS
    assert ethereum_inquirer.has_activity(
        chain_id=ethereum_inquirer.chain_id,
        account=string_to_evm_address('0x84e8EE8911c147755bD70084b6b4D1a5A8351476'),
    ) == HasChainActivity.NONE


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_code(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    assert ethereum_inquirer.get_code(
        account=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
    )[:10] == '0x60806040'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_call_contract(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    assert ethereum_inquirer._call_contract(
        web3=None,
        contract_address=string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        abi=ethereum_inquirer.contracts.erc20_abi,
        method_name='name',
    ) == 'USD Coin'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_latest_block_number(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    assert ethereum_inquirer.get_latest_block_number() == 24069561


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_block_by_number(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    """Check that all indexers properly return block data by block number."""
    block = ethereum_inquirer.get_block_by_number(num=10304885)
    assert block['timestamp'] == 1592686213
    assert block['number'] == 10304885
    assert block['hash'] == '0xe2217ba1639c6ca2183f40b0f800185b3901faece2462854b3162d4c5077752c'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_transaction_receipt(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    raw_receipt = ethereum_inquirer.get_transaction_receipt(
        tx_hash=deserialize_evm_tx_hash('0x12d474b6cbba04fd1a14e55ef45b1eb175985612244631b4b70450c888962a89'),
    )
    assert raw_receipt['blockNumber'] == 10840714
    assert raw_receipt['transactionHash'] == '0x12d474b6cbba04fd1a14e55ef45b1eb175985612244631b4b70450c888962a89'  # noqa: E501
    assert len(raw_receipt['logs']) == 2


@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_get_transaction_by_hash(
        ethereum_inquirer: 'EthereumInquirer',
        check_all_indexers,
) -> None:
    tx, _ = ethereum_inquirer.get_transaction_by_hash(
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x5b180e3dcc19cd29c918b98c876f19393e07b74c07fd728102eb6241db3c2d5c')),  # noqa: E501
    )
    assert tx.tx_hash == tx_hash
    assert tx.timestamp == 1633128954
    assert tx.value == 33000000000000000
    assert tx.gas == 294144
