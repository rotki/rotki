import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.eas.constants import CPT_EAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_attest_optimism(database, optimism_inquirer, optimism_accounts):
    tx_hex = deserialize_evm_tx_hash('0xf843f6d09e8dec2ee2d1b5fdeade9a9744857f598cf593b6c259166c32dfd05a')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1700569289000)
    gas_amount_str = '0.000136427902240075'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount_str)),
            location_label=user_address,
            notes=f'Burned {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.ATTEST,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Attest to https://optimism.easscan.org/attestation/view/0x3045bf8797f8e528219d48b23d28b661be5be17d13c28f61f4f6cced1b349c65',
            counterparty=CPT_EAS,
            address=string_to_evm_address('0x4200000000000000000000000000000000000021'),
        ),
    ]
    assert events == expected_events
