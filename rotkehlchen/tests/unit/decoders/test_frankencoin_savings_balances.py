from typing import Any

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.decoding.frankencoin.constants import CPT_FRANKENCOIN
from rotkehlchen.chain.evm.decoding.frankencoin.savings.balances import (
    FrankencoinSavingsBalances,
)
from rotkehlchen.constants.assets import A_ZCHF
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbC6668371b69FD94110a9E24dCCe517CaFA2B2d1']])
def test_frankencoin_savings_balances(ethereum_inquirer: Any, ethereum_accounts: Any, inquirer: Any) -> None:
    _, tx_decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xe7e484ae4bf7b2a310eb0e6b34bc3e889940fcb85b4bd074ecf8a24a1fa5af70'),
    )
    balances = FrankencoinSavingsBalances(
        evm_inquirer=ethereum_inquirer,
        tx_decoder=tx_decoder,
    ).query_balances()

    assert balances[ethereum_accounts[0]].assets[A_ZCHF][CPT_FRANKENCOIN] == Balance(
        amount=FVal('1598.310020494985735077'),
        value=FVal('2397.4650307424786026155'),
    )
