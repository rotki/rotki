import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.arbitrum_one.modules.airdrops.decoder import ARBITRUM_ONE_AIRDROP
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ARB, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.arbitrum_one import get_arbitrum_allthatnode
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

user_address = '0x0c5b7A89b3689d86Ed473caE4E7CB00381949861'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [[user_address]])
@pytest.mark.parametrize('arbitrum_one_manager_connect_at_start', [(get_arbitrum_allthatnode(ONE),)])  # noqa: E501
def test_arbitrum_airdrop_claim(database, arbitrum_one_inquirer):
    """Data taken from
    https://arbiscan.io/tx/0xa230fc4d5e61db1d9be044215b00cb6ad1775b413a240ea23a98117153f6264e
    """
    tx_hash = deserialize_evm_tx_hash('0xa230fc4d5e61db1d9be044215b00cb6ad1775b413a240ea23a98117153f6264e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1689935876000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000032717')),
            location_label=user_address,
            notes='Burned 0.000032717 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_ARB,
            balance=Balance(amount=FVal('625')),
            location_label=user_address,
            notes='Claimed 625 ARB from arbitrum airdrop',
            counterparty=CPT_ARBITRUM_ONE,
            address=ARBITRUM_ONE_AIRDROP,
        )]
    assert expected_events == events
