import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import (
    CPT_GNOSIS_PAY,
    GNOSIS_PAY_CASHBACK_ADDRESS,
)
from rotkehlchen.constants.assets import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x7EcB43E01425c66a783A3065F782ccF304b39B99']])
def test_gnosis_pay_cashback(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1c6f58c55ba2eeef7e08ed4725d16ae479d1b4210b39e647a9b282af6ffb9470')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    amount = '0.8527869407'
    assert events == [
        EvmEvent(
            sequence_index=8,
            timestamp=TimestampMS(1726146635000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.CASHBACK,
            asset=Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
            balance=Balance(amount=FVal(amount)),
            location_label=gnosis_accounts[0],
            notes=f'Receive cashback of {amount} GNO from Gnosis Pay',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_PAY,
            address=GNOSIS_PAY_CASHBACK_ADDRESS,
        ),
    ]
