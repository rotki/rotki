import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [
    [
        '0x6C65fB326e7734Ba5508b5d043718288b43b9ed9',
        '0x7ac712ec4C58dEd138CC4e63e0fd59F697cC6963',
    ],
])
def test_added_owner(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x2702bb7cf56d012b9bc85d66428a361d560172a5e519384e7c507db22d07090f')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    multisig_address = ethereum_accounts[1]
    new_owner = '0xa0DD8E6c5440a424cD19f5Ec30F8fa485E814247'
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1611089364000)
    gas_amount_str = '0.004625442'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount_str)),
            location_label=user_address,
            notes=f'Burned {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes=f'Add owner {new_owner} to multisig {multisig_address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [
    [
        '0xafCD4572408b322adA9890253a7A42A9Fa4C2E40',
        '0x7ac712ec4C58dEd138CC4e63e0fd59F697cC6963',
    ],
])
def test_removed_owner(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x868a3c64eb7e68a0c0fde4ec94f7825f1400ebba9aeefc284771b0136cbd72dd')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    multisig_address = ethereum_accounts[1]
    removed_owner = '0x8a7dbC2824AcaC4d272289a33b255C3F1f3cdf32'
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1623789005000)
    gas_amount_str = '0.00130834'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount_str)),
            location_label=user_address,
            notes=f'Burned {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes=f'Remove owner {removed_owner} from multisig {multisig_address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [
    [
        '0xa0DD8E6c5440a424cD19f5Ec30F8fa485E814247',
        '0x7ac712ec4C58dEd138CC4e63e0fd59F697cC6963',
    ],
])
def test_changed_threshold(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x8332c637f98362dea0885f744f121d09ac5c548603f833b9d0bd9513fa637c52')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    multisig_address = ethereum_accounts[1]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1614713692000)
    gas_amount_str = '0.005093127'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount_str)),
            location_label=user_address,
            notes=f'Burned {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes=f'Change signers threshold to 3 for multisig {multisig_address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_execution_success(database, ethereum_inquirer, ethereum_accounts):
    """
    Test that a succesful safe transaction execution shows something if the executor is tracked
    """
    tx_hex = deserialize_evm_tx_hash('0x7bfaa362453a9320243d7f604b7ffff10c31964a62e779a8cd280987b203875f')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    multisig_address = '0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52'
    timestamp = TimestampMS(1656087756000)
    gas_amount_str = '0.006953999441541852'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount_str)),
            location_label=user_address,
            notes=f'Burned {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes=f'Successfully executed safe transaction 0xd273f3d34c8d075300dfe3aaa9d3dff76bff7ca4d874846c8bd41c2ab100118f for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x0Cec743b8CE4Ef8802cAc0e5df18a180ed8402A7']])
def test_execution_failure(database, ethereum_inquirer, ethereum_accounts):
    """
    Test that a failed safe transaction execution shows something if the executor is tracked
    """
    tx_hex = deserialize_evm_tx_hash('0xf4b387bac0e6fa05b811098fb747297bdb9ce06152aa9e841750a85ed4d4bece')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    multisig_address = '0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52'
    timestamp = TimestampMS(1599570321000)
    gas_amount_str = '0.020435096'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount_str)),
            location_label=user_address,
            notes=f'Burned {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes=f'Failed to execute safe transaction 0x4663a55668527aaa4c7811e8277c7258b5e43af4269a651b1d1cf6ab24293b1e for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events
