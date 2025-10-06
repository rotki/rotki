import pytest

from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.airdrops.constants import CPT_SHAPESHIFT
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_FOX
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x3800966F67ccBA1976F69D006374204fba56d240']])
def test_airdrop_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6635d1e12fed1a95019a53e6f6495c586891bf7b41bccfc5838f9b1703a9c20c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1634470709000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=243,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_FOX,
            amount=FVal('100'),
            location_label=ethereum_accounts[0],
            notes='Claim 100 FOX from shapeshift airdrop',
            counterparty=CPT_SHAPESHIFT,
            address=string_to_evm_address('0x2977F92D5BaddfB411beb642F97d125aA55C000A'),
            extra_data={AIRDROP_IDENTIFIER_KEY: 'shapeshift'},
        ),
    ]
    assert events == expected_events
