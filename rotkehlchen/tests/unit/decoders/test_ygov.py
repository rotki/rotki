import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YGOV
from rotkehlchen.chain.ethereum.modules.yearn.ygov.constants import YGOV_ADDRESS
from rotkehlchen.constants.assets import A_CRVP_DAIUSDCTTUSD, A_ETH, A_YFI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xB04a6DB13942b6d4416AbeC5A8327866375c17a4']])
def test_ygov_stake(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1c596eb9189d124418d5bd060cb702acf20be8f7b18220fbec9b94a99b95c1d3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1594992345000)
    addy_user = ethereum_accounts[0]
    gas_amount, deposited_amount = '0.005269935', '1736.929114514645653598'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=addy_user,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=172,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_CRVP_DAIUSDCTTUSD,
            amount=FVal(deposited_amount),
            location_label=addy_user,
            notes=f'Deposit {deposited_amount} yDAI+yUSDC+yUSDT+yTUSD in ygov.finance',
            address=YGOV_ADDRESS,
            counterparty=CPT_YGOV,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xA7499Aa6464c078EeB940da2fc95C6aCd010c3Cc']])
def test_ygov_get_reward(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9063899641457daf68518b7017a4df30a79a0630224528aee0f2c483db76fc58')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1623310131000)
    addy_user = ethereum_accounts[0]
    gas_amount, reward_amount = '0.0010707', '0.224594237566776997'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=addy_user,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=182,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_YFI,
            amount=FVal(reward_amount),
            location_label=addy_user,
            notes=f'Collect reward of {reward_amount} YFI from ygov.finance',
            address=YGOV_ADDRESS,
            counterparty=CPT_YGOV,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x3AA33a58BFD82EA119E36b8886BC7E36E6F7Aa29']])
def test_ygov_exit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x42787b2b175d7f09401c3fd68c92f78982de2deef2214196261a31258c68006b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1633109458000)
    addy_user = ethereum_accounts[0]
    gas_amount, reward_amount, withdrawn_amount = '0.012938107', '2.281399151169433806', '665811.174187646507558478'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=addy_user,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_CRVP_DAIUSDCTTUSD,
            amount=FVal(withdrawn_amount),
            location_label=addy_user,
            notes=f'Withdraw {withdrawn_amount} YFI reward from ygov.finance',
            address=YGOV_ADDRESS,
            counterparty=CPT_YGOV,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=6,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_YFI,
            amount=FVal(reward_amount),
            location_label=addy_user,
            notes=f'Collect reward of {reward_amount} YFI from ygov.finance',
            address=YGOV_ADDRESS,
            counterparty=CPT_YGOV,
        ),
    ]
    assert expected_events == events
