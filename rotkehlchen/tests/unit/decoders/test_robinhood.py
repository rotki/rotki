import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.weth.constants import CPT_WETH
from rotkehlchen.constants.assets import A_ETH, A_WETH_ROBINHOOD
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.robinhood import ROBINHOOD_MAINNET_NODE
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

WETH_ROBINHOOD_ADDRESS = '0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('robinhood_manager_connect_at_start', [(ROBINHOOD_MAINNET_NODE,)])
@pytest.mark.parametrize('robinhood_accounts', [['0xab4b90858B6E21a24b5933E58dB17547F3023CD5']])
def test_eth_transfer(robinhood_inquirer, robinhood_accounts):
    """A plain ETH transfer from a tracked account to an untracked EOA."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=robinhood_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x519dd0fa6fbf35a5872ca15b6beebe35926be896216423688c2a550e73bc5a00')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1788598347000)),
        location=Location.ROBINHOOD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000008487864'),
        location_label=(user := robinhood_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ROBINHOOD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(amount := '0.0005'),
        location_label=user,
        notes=f'Send {amount} ETH to {(to_address := "0x2bE31a40F72d255ee0Db3Af0c0C401A57FeCE626")}',  # noqa: E501
        address=to_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('robinhood_manager_connect_at_start', [(ROBINHOOD_MAINNET_NODE,)])
@pytest.mark.parametrize('robinhood_accounts', [['0x5149Ae7F9445E70331608EA03C592c078aE7399D']])
def test_weth_wrap(robinhood_inquirer, robinhood_accounts):
    """Wrapping ETH into the bridge-deployed proxy WETH, which only emits a mint Transfer."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=robinhood_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xab8c99c378b305802bec51639470d5db400600f97cb852ad60e2fdb969751a18')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1788598306000)),
        location=Location.ROBINHOOD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000016106971374'),
        location_label=(user := robinhood_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ROBINHOOD,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal(amount := '0.151202876837959731'),
        location_label=user,
        notes=f'Wrap {amount} ETH in WETH',
        counterparty=CPT_WETH,
        address=WETH_ROBINHOOD_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ROBINHOOD,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_WETH_ROBINHOOD,
        amount=FVal(amount),
        location_label=user,
        notes=f'Receive {amount} WETH',
        counterparty=CPT_WETH,
        address=WETH_ROBINHOOD_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('robinhood_manager_connect_at_start', [(ROBINHOOD_MAINNET_NODE,)])
@pytest.mark.parametrize('robinhood_accounts', [['0x933398e56cbf7466223D26Fb86cB9cC6815bE4B9']])
def test_weth_unwrap(robinhood_inquirer, robinhood_accounts):
    """Unwrapping WETH back to ETH, which only emits a burn Transfer."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=robinhood_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x9335f7adb10702264afba26c1e44bec5c8e89d30ffff4561901b4520b3cf3cee')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1788598146000)),
        location=Location.ROBINHOOD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00002032907549'),
        location_label=(user := robinhood_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ROBINHOOD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_WETH_ROBINHOOD,
        amount=FVal(amount := '0.001039858522146741'),
        location_label=user,
        notes=f'Unwrap {amount} WETH',
        counterparty=CPT_WETH,
        address=WETH_ROBINHOOD_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ROBINHOOD,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=user,
        notes=f'Receive {amount} ETH',
        counterparty=CPT_WETH,
        address=WETH_ROBINHOOD_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('robinhood_manager_connect_at_start', [(ROBINHOOD_MAINNET_NODE,)])
def test_native_balances_via_multicall(robinhood_inquirer):
    """The balance scanner is not deployed on Robinhood chain, so native balances
    go through Multicall3's getEthBalance. The WETH contract holds the wrapped supply."""
    balances = robinhood_inquirer.get_multi_balance(
        accounts=[WETH_ROBINHOOD_ADDRESS, (user := '0x5149Ae7F9445E70331608EA03C592c078aE7399D')],
    )
    assert set(balances) == {WETH_ROBINHOOD_ADDRESS, user}
    assert balances[WETH_ROBINHOOD_ADDRESS] > FVal(10000)
    assert balances[user] >= 0
