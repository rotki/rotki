from typing import Any

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.gnosis.modules.gnosisdao.constants import (
    CPT_GNOSISDAO,
    GNOSISDAO_TREASURY_SAFE,
    REDEMPTION_DEPOSIT_ADDRESS,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_XDAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

A_GNO = Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x7dfF87ac15Ca19DF043Bf76F2EF5efdfebB9d712']])
def test_gnosisdao_redemption_deposit(
        gnosis_inquirer: Any,
        gnosis_accounts: Any,
        allow_gnosis_etherscan: Any,
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x6e23bf76cb922eaf2fd85aed5453a0972aa1ee7121b11310f4ff852ebc440cf8')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1784289030000)),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas := '0.0000085954752'),
            location_label=(user_address := gnosis_accounts[0]),
            notes=f'Burn {gas} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GNO,
            amount=FVal(amount := '41.788245894808843714'),
            location_label=user_address,
            notes=f'Deposit {amount} GNO into the GnosisDAO treasury redemption',
            counterparty=CPT_GNOSISDAO,
            address=GNOSISDAO_TREASURY_SAFE,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GNO,
            amount=ZERO,
            location_label=user_address,
            notes=f'Revoke GNO spending approval of {user_address} by {REDEMPTION_DEPOSIT_ADDRESS}',  # noqa: E501
            address=REDEMPTION_DEPOSIT_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x8547C3710B8c1CC465C1ca2aF64Fe01Ed7918a28']])
def test_gnosisdao_redemption_claim(
        gnosis_inquirer: Any,
        gnosis_accounts: Any,
        allow_gnosis_etherscan: Any,
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xdb289aad6dc4b1064f6746631f617d28a503dd0d188505dc45364cd1e84488a6')),  # noqa: E501
    )
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784300750000)),
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_XDAI,
        amount=FVal(gas := '0.000375774'),
        location_label=(user_address := gnosis_accounts[0]),
        notes=f'Burn {gas} XDAI for gas',
        counterparty=CPT_GAS,
    )]
    expected_events.extend(EvmEvent(
        tx_ref=tx_hash,
        sequence_index=sequence_index,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset(asset_id),
        amount=FVal(amount),
        location_label=user_address,
        notes=f'Claim {amount} {symbol} from the GnosisDAO treasury redemption',
        counterparty=CPT_GNOSISDAO,
        address=GNOSISDAO_TREASURY_SAFE,
    ) for sequence_index, asset_id, amount, symbol in (
        (25, 'eip155:100/erc20:0x6C76971f98945AE98dD7d4DFcA8711ebea946eA6', '0.089328121498372831', 'wstETH'),  # noqa: E501
        (26, 'eip155:100/erc20:0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d', '113.691160118066439749', 'WXDAI'),  # noqa: E501
        (27, 'eip155:100/erc20:0x177127622c4A00F3d409B75571e12cB3c8973d3c', '150.617763514554259263', 'COW'),  # noqa: E501
        (28, 'eip155:100/erc20:0x4d18815D14fe5c3304e87B3FA18318baa5c23820', '238.849471135506162619', 'SAFE'),  # noqa: E501
        (29, 'eip155:100/erc20:0xD057604A14982FE8D88c5fC25Aac3267eA142a08', '379.440904238588614682', 'HOPR'),  # noqa: E501
        (30, 'eip155:100/erc20:0x37b60f4E9A31A64cCc0024dce7D0fD07eAA0F7B3', '58.196859946401765785', 'PNK'),  # noqa: E501
        (31, 'eip155:100/erc20:0x63803B132a59E481920c4c46a981bF45555b0421', '2.574993037107505724', 'auraBAL'),  # noqa: E501
    ))
    assert events == expected_events
