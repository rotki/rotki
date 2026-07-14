from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.modules.kinetiq.constants import (
    CPT_KINETIQ,
    KINETIQ_EARN_QUEUE,
    KINETIQ_EARN_VAULT,
    KINETIQ_STAKING_MANAGER,
)
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer

A_KHYPE = Asset('eip155:999/erc20:0xfD739d4e423301CE9385c1fb8850539D657C296D')
A_VKHYPE = Asset('eip155:999/erc20:0x9BA2EDc44E0A4632EB4723E81d4142353e1bB160')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xAE5028F1Aca223691F9Ca630c83CC4404511D87b']])
def test_kinetiq_stake(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x4038b03243cb10a8efd117e4126e44a74e8694167ecdfeb58736dfd915ce5cdb')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783545961000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.0000418122'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_HYPE,
            amount=FVal(staked_amount := '257.05977605'),
            location_label=hyperliquid_accounts[0],
            notes=f'Stake {staked_amount} HYPE in Kinetiq',
            counterparty=CPT_KINETIQ,
            address=KINETIQ_STAKING_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_KHYPE,
            amount=FVal(received_amount := '251.765493660103955706'),
            location_label=hyperliquid_accounts[0],
            notes=f'Receive {received_amount} kHYPE from staking in Kinetiq',
            counterparty=CPT_KINETIQ,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xd418224aE3c510B645112FD9275CCFD50F996ee4']])
def test_kinetiq_partner_stake(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    """Test that staking via a partner deployment (Flowdesk flowHYPE) is also decoded"""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x48bb914d934aa42806429092e302656ff671b4fb60bf20d0a3782892755f8bef')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1754935589000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.0051277856259259'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_HYPE,
            amount=FVal(staked_amount := '1'),
            location_label=hyperliquid_accounts[0],
            notes=f'Stake {staked_amount} HYPE in Kinetiq',
            counterparty=CPT_KINETIQ,
            address=string_to_evm_address('0xfdd35c5179E8594E237031dd945E0584Af29572b'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:999/erc20:0x86d96fF0E78Dba9570b00f75807ce21213a19f3d'),
            amount=FVal(received_amount := '1'),
            location_label=hyperliquid_accounts[0],
            notes=f'Receive {received_amount} flowHYPE from staking in Kinetiq',
            counterparty=CPT_KINETIQ,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xC16D03879B158604958A7bAE8b61763c2953a5f2']])
def test_kinetiq_queue_withdrawal(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x1638247ae17adceb57fb31545c569ceed387c1d82c9b8e9ef55cfcec5446bf25')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783593194000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.00290796414'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_KHYPE,
            amount=FVal(khype_amount := '8.95134721'),
            location_label=hyperliquid_accounts[0],
            notes=f'Queue unstaking of {khype_amount} kHYPE for 9.140056182774328838 HYPE from Kinetiq with withdrawal request id 0',  # noqa: E501
            counterparty=CPT_KINETIQ,
            address=KINETIQ_STAKING_MANAGER,
            extra_data={'withdrawal_id': 0},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xCADCE6cc55aF7Fe0d5570A19f3791E8a76e07e74']])
def test_kinetiq_confirm_withdrawal(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xacd376754d6b72d3975443c23bb34d3422282c10d215f8b9feb020c41f7bd574')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783572755000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.00001550675152'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_HYPE,
            amount=FVal(hype_amount := '100.09950089016336248'),
            location_label=hyperliquid_accounts[0],
            notes=f'Unstake {hype_amount} HYPE from Kinetiq',
            counterparty=CPT_KINETIQ,
            address=KINETIQ_STAKING_MANAGER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0x3A6f0416fB5678efe6eC415c984B0D64E456E2F7']])
def test_kinetiq_instant_unstake(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x507ff2318c3e35d619901831491b9d1b7228fc705bf92d1646bc3e42e57b1c93')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783573784000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.0000386778'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_KHYPE,
            amount=FVal(khype_amount := '4.5'),
            location_label=hyperliquid_accounts[0],
            notes=f'Instantly unstake {khype_amount} kHYPE from Kinetiq',
            counterparty=CPT_KINETIQ,
            address=KINETIQ_STAKING_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_HYPE,
            amount=FVal(hype_amount := '4.590272458558035808'),
            location_label=hyperliquid_accounts[0],
            notes=f'Receive {hype_amount} HYPE from unstaking in Kinetiq',
            counterparty=CPT_KINETIQ,
            address=string_to_evm_address('0x665b67793594fc5C251a3C95cbEb4B6245Cd2123'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0x226475888418bdD5B29C2C70bbd133869df39d08']])
def test_kinetiq_redelegate(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xb3eea91821a2a02e47df5aab9907755ff2c652480da4ec9e6d0ea6604fdc705e')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783543247000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.00002059695501'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_HYPE,
            amount=FVal(redelegated_amount := '459'),
            location_label=hyperliquid_accounts[0],
            notes=f'Request redelegation of {redelegated_amount} HYPE from validator 0xb8F45222a3246a2B0104696a1Df26842007c5Bc5 to validator 0xEEEe86F718F9Da3e7250624A460f6EA710E9C006 in Kinetiq',  # noqa: E501
            counterparty=CPT_KINETIQ,
            address=KINETIQ_STAKING_MANAGER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0x0F049Fea32a4AA8892596570f2F59791180449be']])
def test_kinetiq_earn_deposit(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x8307faa1eb25f100669a87aed4d026ccb5366974f39f215af731aca383ddcc01')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1781640798000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.000153270842071554'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_KHYPE,
            amount=FVal(deposited_amount := '3.542776370761928914'),
            location_label=hyperliquid_accounts[0],
            notes=f'Deposit {deposited_amount} kHYPE in Kinetiq Earn',
            counterparty=CPT_KINETIQ,
            address=KINETIQ_EARN_VAULT,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=A_VKHYPE,
            amount=FVal(shares_amount := '3.509614785423175029'),
            location_label=hyperliquid_accounts[0],
            notes=f'Receive {shares_amount} vkHYPE from depositing in Kinetiq Earn',
            counterparty=CPT_KINETIQ,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xF839aD355713BA6B2245f651979D110A26Ea59b9']])
def test_kinetiq_earn_withdraw_request(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x5039d2c51631d6b600a346b502d46fb9354a7948a24c4fdef8907f030b94aafe')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1780666943000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.00016954769121696'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=A_VKHYPE,
            amount=FVal(shares_amount := '24.979101460783017797'),
            location_label=hyperliquid_accounts[0],
            notes=f'Request withdrawal of {shares_amount} vkHYPE worth 25.214842088204747132 kHYPE from Kinetiq Earn',  # noqa: E501
            counterparty=CPT_KINETIQ,
            address=KINETIQ_EARN_QUEUE,
            extra_data={
                'request_id': '0xdbd575ad894695b2b220863aea4c520c0b6b2683d1a6bc1f1794fa4b9c9de669',
                'amount_of_assets': '25.214842088204747132',
                'asset_out': 'eip155:999/erc20:0xfD739d4e423301CE9385c1fb8850539D657C296D',
            },
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xD101497Ae918Fdbb1347704cDbea3440C5471473']])
def test_kinetiq_earn_withdraw_solve(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
):
    """Test the execution of a queued Kinetiq Earn withdrawal (here self-solved by the user)"""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xd4323118eeb3e5614bb1bda3149d35f4775e847f8280eb52d86cc1157106a94a')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1779687913000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.000752592441132494'),
            location_label=hyperliquid_accounts[0],
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_KHYPE,
            amount=FVal(withdrawn_amount := '393.719079254754886309'),
            location_label=hyperliquid_accounts[0],
            notes=f'Withdraw {withdrawn_amount} kHYPE from Kinetiq Earn',
            counterparty=CPT_KINETIQ,
            address=string_to_evm_address('0xb3C859c519052eb5111c321Db1114ae006837F4C'),
        ),
    ]
