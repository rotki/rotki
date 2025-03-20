import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.pendle.constants import CPT_PENDLE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xFd83CCCecef02a334e6A86e7eA8D0aa0F61f1Faf']])
def test_lock_pendle(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc8b252de1a62daa57d4fe294f371e67550e087fdeffe972261e1acc890d84bd5')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, approval_amount, out_amount, locked_amount, lock_timestamp = ethereum_accounts[0], TimestampMS(1742478515000), '0.00118595784570676', '11.106239093069566243', '0.003254870108208791', '1110.62390930695662426', 1747267200  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Pay {out_amount} ETH as vePendle state broadcast fee',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=213,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0x808507121B80c02388fAd14726482e061B8da827'),
            amount=FVal(locked_amount),
            location_label=user_address,
            notes=f'Lock {locked_amount} PENDLE in voting escrow until {decoder.decoders["Pendle"].timestamp_to_date(lock_timestamp)}',  # noqa: E501
            counterparty=CPT_PENDLE,
            extra_data={'lock_time': 1747267200},
            address=string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=214,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x808507121B80c02388fAd14726482e061B8da827'),
            amount=FVal(approval_amount),
            location_label=user_address,
            notes=f'Set PENDLE spending approval of {user_address} by 0x4f30A9D41B80ecC5B94306AB4364951AE3170210 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xe0eAa41BdaF0F0126c75bD0a4F07a325dE842dd6']])
def test_unlock_pendle(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5bbfd3175156e347edb917f02311cbc7723d6f61d5bed532e7cfb947fe5b4d72')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, withdrawn_amount = ethereum_accounts[0], TimestampMS(1742472839000), '0.000059142779024945', '4497.51803084'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=411,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0x808507121B80c02388fAd14726482e061B8da827'),
            amount=FVal(withdrawn_amount),
            location_label=user_address,
            notes=f'Withdraw {withdrawn_amount} PENDLE from vote escrow',
            counterparty=CPT_PENDLE,
            address=string_to_evm_address('0x4f30A9D41B80ecC5B94306AB4364951AE3170210'),
        ),
    ]
    assert events == expected_events
