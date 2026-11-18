from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.chainlink.constants import (
    COMMUNITY_POOL,
    CPT_CHAINLINK,
    REWARD_VAULT,
    STAKING_V01,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_LINK
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x65D85F11012a0d55acfC4c63Bc449f2FBD7BffC1']])
def test_stake_v01(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x6529d12c864cbe499aa697d93c429e9b64402b607e7a1e69d9d84f40f1cd764f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1682420531000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.002562857126278616'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=226,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_LINK,
        amount=FVal(staked_amount := '500'),
        location_label=user_address,
        notes=f'Stake {staked_amount} LINK in Chainlink staking v0.1',
        counterparty=CPT_CHAINLINK,
        address=STAKING_V01,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4d29b7F953ba471fb650fc5842127b05e35949B5']])
def test_unstake_v01(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """The principal and the rewards come in one transfer, which is split in two events"""
    tx_hash = deserialize_evm_tx_hash('0x6379eb410a83e55b677d370080a03ba3f74b112e4227efea953ec819070b8063')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1776787151000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00010138883677739'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=928,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_LINK,
        amount=FVal(unstaked_amount := '50'),
        location_label=user_address,
        notes=f'Unstake {unstaked_amount} LINK from Chainlink staking v0.1',
        counterparty=CPT_CHAINLINK,
        address=STAKING_V01,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=930,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_LINK,
        amount=FVal(reward_amount := '2.31061816674'),
        location_label=user_address,
        notes=f'Receive {reward_amount} LINK as Chainlink staking v0.1 rewards',
        counterparty=CPT_CHAINLINK,
        address=STAKING_V01,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x40c9416c6c7458D4975F38e45B5Fb8834A9fe9CC']])
def test_migrate_v01(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """The principal and the rewards go to the community pool without passing through the
    staker's wallet. The rewards are earned and staked, while the principal stays staked."""
    tx_hash = deserialize_evm_tx_hash('0x286dd6596c91391aa8eef837c15589152f11118d63e3f249e94137fe228f390a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1701536363000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.0065219696410648'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=151,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_LINK,
        amount=ZERO,
        location_label=user_address,
        notes='Migrate 150 LINK staked in Chainlink staking v0.1 to the Chainlink community staking pool',  # noqa: E501
        counterparty=CPT_CHAINLINK,
        address=STAKING_V01,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=160,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_LINK,
        amount=FVal(reward_amount := '6.96238144758'),
        location_label=user_address,
        notes=f'Receive {reward_amount} LINK as Chainlink staking v0.1 rewards',
        counterparty=CPT_CHAINLINK,
        address=STAKING_V01,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=161,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_LINK,
        amount=FVal(reward_amount),
        location_label=user_address,
        notes=f'Stake {reward_amount} LINK of Chainlink staking v0.1 rewards in the Chainlink community staking pool',  # noqa: E501
        counterparty=CPT_CHAINLINK,
        address=COMMUNITY_POOL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC6F6662B0a27d9461058f329450AC61e7e841cd0']])
def test_stake_v02(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xcb05df6fb261af19b3af1caaff997da3fd3e32e0b38416fa7e3cd77859a97539')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794921515000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000379603841775675'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=94,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_LINK,
        amount=FVal(staked_amount := '11.61'),
        location_label=user_address,
        notes=f'Stake {staked_amount} LINK in the Chainlink community staking pool',
        counterparty=CPT_CHAINLINK,
        address=COMMUNITY_POOL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xAb62cC21cdC6Eb61fF42D73fAC0c6DA5aB4D1fD1']])
def test_unbond_v02(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xd3be07ca5a0bfc925cf9cb9f72e4b56e46ccad5467222ee1b700d01037c42b4f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794944351000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000038183607785536'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=290,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_LINK,
        amount=ZERO,
        location_label=user_address,
        notes='Start the unbonding period to unstake LINK from the Chainlink community staking pool',  # noqa: E501
        counterparty=CPT_CHAINLINK,
        address=COMMUNITY_POOL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x42116f5F801948ac22B27078145D53cFf365862b']])
def test_unstake_v02(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1923252e0dad549f37e882ab05c56e1706ae86df9e068df6591036c2e51638e9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794970367000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000247507232350248'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=125,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_LINK,
        amount=FVal(unstaked_amount := '423.48'),
        location_label=user_address,
        notes=f'Unstake {unstaked_amount} LINK from the Chainlink community staking pool',
        counterparty=CPT_CHAINLINK,
        address=COMMUNITY_POOL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xa5958e493C416B5A7C1bF559eBe00035C6dc8a6D']])
def test_claim_rewards_v02(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x540f59ea98505fb0e442cb2b294248e4c6445fba802dc2f6f853150b2cbd82d8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1794977135000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00020019367806764'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=196,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=A_LINK,
        amount=FVal(reward_amount := '24.269701731856717256'),
        location_label=user_address,
        notes=f'Claim {reward_amount} LINK of Chainlink staking rewards',
        counterparty=CPT_CHAINLINK,
        address=REWARD_VAULT,
    )]
