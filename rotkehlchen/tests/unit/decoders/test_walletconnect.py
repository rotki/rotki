from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.walletconnect.constants import (
    CPT_WALLETCONNECT,
    WALLETCONECT_STAKE_WEIGHT,
    WCT_TOKEN_ID,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4C0F41D710395D0e4d1afcA4207F8C72C0667140']])
def test_airdrop_claim(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1bf831eb53a09cbd1ed309b938d3a09d0a00c17cd777830e3a47f49422eff3e6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, token_amount = TimestampMS(1732720037000), optimism_accounts[0], '0.000002227023099306', '181.44172120901'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=185,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=Asset(WCT_TOKEN_ID),
            balance=Balance(FVal(token_amount)),
            location_label=user_address,
            notes=f'Claim {token_amount} WCT from walletconnect airdrop',
            counterparty=CPT_WALLETCONNECT,
            address=string_to_evm_address('0xa86Ca428512D0A18828898d2e656E9eb1b6bA6E7'),
            extra_data={'airdrop_identifier': 'walletconnect'},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xc0d5dBe750bb5c001Ba8C499385143f566611679']])
def test_stake(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xcc691ea8eeb56fd5f5ceb98879e3571ee167a2ac4c5bad4c9463127262d096af')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, token_amount, lock_timestamp = TimestampMS(1732726673000), optimism_accounts[0], '0.000000666285515991', '184.286559270201', 1734566400  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=75,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(WCT_TOKEN_ID),
            balance=Balance(FVal(token_amount)),
            location_label=user_address,
            notes=f'Stake {token_amount} WCT until {decoder.decoders["Walletconnect"].timestamp_to_date(lock_timestamp)}',  # type: ignore  # noqa: E501
            counterparty=CPT_WALLETCONNECT,
            address=WALLETCONECT_STAKE_WEIGHT,
            extra_data={'until': lock_timestamp},
        ),
    ]
