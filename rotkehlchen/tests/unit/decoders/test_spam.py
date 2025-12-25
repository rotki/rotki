
from typing import TYPE_CHECKING

import pytest

from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import SPAM_PROTOCOL, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x929a6225A5012316aF9d36386b243911ad6df9DF', '0x223EE48E2A9A786FD061e8273D078a4451FAf76B']])  # noqa: E501
def test_receive_poison(ethereum_inquirer: 'EthereumInquirer'):
    """Check the main currency poisoning. In this transaction there are only spam token transfers.
    There is a fake ETH transfer and a fake USDC transfer.
    """
    tx_hash = deserialize_evm_tx_hash('0xaaa20e8ab6dc3f16a0518c4f3c9fadf61264a321d65cd5af68869f5f47828934')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events[0].notes == 'Receive 2.12507748 ETH from 0x7eb7b44A10B7af2b9e79eADD813c04Ba6D422bBB to 0x223EE48E2A9A786FD061e8273D078a4451FAf76B'  # fake ETH  # noqa: E501
    assert events[1].notes == 'Receive 44794.000506 USDC from 0x8845F09D88EEFfeD9B197c8a92cDd36A9dD72c05 to 0x929a6225A5012316aF9d36386b243911ad6df9DF'  # TODO @yabirgb: fake USDC, we need to detect it as spam also but we need a different logic and with no false positives # noqa: E501
    assert events[0].asset.resolve_to_evm_token().protocol == SPAM_PROTOCOL
