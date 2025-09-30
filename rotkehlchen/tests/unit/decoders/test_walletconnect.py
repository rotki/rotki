from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.walletconnect.constants import (
    CPT_WALLETCONNECT,
    WALLETCONECT_STAKE_WEIGHT,
    WCT_TOKEN_ID,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler
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
            amount=FVal(gas_amount),
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
            amount=FVal(token_amount),
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
            amount=FVal(gas_amount),
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
            amount=FVal(token_amount),
            location_label=user_address,
            notes=f'Stake {token_amount} WCT until {decoder.decoders["Walletconnect"].timestamp_to_date(lock_timestamp)}',  # type: ignore  # noqa: E501
            counterparty=CPT_WALLETCONNECT,
            address=WALLETCONECT_STAKE_WEIGHT,
            extra_data={'until': lock_timestamp},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xd14D32F30b184983d3360c6F4b6593d41eD834F4']])
def test_unstake(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x73d20d4ad0af8350fa66e9d8ee5a83b65b5099cde5a9ae51299c440793951b18')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, token_amount = TimestampMS(1732792847000), optimism_accounts[0], '0.000004252055654884', '248'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset(WCT_TOKEN_ID),
            amount=FVal(token_amount),
            location_label=user_address,
            notes=f'Unstake {token_amount} WCT',
            counterparty=CPT_WALLETCONNECT,
            address=WALLETCONECT_STAKE_WEIGHT,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4Bf0B0ed0c9520b24F7E30Ad51Fcd89781dAEc8d']])
def test_increase_lock(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
        database: 'DBHandler',
) -> None:
    # make sure WCT is in the DB (we have not yet added it in globalDB as of this writing and decoding this transaction has no transfers so it does not get autoadded)  # noqa: E501
    get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xeF4461891DfB3AC8572cCf7C794664A8DD927945'),
        chain_id=ChainID.OPTIMISM,
    )
    tx_hash = deserialize_evm_tx_hash('0xbf5de8df32c5faa598b56f0235f51ca779a659ee4686e959d89fc38798c62c54')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, unlock_time = TimestampMS(1732793011000), optimism_accounts[0], '0.000002761170017713', 1736985600  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=72,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset(WCT_TOKEN_ID),
            amount=ZERO,
            location_label=user_address,
            notes=f'Increase WCT staking expiration until {decoder.decoders["Walletconnect"].timestamp_to_date(unlock_time)}',  # type: ignore  # noqa: E501
            counterparty=CPT_WALLETCONNECT,
            address=WALLETCONECT_STAKE_WEIGHT,
            extra_data={'until': unlock_time},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x595a053dD045f7b803Dd29d965a5397FEfA9a5d5']])
def test_update_lock(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Updates an existing staking lock by adding more WCT to it"""
    tx_hash = deserialize_evm_tx_hash('0xf5c75dc26c66075cea2105cae62f31200a2518123b6106876229e661573bada7')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, token_amount, unlock_time = TimestampMS(1732792963000), optimism_accounts[0], '0.000003454138559574', '100.003508602839', 1738800000  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=47,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(WCT_TOKEN_ID),
            amount=FVal(token_amount),
            location_label=user_address,
            notes=f'Stake {token_amount} WCT until {decoder.decoders["Walletconnect"].timestamp_to_date(unlock_time)}',  # type: ignore  # noqa: E501
            counterparty=CPT_WALLETCONNECT,
            address=WALLETCONECT_STAKE_WEIGHT,
            extra_data={'until': unlock_time},
        ),
    ]
