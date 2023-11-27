import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.stakedao.constants import (
    CPT_STAKEDAO,
    STAKEDAO_CLAIMER1,
    STAKEDAO_CLAIMER2,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_CRV, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import timestamp_to_date


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6eEC7Dd840e3c1aBbaC157bB3C14e2aCBa72bC1e']])
def test_claim_one(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x3f747b34f1d0a6c59c62b5d6c3aba8f2bd278546cd53daa131327242c7c5b02e')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1684662791000)
    amount_str = '215.403304465915246838'
    period = 1684368000
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.003543266133945936')),
            location_label=user_address,
            notes='Burned 0.003543266133945936 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=580,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            balance=Balance(amount=FVal(amount_str)),
            location_label=user_address,
            notes=f'Claimed {amount_str} CRV from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_STAKEDAO,
            address=STAKEDAO_CLAIMER2,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3c28C42B24B7909c8292920929f083F60C4997A6']])
def test_claim_multiple(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xc866db3fcbef6359919c444de324b6f059f299ed155f5bff00abd81537c88627')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1678952351000)
    period = 1678924800
    amount1_str = '43.57001129039620188'
    amount2_str = '41.966838515681574848'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002833214770290904')),
            location_label=user_address,
            notes='Burned 0.002833214770290904 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=328,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            balance=Balance(amount=FVal(amount1_str)),
            location_label=user_address,
            notes=f'Claimed {amount1_str} CRV from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_STAKEDAO,
            address=STAKEDAO_CLAIMER1,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=330,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            balance=Balance(amount=FVal(amount2_str)),
            location_label=user_address,
            notes=f'Claimed {amount2_str} CRV from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_STAKEDAO,
            address=STAKEDAO_CLAIMER1,
        ),
    ]
    assert events == expected_events
