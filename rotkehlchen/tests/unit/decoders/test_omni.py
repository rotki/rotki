import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.omni.constants import (
    CPT_OMNI,
    OMNI_AIDROP_CONTRACT,
    OMNI_TOKEN_ID,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


# @pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x9211043D7012457a51caB901e5b184dA2Ef8b245']])
def test_claim(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xc626898273896eb771e9725137849dd104e388aad49687068a7681b5c54893fe')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp, gas_str = TimestampMS(1713555527000), '0.000567969103578996'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0005')),
            location_label=ethereum_accounts[0],
            notes='Spend 0.0005 ETH as a fee to claim the Omni genesis airdrop',
            counterparty=CPT_OMNI,
            address=OMNI_AIDROP_CONTRACT,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=217,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=Asset(OMNI_TOKEN_ID),
            balance=Balance(amount=FVal('14.411451809999998976')),
            location_label=ethereum_accounts[0],
            notes='Claim 14.411451809999998976 OMNI from the Omni genesis airdrop',
            counterparty=CPT_OMNI,
            address=OMNI_AIDROP_CONTRACT,
        ),
    ]
    assert events == expected_events
