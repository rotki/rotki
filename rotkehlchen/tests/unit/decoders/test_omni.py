import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.omni.constants import (
    CPT_OMNI,
    OMNI_AIDROP_CONTRACT,
    OMNI_STAKING_CONTRACT,
    OMNI_TOKEN_ID,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9211043D7012457a51caB901e5b184dA2Ef8b245']])
def test_claim(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xc626898273896eb771e9725137849dd104e388aad49687068a7681b5c54893fe')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
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
            amount=FVal(gas_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0005'),
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
            amount=FVal('14.411451809999998976'),
            location_label=ethereum_accounts[0],
            notes='Claim 14.411451809999998976 OMNI from the Omni genesis airdrop',
            counterparty=CPT_OMNI,
            address=OMNI_AIDROP_CONTRACT,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'omni'},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x361D6a0A6ce25c833081DAa7C31c416D4295eC5A']])
def test_stake(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x66f47dc448d7371eeccaa500af1aea76a1620de56c621187be83b1cc19bf861c')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp, gas_str, omni_str = TimestampMS(1713604307000), '0.00061736344563685', '5.06213676'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
            sequence_index=102,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset(OMNI_TOKEN_ID),
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Revoke OMNI spending approval of {ethereum_accounts[0]} by {OMNI_STAKING_CONTRACT}',  # noqa: E501
            address=OMNI_STAKING_CONTRACT,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=103,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(OMNI_TOKEN_ID),
            amount=FVal(omni_str),
            location_label=ethereum_accounts[0],
            notes=f'Stake {omni_str} OMNI',
            counterparty=CPT_OMNI,
            address=OMNI_STAKING_CONTRACT,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x77782FcAFAF67576b7423ae5173CDe6D83695796']])
def test_claim_and_stake(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x630c32c20d75c51ffe7b1db1cb3d82d357a8db4da10c1c5b212e01f8e92f6310')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp, gas_str, omni_str = TimestampMS(1713602555000), '0.000645708531342875', '15.3275649'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0005'),
            location_label=ethereum_accounts[0],
            notes='Spend 0.0005 ETH as a fee to claim the Omni genesis airdrop',
            counterparty=CPT_OMNI,
            address=OMNI_AIDROP_CONTRACT,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=Asset(OMNI_TOKEN_ID),
            amount=FVal(omni_str),
            location_label=ethereum_accounts[0],
            notes=f'Claim {omni_str} OMNI from the Omni genesis airdrop',
            counterparty=CPT_OMNI,
            address=OMNI_AIDROP_CONTRACT,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'omni'},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(OMNI_TOKEN_ID),
            amount=FVal(omni_str),
            location_label=ethereum_accounts[0],
            notes=f'Stake {omni_str} OMNI',
            counterparty=CPT_OMNI,
            address=OMNI_STAKING_CONTRACT,
        ),
    ]
    assert events == expected_events
