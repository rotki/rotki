from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.aave.gho.constants import (
    CPT_GHO,
    GHO_IDENTIFIER,
    STAKED_GHO_ADDRESS,
    STKGHO_IDENTIFIER,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5F8d3A0b0E986E36f6a556ebF1c3c4BDACcC987E']])
def test_activate_cooldown(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that the decoder handles the stkGHO cooldown activation event."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf9c30216153bc39ccd4abe0e8098b6013077be053a549aac5bc8944e26045a4f')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1772137403000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees := '0.000003585343272752'),
        location_label=(user := ethereum_accounts[0]),
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=406,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset(STKGHO_IDENTIFIER),
        amount=FVal('36.906756605958462147'),
        location_label=user,
        notes='Activate cooldown for 36.906756605958462147 stkGHO',
        counterparty=CPT_GHO,
        address=STAKED_GHO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5A580658e119CDFBbb7e0269c32C5Ddf40B53f6a']])
def test_stake_gho(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that the decoder handles staking GHO to receive stkGHO."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xb5a49e96536425c55ffa3d552d02cefecb5455100198c39900eaf538b35bf196')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1772137607000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees := '0.000008884571617488'),
        location_label=(user := ethereum_accounts[0]),
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=212,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset(GHO_IDENTIFIER),
        amount=FVal(amount := '115.46416512082666946'),
        location_label=user,
        notes=f'Set GHO spending approval of {user} by {STAKED_GHO_ADDRESS} to {amount}',
        address=STAKED_GHO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=213,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset(GHO_IDENTIFIER),
        amount=FVal(amount),
        location_label=user,
        notes=f'Stake {amount} GHO',
        counterparty=CPT_GHO,
        address=STAKED_GHO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=214,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset(STKGHO_IDENTIFIER),
        amount=FVal(amount),
        location_label=user,
        notes=f'Receive {amount} stkGHO from staking in GHO',
        counterparty=CPT_GHO,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5F8d3A0b0E986E36f6a556ebF1c3c4BDACcC987E']])
def test_redeem_stkgho(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that the decoder handles redeeming stkGHO back to GHO."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x74302dcb2e2d1959ef1fe7f639658e0f74e7b420fe0fd1599604e3ee2c0f5daf')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1772137523000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees := '0.000006341116107216'),
        location_label=(user := ethereum_accounts[0]),
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset(STKGHO_IDENTIFIER),
        amount=FVal(amount := '36.906756605958462147'),
        location_label=user,
        notes=f'Unstake {amount} stkGHO',
        counterparty=CPT_GHO,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset(GHO_IDENTIFIER),
        amount=FVal(amount),
        location_label=user,
        notes=f'Receive {amount} GHO after unstaking from GHO',
        counterparty=CPT_GHO,
        address=STAKED_GHO_ADDRESS,
    )]
