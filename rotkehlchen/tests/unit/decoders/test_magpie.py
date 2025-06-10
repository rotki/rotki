from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.magpie.constants import CPT_MAGPIE, MAGPIE_ROUTER
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.parametrize('base_accounts', [['0x3a20BA3678C5c40F7CD48EB373fF8a501d170534']])
def test_magpie_eth_to_token_swap(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding a Magpie ETH to token swap on Base

    Data from:
    https://basescan.org/tx/0xe0694a8b16649877e82f7039e6e61265552e62c83d274e3994f4f8855a4eb352
    """
    tx_hash = deserialize_evm_tx_hash(
        '0xe0694a8b16649877e82f7039e6e61265552e62c83d274e3994f4f8855a4eb352',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]
    timestamp = TimestampMS(1747100759000)
    gas_amount = '0.000000857490760886'  # actual gas from test
    spend_amount = '0.00005'  # 50000000000000 / 10^18
    receive_amount = '3.603360047987326035'  # actual amount from test
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} ETH in Magpie',
            counterparty=CPT_MAGPIE,
            address=MAGPIE_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:8453/erc20:0xA88594D404727625A9437C3f886C7643872296AE'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} WELL from Magpie swap',
            counterparty=CPT_MAGPIE,
            address=MAGPIE_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.parametrize('base_accounts', [['0xF9c6Fc43a385362C9C8364bF9C5236314607c0A5']])
def test_magpie_token_to_token_swap(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding a Magpie token to token swap on Base

    Data from:
    https://basescan.org/tx/0xe8551212a0bb6f59a38883161ec11393f03ba6e8f2f71e8d3c41df0bfe0a71c6
    """
    tx_hash = deserialize_evm_tx_hash(
        '0xe8551212a0bb6f59a38883161ec11393f03ba6e8f2f71e8d3c41df0bfe0a71c6',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]

    timestamp = TimestampMS(1747098901000)
    gas_amount = '0.000005597469523105'  # actual gas from output
    rabby_fee_amount = '0.009750330804687233'  # Fee to Rabby
    spend_amount = '3.890381991070206089'  # VIRTUAL swapped (router amount)
    receive_amount = '7.574831'  # USDC received
    virtual_asset = Asset('eip155:8453/erc20:0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b')
    usdc_asset = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')  # USDC

    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=118,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=virtual_asset,
            amount=FVal('3.890381991070206089'),
            location_label=user_address,
            notes=(
                'Set VIRTUAL spending approval of 0xF9c6Fc43a385362C9C8364bF9C5236314607c0A5 '
                'by 0xEF42f78d25f4c681dcaD2597fA04877ff802eF4B to 3.890381991070206089'
            ),
            address=MAGPIE_ROUTER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=120,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=virtual_asset,
            amount=ZERO,
            location_label=user_address,
            notes=(
                'Revoke VIRTUAL spending approval of 0xF9c6Fc43a385362C9C8364bF9C5236314607c0A5 '
                'by 0xEF42f78d25f4c681dcaD2597fA04877ff802eF4B'
            ),
            address=MAGPIE_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=121,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=virtual_asset,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} VIRTUAL in Magpie',
            counterparty=CPT_MAGPIE,
            address=MAGPIE_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=122,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=usdc_asset,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} USDC from Magpie swap',
            counterparty=CPT_MAGPIE,
            address=MAGPIE_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=123,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.FEE,
            asset=virtual_asset,
            amount=FVal(rabby_fee_amount),
            location_label=user_address,
            notes=f'Pay {rabby_fee_amount} VIRTUAL as Rabby interface fee',
            counterparty=CPT_MAGPIE,
            address=MAGPIE_ROUTER,
        ),
    ]
    assert expected_events == events
