import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.optimism.modules.airdrops.constants import CPT_OPTIMISM
from rotkehlchen.constants.assets import A_ETH, A_OP
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, Timestamp, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_optimism_airdrop_claim(database, optimism_inquirer):
    """Data taken from
    https://optimistic.etherscan.io/tx/0xda810d7e1757c6ce7387b437c26472f802eec47404e60d4f1eaa9f23bf8d8b73
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0xda810d7e1757c6ce7387b437c26472f802eec47404e60d4f1eaa9f23bf8d8b73')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = Timestamp(1673337921000)
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000000122548')),
            location_label=ADDY,
            notes='Burned 0.000000122548 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_OP,
            balance=Balance(amount=FVal('827.759804739626467328')),
            location_label=ADDY,
            notes='Claimed 827.759804739626467328 OP from optimism airdrop',
            counterparty=CPT_OPTIMISM,
        )]
    assert expected_events == events
