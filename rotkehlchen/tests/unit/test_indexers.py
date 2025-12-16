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
    [],
    [(etherscan_patch := patch(
        target='rotkehlchen.externalapis.etherscan.Etherscan._query',
        side_effect=RemoteError('BOOM'),
    ))],
    [etherscan_patch, patch(
        target='rotkehlchen.externalapis.blockscout.Blockscout._query_and_process',
        side_effect=RemoteError('BOOM'),
    )],
])
def fixture_check_all_indexers(request: pytest.FixtureRequest) -> Iterator[None]:
    """Run the test once for each indexer, patching the other indexers to fail."""
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
