import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, CPT_GITCOIN
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_optimism_donation_received(database, optimism_inquirer, optimism_accounts):
    tx_hex = deserialize_evm_tx_hash('0x08685669305ee26060a5a78ae70065aec76d9e62a35f0837c291fb1232f33601')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1692176477000)
    amount_str = '0.00122'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount_str)),
        location_label=user_address,
        notes=f'Receive a gitcoin donation of {amount_str} ETH from 0xf0C2007aD05a8d66e98be932C698c232292eC8eA',  # noqa: E501
        counterparty=CPT_GITCOIN,
        address='0x99906Ea77C139000681254966b397a98E4bFdE21',
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_ethereum_donation_received(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x71fc406467f342f5801560a326aa29ac424381daf17cc04b5573960425ba605b')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1683655379000)
    amount_str = '0.001'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount_str)),
        location_label=user_address,
        notes=f'Receive a gitcoin donation of {amount_str} ETH from 0xc191a29203a83eec8e846c26340f828C68835715',  # noqa: E501
        counterparty=CPT_GITCOIN,
        address='0xDA2F26B30e8f5aa9cbE9c5B7Ed58E1cA81D0EbF2',
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x1B274eaCc333F4a904D72b576B55A108532aB379',
    # also track a grantee to see we handle donating to self fine
    '0xB352bB4E2A4f27683435f153A259f1B207218b1b',
]])
def test_ethereum_make_donation(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xd8d55b66f19a6dbf260d171fbb0c4c146f00c90919f1215cf691d7f0684771c6')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    tracked_grant = ethereum_accounts[1]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1683676595000)
    amount_str = '0.0006'
    gas_str = '0.011086829409239852'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount_str)),
        location_label=user_address,
        notes=f'Transfer a gitcoin donation of {amount_str} ETH to {tracked_grant}',
        counterparty=CPT_GITCOIN,
        address=tracked_grant,
    )]

    expected_events += [EvmEvent(
        tx_hash=evmhash,
        sequence_index=idx,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount_str)),
        location_label=user_address,
        notes=f'Make a gitcoin donation of {amount_str} ETH to {grant_address}',
        counterparty=CPT_GITCOIN,
        address=grant_address,
    ) for idx, grant_address in [
        (2, '0x713Bc00D1df5C452F172C317D39eFf71B771C163'),
        (107, '0xDEcf6615152AC768BFB688c4eF882e35DeBE08ac'),
        (109, '0x187089b65520D2208aB93FB471C4970c29eAf929'),
        (111, '0xb7081Fd06E7039D198D10A8b72B824e60C1B1E16'),
    ]]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_optimism_create_project(database, optimism_inquirer, optimism_accounts):
    tx_hex = deserialize_evm_tx_hash('0xe59f04c693e91f1659bd8bc718c993158efeb9af02c9c6337f039c44d8a822f6')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1691697693000)
    gas_str = '0.000085459641651569'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=65,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.DEPLOY,
        asset=A_ETH,
        balance=Balance(),
        location_label=user_address,
        notes=f'Create gitcoin project with id 779 and owner {user_address}',
        counterparty=CPT_GITCOIN,
        address='0x8e1bD5Da87C14dd8e08F7ecc2aBf9D1d558ea174',
    )]
    assert events == expected_events
