from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.aztec.balances import AztecBalances
from rotkehlchen.chain.ethereum.modules.aztec.constants import A_AZTEC, CPT_AZTEC
from rotkehlchen.chain.evm.contracts import WEB3
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Price, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.mark.parametrize('ethereum_accounts', [['0x16425074e97d06392D602f1c2eB5ef9178cf97c9']])
def test_staking_balances(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x761a58d876bbe82646bc08e9981e745d286e3ad84d35669530a7b64f3c5fb00a'),
    )
    with (
        patch.object(ethereum_inquirer, 'multicall', return_value=[
            WEB3.codec.encode(['uint256'], [150000 * 10**18]),
            WEB3.codec.encode(['uint256'], [100 * 10**18]),
        ]),
        patch.object(
            Inquirer,
            'find_main_currency_prices',
            return_value={A_AZTEC: Price(FVal(2))},
        ),
    ):
        balances = AztecBalances(
            evm_inquirer=ethereum_inquirer,
            tx_decoder=tx_decoder,
        ).query_balances(addresses=ethereum_accounts)

    assert balances[ethereum_accounts[0]].assets[A_AZTEC][CPT_AZTEC] == Balance(
        amount=FVal(150095),
        value=FVal(300190),
    )
