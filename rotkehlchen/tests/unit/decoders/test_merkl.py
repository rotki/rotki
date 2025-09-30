from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.merkl.constants import CPT_MERKL, MERKL_DISTRIBUTOR_ADDRESS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x31B3c272d4d47c84d1dF60E69d1abdaf2943E5Bc']])
def test_merkl_morpho_reward(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xaad239c0266abf4cf17536c8023ad2ebbea638e2e93a88bdcca33931a6a2e12a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1752610171000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000718262527749'),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=163,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:8453/erc20:0x2dAD3a13ef0C6366220f989157009e501e7938F8'),
        amount=FVal(reward_amount := '108.85588695952950918'),
        location_label=user_address,
        notes=f'Claim {reward_amount} EXTRA from Morpho via Merkl',
        address=MERKL_DISTRIBUTOR_ADDRESS,
        counterparty=CPT_MERKL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB81a0e6c38c3Fec8A171cFE9631F60127a0C5bfD']])
def test_merkl_multi_reward(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xa95d10273815bf576e9873ed75c634fef9f220b2f00e8b45abf63c9478c148d7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1753427615000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00008503835211301'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=246,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0x8292Bb45bf1Ee4d140127049757C2E0fF06317eD'),
        amount=FVal(reward_amount_1 := '2914.492832815667985199'),
        location_label=user_address,
        notes=f'Claim {reward_amount_1} RLUSD from Euler via Merkl',
        address=MERKL_DISTRIBUTOR_ADDRESS,
        counterparty=CPT_MERKL,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=249,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0xf3e621395fc714B90dA337AA9108771597b4E696'),
        amount=FVal(reward_amount_2 := '5.879047551691231043'),
        location_label=user_address,
        notes=f'Claim {reward_amount_2} rEUL from Euler via Merkl',
        address=MERKL_DISTRIBUTOR_ADDRESS,
        counterparty=CPT_MERKL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB81a0e6c38c3Fec8A171cFE9631F60127a0C5bfD']])
def test_merkl_multi_reward_multiprotocol(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1d9473e79cc211ab1d4b97a836cf8460eaea431863fb45dad87d27583d55ae94')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1751794103000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.0000838002'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=342,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0x8292Bb45bf1Ee4d140127049757C2E0fF06317eD'),
        amount=FVal(reward_amount_1 := '3472.713727005249892342'),
        location_label=user_address,
        notes=f'Claim {reward_amount_1} RLUSD from Euler via Merkl',
        address=MERKL_DISTRIBUTOR_ADDRESS,
        counterparty=CPT_MERKL,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=345,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0xf3e621395fc714B90dA337AA9108771597b4E696'),
        amount=FVal(reward_amount_2 := '17.213740039819138639'),
        location_label=user_address,
        notes=f'Claim {reward_amount_2} rEUL from Euler via Merkl',
        address=MERKL_DISTRIBUTOR_ADDRESS,
        counterparty=CPT_MERKL,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=347,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=FVal(reward_amount_3 := '0.158389'),
        location_label=user_address,
        notes=f'Claim {reward_amount_3} USDC from Merkl',
        address=MERKL_DISTRIBUTOR_ADDRESS,
        counterparty=CPT_MERKL,
    )]
