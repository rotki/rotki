import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.airdrops.constants import CPT_ELEMENT_FINANCE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ELFI, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_claim_airdrop(ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0x1e58aed1baf70b57e6e3e880e1890e7fe607fddc94d62986c38fe70e483e594b
    """
    tx_hash = deserialize_evm_tx_hash('0x1e58aed1baf70b57e6e3e880e1890e7fe607fddc94d62986c38fe70e483e594b')  # noqa: E501
    timestamp = TimestampMS(1652910214000)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0061843862'),
            location_label=ADDY,
            notes='Burn 0.0061843862 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=549,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_ELFI,
            amount=FVal('613.8986657935664'),
            location_label=ADDY,
            notes='Claim 613.8986657935664 ELFI from element-finance airdrop and delegate it to 0x7BAFC0D5c5892f2041FD9F2415A7611042218e22',  # noqa: E501
            counterparty=CPT_ELEMENT_FINANCE,
            address=string_to_evm_address('0x5ae69B714859A3C15281e0a227D9B8C82F03b966'),
            extra_data={AIRDROP_IDENTIFIER_KEY: 'elfi'},
        ),
    ]
    assert events == expected_events
