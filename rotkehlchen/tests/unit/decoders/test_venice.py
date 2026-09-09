from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.venice.constants import (
    CPT_VENICE,
    DIEM_TOKEN_ID,
    SVVV_TOKEN_ID,
    VENICE_AIRDROP_CONTRACT,
    VENICE_STAKING_CONTRACT,
    VVV_TOKEN_ID,
)
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    Location,
    SupportedBlockchain,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base-open-rpc',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [['0xF382a508c7a56Ef764cFECE6317b5bf81424Fa4F']])
def test_venice_airdrop_claim(
        base_inquirer: BaseInquirer,
        base_accounts: list[ChecksumEvmAddress],
        allow_base_routescan: None,
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7a5ecbf4c90f0b309b063bbdccaf0394250a7bfed592aedc30a1c242da69ae9b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741749039000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000002431104757863'),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=427,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=Asset(VVV_TOKEN_ID),
            amount=FVal(claimed_amount := '10'),
            location_label=user_address,
            notes=f'Claim {claimed_amount} VVV from Venice airdrop',
            counterparty=CPT_VENICE,
            address=VENICE_AIRDROP_CONTRACT,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'venice'},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base-open-rpc',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [['0x6E02D838572f0b0A9A0160B6f55348AD4C087734']])
def test_stake_vvv(
        base_inquirer: BaseInquirer,
        base_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xc440e54f7a53e372eb478b2b79873e6000d1ceee81754ad867e3b071da0e35f5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1788964145000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000005540898821601'),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=554,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset(VVV_TOKEN_ID),
            amount=FVal(reward_amount := '0.000075121196321699'),
            location_label=user_address,
            notes=f'Claim {reward_amount} VVV staking reward from Venice',
            counterparty=CPT_VENICE,
            address=VENICE_STAKING_CONTRACT,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=555,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(VVV_TOKEN_ID),
            amount=FVal(amount := '0.915604390377228329'),
            location_label=user_address,
            notes=f'Stake {amount} VVV',
            counterparty=CPT_VENICE,
            address=VENICE_STAKING_CONTRACT,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=556,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(SVVV_TOKEN_ID),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Receive {amount} sVVV after staking in Venice',
            counterparty=CPT_VENICE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base-open-rpc',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [['0x2E0940A7934A11a2ba03A8297A0e72b047196235']])
def test_mint_diem(
        base_inquirer: BaseInquirer,
        base_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xafbc27d2fcdd1c7f1ece4acecd04676a1c6f09fa74cdefd6e64127768bf0f994')  # noqa: E501
    with patch(
        'rotkehlchen.chain.evm.transactions.EvmTransactions._query_internal_transactions_for_parent_hash',
        return_value=([], None, None),
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1789030619000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000001984802060257'),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=813,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset(VVV_TOKEN_ID),
            amount=FVal(reward_amount := '3.199239242273140974'),
            location_label=user_address,
            notes=f'Claim {reward_amount} VVV staking reward from Venice',
            counterparty=CPT_VENICE,
            address=VENICE_STAKING_CONTRACT,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=814,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(SVVV_TOKEN_ID),
            amount=FVal(locked_amount := '26.624005413704394332'),
            location_label=user_address,
            notes=f'Deposit {locked_amount} sVVV as collateral to mint DIEM',
            counterparty=CPT_VENICE,
            address=VENICE_STAKING_CONTRACT,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=815,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=Asset(DIEM_TOKEN_ID),
            amount=FVal(minted_amount := '0.049852270557218694'),
            location_label=user_address,
            notes=f'Mint {minted_amount} DIEM by locking {locked_amount} sVVV',
            counterparty=CPT_VENICE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base-open-rpc',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [['0x529C3f796016301556Fe5402079cac7f409C9104']])
def test_burn_diem(
        base_inquirer: BaseInquirer,
        base_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x027ff791690139f1d4980a485fdde9ad5227d64f5a06285ba01c217845b9b86d')  # noqa: E501
    with patch(
        'rotkehlchen.chain.evm.transactions.EvmTransactions._query_internal_transactions_for_parent_hash',
        return_value=([], None, None),
    ):
        events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    unlocked_amount = '16.911991970432576022'
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1789033909000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000004013669320793'),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1165,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset(VVV_TOKEN_ID),
            amount=FVal(reward_amount := '0.512646425320401158'),
            location_label=user_address,
            notes=f'Claim {reward_amount} VVV staking reward from Venice',
            counterparty=CPT_VENICE,
            address=VENICE_STAKING_CONTRACT,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1166,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=Asset(DIEM_TOKEN_ID),
            amount=FVal(burned_amount := '0.05'),
            location_label=user_address,
            notes=f'Burn {burned_amount} DIEM to unlock {unlocked_amount} sVVV',
            counterparty=CPT_VENICE,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1167,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset(SVVV_TOKEN_ID),
            amount=FVal(unlocked_amount),
            location_label=user_address,
            notes=f'Withdraw {unlocked_amount} sVVV collateral by burning DIEM',
            counterparty=CPT_VENICE,
            address=VENICE_STAKING_CONTRACT,
        ),
    ]
