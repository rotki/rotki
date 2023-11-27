
import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.polygon.constants import POLYGON_MIGRATION_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.polygon.constants import CPT_POLYGON
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH_MATIC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x692C673814eDB9Fe6DB2a6F4227F40524240Cbec']])
def test_matic_to_pol_migration(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6c30b202e7223ea93b9d1c898d7012b699d14bec5434e8839fc290858718f6a2')  # noqa: E501
    timestamp = TimestampMS(1698285215000)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    amount = '10000.28'
    gas_str = '0.001792178291324676'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=372,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_ETH_MATIC,
        balance=Balance(amount=ZERO),
        location_label=ethereum_accounts[0],
        notes=f'Revoke MATIC spending approval of {ethereum_accounts[0]} by {POLYGON_MIGRATION_ADDRESS}',  # noqa: E501
        address=POLYGON_MIGRATION_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=373,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH_MATIC,
        balance=Balance(amount=FVal(amount)),
        location_label=ethereum_accounts[0],
        notes=f'Migrate {amount} MATIC to POL',
        counterparty=CPT_POLYGON,
        address=POLYGON_MIGRATION_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=374,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6'),
        balance=Balance(amount=FVal(amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {amount} POL from MATIC->POL migration',
        counterparty=CPT_POLYGON,
        address=POLYGON_MIGRATION_ADDRESS,
    )]
    assert expected_events == events
