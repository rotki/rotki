import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN
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


