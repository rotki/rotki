import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, CPT_GITCOIN
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_SAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_gitcoin_old_donation(database, ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0x811ba23a10c76111289133ec6f90d3c33a604baa50053739210e870687a456d9
    """
    tx_hash = deserialize_evm_tx_hash('0x811ba23a10c76111289133ec6f90d3c33a604baa50053739210e870687a456d9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1569924574000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000055118'), usd_value=ZERO),
            location_label=ADDY,
            notes='Burned 0.000055118 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=164,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_SAI,
            balance=Balance(amount=FVal('0.95'), usd_value=ZERO),
            location_label=ADDY,
            notes='Donate 0.95 SAI to 0xEbDb626C95a25f4e304336b1adcAd0521a1Bdca1 via gitcoin',
            counterparty=CPT_GITCOIN,
            address=string_to_evm_address('0xEbDb626C95a25f4e304336b1adcAd0521a1Bdca1'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=165,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_SAI,
            balance=Balance(amount=FVal('0.05'), usd_value=ZERO),
            location_label=ADDY,
            notes='Donate 0.05 SAI to 0x00De4B13153673BCAE2616b67bf822500d325Fc3 via gitcoin',
            counterparty=CPT_GITCOIN,
            address=string_to_evm_address('0x00De4B13153673BCAE2616b67bf822500d325Fc3'),
        ),
    ]
    assert events == expected_events
