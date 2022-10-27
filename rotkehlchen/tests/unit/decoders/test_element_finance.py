import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.airdrops.constants import CPT_ELEMENT_FINANCE
from rotkehlchen.constants.assets import A_ELFI, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])  # noqa: E501
def test_claim_aidrop(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from
    https://etherscan.io/tx/0x1e58aed1baf70b57e6e3e880e1890e7fe607fddc94d62986c38fe70e483e594b
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x1e58aed1baf70b57e6e3e880e1890e7fe607fddc94d62986c38fe70e483e594b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1652910214000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0061843862')),
            location_label=ADDY,
            notes='Burned 0.0061843862 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=549,
            timestamp=1652910214000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_ELFI,
            balance=Balance(amount=FVal('613.8986657935664')),
            location_label=ADDY,
            notes='Claim 613.8986657935664 ELFI from element-finance airdrop and delegate it to 0x7BAFC0D5c5892f2041FD9F2415A7611042218e22',  # noqa: E501
            counterparty=CPT_ELEMENT_FINANCE,
        ),
    ]
    assert events == expected_events
