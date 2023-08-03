import pytest
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.diva.constants import CPT_DIVA
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction

from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_diva_delegate(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x806081bcc60a40db22bae2c1729f240f48de4b73e76b673fc4767bcee4f1c704')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1690964039000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001694706319628652')),
            location_label=ethereum_accounts[0],
            notes='Burned 0.001694706319628652 ETH for gas',
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=94,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            balance=Balance(),
            location_label=ethereum_accounts[0],
            notes='0xc37b40ABdB939635068d3c5f13E7faF686F03B65 started to delegate on DIVA to 0x42E6DD8D517abB3E4f6611Ca53a8D1243C183fB0',  # noqa: E501
            counterparty=CPT_DIVA,
        ),
    ]
    assert events == expected_events
