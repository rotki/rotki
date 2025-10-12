import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.golem.constants import CPT_GOLEM, GNT_MIGRATION_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH, A_GLM
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xf264267DCaFC1539900bc96006879701fA053259']])
def test_gnt_glm_migration(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x86baa45e4ab48d1db26df82da1a6f654fe96f1254ace5883b6397d7f55eb11a4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1646777828000)
    gas_str = '0.00560851737819982'
    amount_str = '5920'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MIGRATE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xa74476443119A942dE498590Fe1f2454d7D4aC0d'),
            amount=FVal(amount_str),
            location_label=ethereum_accounts[0],
            notes=f'Migrate {amount_str} GNT to GLM',
            counterparty=CPT_GOLEM,
            address=GNT_MIGRATION_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.MIGRATE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_GLM,
            amount=FVal(amount_str),
            location_label=ethereum_accounts[0],
            notes=f'Receive {amount_str} GLM from GNT->GLM migration',
            counterparty=CPT_GOLEM,
            address=GNT_MIGRATION_ADDRESS,
        ),
    ]
    assert events == expected_events
