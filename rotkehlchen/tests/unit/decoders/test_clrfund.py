import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.arbitrum_one.modules.clrfund.constants import CPT_CLRFUND
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_ethstaker_matching_claim(arbitrum_one_inquirer, arbitrum_one_accounts):
    """Whats interesting here is that someone else claimed funds and not the recipient address"""
    tx_hash = deserialize_evm_tx_hash('0x5236f217873582446398c9b427a80a669be90b8a17fb5ed842f8d5d2925f3e7f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, user, amount = TimestampMS(1654833348000), arbitrum_one_accounts[0], '39566.332611058195231384'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.DONATE,
            asset=EvmToken('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            amount=FVal(amount),
            location_label=user,
            notes=f'Claim {amount} DAI as matching funds payout of clrfund Ethstaker round for {user}',  # noqa: E501
            counterparty=CPT_CLRFUND,
            address=string_to_evm_address('0xeD67d6682DC88E06c66e188027cA883455AfdADa'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_add_recipient(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x52f8b96df94af89566fb6048026d10411928f8cf1518788b2d3d0ef6623bafe2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    gas, timestamp, user, amount = '0.00483736114768445', TimestampMS(1650384723000), arbitrum_one_accounts[0], '0.005'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=user,
            notes=f'Apply to clrfund Ethstaker round with rotki and pay a {amount} ETH fee',
            counterparty=CPT_CLRFUND,
            address=string_to_evm_address('0xD2020926C0f1f8990DE806eBbAd510fa4b9b6f45'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x506498abf98C157eFE8B226E5EcAa0093aB77F04']])
def test_voted(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf2fa4e67b28a20e49fe69fe83c0848557141b852bf84367f260f285e38bef5c5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    gas, timestamp, user = '0.003010415219175718', TimestampMS(1653433014000), arbitrum_one_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=17,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user,
            notes='Vote in Clrfund Ethstaker round',
            counterparty=CPT_CLRFUND,
            address=string_to_evm_address('0xeD67d6682DC88E06c66e188027cA883455AfdADa'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x017dc108b35495f627B9F991AA34C982Ae1047Fb']])
def test_contribution(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x527e008a0fd9f0e0146eb842dfe7c47e2830e9cc05f07ca9908b23be1f8a18b8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    gas, timestamp, amount, user = '0.000313841956638943', TimestampMS(1653433994000), '8', arbitrum_one_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=EvmToken('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            amount=FVal(amount),
            location_label=user,
            notes=f'Donate {amount} DAI to Clrfund Ethstaker round',
            counterparty=CPT_CLRFUND,
            address=string_to_evm_address('0xeD67d6682DC88E06c66e188027cA883455AfdADa'),
        ),
    ]
    assert events == expected_events
