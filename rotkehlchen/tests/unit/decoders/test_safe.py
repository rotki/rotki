import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
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


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x96399Ddb62d833029fbEf774d1FE044AF33E98Ef']])
def test_safe_creation(database, ethereum_inquirer, ethereum_accounts):
    """Test that creation of new safes is tracked"""
    tx_hex = deserialize_evm_tx_hash('0xa9e3c581f39403a0a2eb5a3e604be715c0a4ee8aa4bcc9bddece5c268b47e233')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1691846051000)
    gas_amount_str = '0.004928138478008416'
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
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Create a new safe with a threshold of 2 and owners 0x95a47323EF5B86fa56F3960B86C2F2e78325b402,0x19e18956dfD3836fB8f9c422C8e306C787F0bE00',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=string_to_evm_address('0x2eb2B9300036807A7674997e6c6874601275EDDD'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('polygon_pos_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])  # yabir.eth  # noqa: E501
def test_safe_spam(database, polygon_pos_inquirer, polygon_pos_accounts):
    """Test that a safe transaction if from an unrelated account, does not appear in events"""
    tx_hex = deserialize_evm_tx_hash('0xefb07f4d166d6887eada96e61fd6821bfdf889d5435d75ab44d4ca0fa7627396')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = polygon_pos_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1651102781000)
    amount_str = '0.00637462961483049'
    spam_contract = '0xC63c477465a792537D291ADb32Ed15c0095E106B'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=431,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:137/erc20:0x580A84C73811E1839F75d86d75d88cCa0c241fF4'),
            balance=Balance(amount=FVal(amount_str)),
            location_label=user_address,
            notes=f'Receive {amount_str} QI from {spam_contract} to {user_address}',
            address=spam_contract,
        ),
    ]
    assert events == expected_events
