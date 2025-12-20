from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.base.transactions import BaseTransactions
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.safe.constants import (
    CPT_SAFE,
    SAFE_LOCKING,
    SAFE_VESTING,
    SAFEPASS_AIRDROP,
)
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.types import (
    EvmIndexer,
    NodeName,
    SerializableChainIndexerOrder,
    WeightedNode,
    string_to_evm_address,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_XDAI
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [
    [
        '0x6C65fB326e7734Ba5508b5d043718288b43b9ed9',
        '0x7ac712ec4C58dEd138CC4e63e0fd59F697cC6963',
    ],
])
def test_added_owner(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2702bb7cf56d012b9bc85d66428a361d560172a5e519384e7c507db22d07090f')  # noqa: E501
    user_address = ethereum_accounts[0]
    multisig_address = ethereum_accounts[1]
    new_owner = '0xa0DD8E6c5440a424cD19f5Ec30F8fa485E814247'
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1611089364000)
    gas_amount_str = '0.004625442'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=user_address,
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=153,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Add owner {new_owner} to multisig {multisig_address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [
    [
        '0xafCD4572408b322adA9890253a7A42A9Fa4C2E40',
        '0x7ac712ec4C58dEd138CC4e63e0fd59F697cC6963',
    ],
])
def test_removed_owner(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x868a3c64eb7e68a0c0fde4ec94f7825f1400ebba9aeefc284771b0136cbd72dd')  # noqa: E501
    user_address = ethereum_accounts[0]
    multisig_address = ethereum_accounts[1]
    removed_owner = '0x8a7dbC2824AcaC4d272289a33b255C3F1f3cdf32'
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1623789005000)
    gas_amount_str = '0.00130834'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=user_address,
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=101,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Remove owner {removed_owner} from multisig {multisig_address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [
    [
        '0xa0DD8E6c5440a424cD19f5Ec30F8fa485E814247',
        '0x7ac712ec4C58dEd138CC4e63e0fd59F697cC6963',
    ],
])
def test_changed_threshold(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8332c637f98362dea0885f744f121d09ac5c548603f833b9d0bd9513fa637c52')  # noqa: E501
    user_address = ethereum_accounts[0]
    multisig_address = ethereum_accounts[1]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1614713692000)
    gas_amount_str = '0.005093127'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=user_address,
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=59,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Change signers threshold to 3 for multisig {multisig_address}',
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_execution_success(ethereum_inquirer, ethereum_accounts):
    """
    Test that a successful safe transaction execution shows something if the executor is tracked
    """
    tx_hash = deserialize_evm_tx_hash('0x7bfaa362453a9320243d7f604b7ffff10c31964a62e779a8cd280987b203875f')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    multisig_address = '0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52'
    timestamp = TimestampMS(1656087756000)
    gas_amount_str = '0.006953999441541852'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=user_address,
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=194,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Successfully executed safe transaction 0xd273f3d34c8d075300dfe3aaa9d3dff76bff7ca4d874846c8bd41c2ab100118f for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x0Cec743b8CE4Ef8802cAc0e5df18a180ed8402A7']])
def test_execution_failure(ethereum_inquirer, ethereum_accounts):
    """
    Test that a failed safe transaction execution shows something if the executor is tracked
    """
    tx_hash = deserialize_evm_tx_hash('0xf4b387bac0e6fa05b811098fb747297bdb9ce06152aa9e841750a85ed4d4bece')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    multisig_address = '0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52'
    timestamp = TimestampMS(1599570321000)
    gas_amount_str = '0.020435096'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=user_address,
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=217,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Failed to execute safe transaction 0x4663a55668527aaa4c7811e8277c7258b5e43af4269a651b1d1cf6ab24293b1e for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', [{
    'evm_indexers_order': SerializableChainIndexerOrder(
        order={ChainID.BASE: [EvmIndexer.ROUTESCAN]},
    ),
}])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base-open-rpc',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [[
    '0x8De14E014402C0677B075A69122F94C0425Cc179',
    '0x0BeBD2FcA9854F657329324aA7dc90F656395189',
]])
def test_safe_mastercopy_upgrade_on_base(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x37d530d1347e3d0903bcb2c8650bd223b39259ba22af373ba70a3cb064ac46b4')  # noqa: E501
    transactions = BaseTransactions(base_inquirer, base_inquirer.database)
    transactions.single_address_query_transactions(  # temporary hack at the time of writing get_decoded_events_of_transaction does not respect the `evm_indexers_order` so we do this here to use the given order  # noqa: E501
        address=base_accounts[0],
        start_ts=Timestamp(1756713300),
        end_ts=Timestamp(1756713400),
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1756713353000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=(gas_amount := FVal('0.000000145868417642')),
            location_label=(user := base_accounts[0]),
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=336,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user,
            notes=f'Upgrade Safe master copy to 0x29fcB43b46531BcA003ddC8FCB67FFE91900C762 for multisig {base_accounts[1]}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=base_accounts[1],
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x96399Ddb62d833029fbEf774d1FE044AF33E98Ef']])
def test_safe_creation(ethereum_inquirer, ethereum_accounts):
    """Test that creation of new safes is tracked"""
    tx_hash = deserialize_evm_tx_hash('0xa9e3c581f39403a0a2eb5a3e604be715c0a4ee8aa4bcc9bddece5c268b47e233')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1691846051000)
    gas_amount_str = '0.004928138478008416'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=user_address,
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=171,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.CREATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Create a new safe with a threshold of 2 and owners 0x95a47323EF5B86fa56F3960B86C2F2e78325b402,0x19e18956dfD3836fB8f9c422C8e306C787F0bE00',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=string_to_evm_address('0x2eb2B9300036807A7674997e6c6874601275EDDD'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])  # yabir.eth  # noqa: E501
def test_safe_spam(polygon_pos_inquirer, polygon_pos_accounts):
    """Test that a safe transaction if from an unrelated account, does not appear in events"""
    tx_hash = deserialize_evm_tx_hash('0xefb07f4d166d6887eada96e61fd6821bfdf889d5435d75ab44d4ca0fa7627396')  # noqa: E501
    user_address = polygon_pos_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1651102781000)
    amount_str = '0.00637462961483049'
    spam_contract = '0xC63c477465a792537D291ADb32Ed15c0095E106B'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=431,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:137/erc20:0x580A84C73811E1839F75d86d75d88cCa0c241fF4'),
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Receive {amount_str} QI from {spam_contract} to {user_address}',
            address=spam_contract,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x4a24fe31b4D7215e7643f738058130054f9b3F3A',
    '0xF2961617C402404A4BB0Cd3d83992b5B4C8090eE',
]])
def test_safe_vesting_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc831d94b43be533e83562da9bc10b38b4bab6ce6046c3a9baf76c5359634625a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, multisig_address, timestamp, gas, amount = ethereum_accounts[0], ethereum_accounts[1], TimestampMS(1717404395000), '0.00123180896602807', '20549.221611721611721612'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=270,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'),
            amount=FVal(amount),
            location_label=multisig_address,
            notes=f'Claim {amount} SAFE from vesting',
            counterparty=CPT_SAFE,
            address=SAFE_VESTING,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=271,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Successfully executed safe transaction 0x4abbfbca46ad4a4099ae7896cfd9e4a4c3ef604236d55efd58a0314e1bfcf0eb for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x663aD41156a9B2Da7Ead2edC6494E102c9b36184',
    '0xA76C44d0adD77F9403715D8B6F47AD4e6515EC8c',
]])
def test_safe_lock(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xad3d976ae02cf82f109cc2d2f3e8f2f10df6a00a4825e3f04cf0e1b7e68a06b8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, multisig_address, timestamp, gas, amount = ethereum_accounts[0], ethereum_accounts[1], TimestampMS(1719926867000), '0.00072087801264352', '5115.763372'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=157,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'),
            amount=FVal(amount),
            location_label=multisig_address,
            notes=f'Set SAFE spending approval of {multisig_address} by {SAFE_LOCKING} to {amount}',  # noqa: E501
            address=SAFE_LOCKING,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=158,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'),
            amount=ZERO,
            location_label=multisig_address,
            notes=f'Revoke SAFE spending approval of {multisig_address} by {SAFE_LOCKING}',
            address=SAFE_LOCKING,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=159,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'),
            amount=FVal(amount),
            location_label=multisig_address,
            notes=f'Lock {amount} SAFE for Safe{{Pass}}',
            counterparty=CPT_SAFE,
            address=SAFE_LOCKING,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=161,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Successfully executed safe transaction 0x4aed5d3d1e4a41a5dec570127ff5bba82d40214ce4fc6f65767ee3c2ac17aaca for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xdfDA7181EB27A69d897E82cF96C5BcbdC3c059B0',
    '0x51C40354119dd14C02d8ab24ed72C12D29f8cdA4',
]])
def test_safe_unlock(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x51d4c06ff00be729fe5bc79215253e45e65ce4c8531cd249633c6e76754c89d0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, multisig_address, timestamp, gas, amount = ethereum_accounts[0], ethereum_accounts[1], TimestampMS(1721101211000), '0.0003433', '1026.126150242296748346'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=560,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'),
            amount=FVal(amount),
            location_label=multisig_address,
            notes=f'Start unlock of {amount} SAFE from Safe{{Pass}}',
            counterparty=CPT_SAFE,
            address=SAFE_LOCKING,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=561,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Successfully executed safe transaction 0x3b6ade06b3f4dd85a4056813f6c418a6780fa675a69c728fad28e88a7726c9dd for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xf901C093edC3AB68c796eD29253E8EAf3349663f',
    '0xd90c2DC41d97c62585841A8b6E0d500A5217B9Ab',
]])
def test_safe_withdraw_unlocked(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9520c7e117225afc930d1092bf35c17e6726c6564ed4e757eeb6a3c29d10304b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, multisig_address, timestamp, gas, amount = ethereum_accounts[0], ethereum_accounts[1], TimestampMS(1721130791000), '0.00095328952396285', '2404.451820314008697626'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=146,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'),
            amount=FVal(amount),
            location_label=multisig_address,
            notes=f'Withdraw {amount} SAFE from Safe{{Pass}} locking',
            counterparty=CPT_SAFE,
            address=SAFE_LOCKING,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=147,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Successfully executed safe transaction 0x1f5ea0fb049fabccf49f2a9e8ccd8ae95db0d32727d5c62ea329b0381a51a698 for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xd52623EE9A40402A5a9ED82Bb0417e04d88A778C',
    '0x89C5d54C979f682F40b73a9FC39F338C88B434c6',
]])
def test_safepass_start_vesting_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xfd07173651763370557d8300a8f5891d26ec7055238d6daf4f53c3f060d0f42d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, multisig_address, timestamp, gas = ethereum_accounts[0], ethereum_accounts[1], TimestampMS(1735818059000), '0.00149046414099075'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=118,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'),
            amount=ZERO,
            location_label=multisig_address,
            notes='Claim and start vesting of SAFE tokens from Safe{Pass}',
            counterparty=CPT_SAFE,
            address=SAFEPASS_AIRDROP,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=119,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Successfully executed safe transaction 0x8e01ca76365b063a7628f0072527f51579660103276990ab4f2b97e2de26e04b for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0x97c599819C95Aaf1BBC9063f4c743cCfCE7bc591',
    '0xEbfbf7A3006104fB1D3b68529A7B1b584acf4203',
]])
def test_safe_added_owner_indexed(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x42536687dbc0c93d6b18c451c458def1e9d78476f610c8909be31bf2ffd56a69')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, multisig_address, timestamp, gas = gnosis_accounts[0], gnosis_accounts[1], TimestampMS(1747908200000), '0.000097393118048512'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=57,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Upgrade Safe master copy to 0x29fcB43b46531BcA003ddC8FCB67FFE91900C762 for multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=60,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Add owner 0xfD90FAd33ee8b58f32c00aceEad1358e4AFC23f9 to multisig {multisig_address}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=multisig_address,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC5d494aa0CBabD7871af0Ef122fB410Fa25c3379']])
def test_safe_execute_tx_with_hash_in_topics(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf53c056368eaf1498ce9af5d1121b54e64d50dc22810690bb676bc29efaeb908')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    multisig_address = string_to_evm_address('0x0BeBD2FcA9854F657329324aA7dc90F656395189')
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1761739487000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000100222361747948'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=481,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes=f'Successfully executed safe transaction 0x9b0dd4dd2297320f153b19521311de7b9cd4e3fa40d40fe34e47dbea755ad2e4 for multisig {multisig_address}',  # noqa: E501
        counterparty=CPT_SAFE_MULTISIG,
        address=multisig_address,
    )]
