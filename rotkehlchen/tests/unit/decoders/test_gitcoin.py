import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.gitcoin.constants import CPT_GITCOIN
from rotkehlchen.constants.assets import A_ETH, A_SAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])  # noqa: E501
def test_gitcoin_old_donation(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from
    https://etherscan.io/tx/0x811ba23a10c76111289133ec6f90d3c33a604baa50053739210e870687a456d9
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x811ba23a10c76111289133ec6f90d3c33a604baa50053739210e870687a456d9')  # noqa: E501
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
            timestamp=1569924574000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000055118'), usd_value=ZERO),
            location_label=ADDY,
            notes='Burned 0.000055118 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=164,
            timestamp=1569924574000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_SAI,
            balance=Balance(amount=FVal('0.95'), usd_value=ZERO),
            location_label=ADDY,
            notes='Donate 0.95 SAI to 0xEbDb626C95a25f4e304336b1adcAd0521a1Bdca1 via gitcoin',  # noqa: E501
            counterparty=CPT_GITCOIN,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=165,
            timestamp=1569924574000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_SAI,
            balance=Balance(amount=FVal('0.05'), usd_value=ZERO),
            location_label=ADDY,
            notes='Donate 0.05 SAI to 0x00De4B13153673BCAE2616b67bf822500d325Fc3 via gitcoin',  # noqa: E501
            counterparty=CPT_GITCOIN,
        ),
    ]
    assert events == expected_events
