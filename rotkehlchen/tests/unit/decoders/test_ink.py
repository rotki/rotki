from unittest.mock import patch

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.weth.constants import CPT_WETH
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants.assets import A_ETH, A_WETH_INK
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.ink import INK_MAINNET_NODE
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

WETH_INK_ADDRESS = '0x4200000000000000000000000000000000000006'


@pytest.mark.vcr(filter_query_parameters=['apikey'], match_on=['match_rpc_calls'])
@pytest.mark.parametrize('ink_manager_connect_at_start', [(INK_MAINNET_NODE,)])
@pytest.mark.parametrize('ink_accounts', [['0x1f49a3fa2b5B5b61df8dE486aBb6F3b9df066d86']])
def test_eth_transfer(ink_inquirer, ink_accounts):
    """A plain ETH transfer from a tracked account to an untracked EOA."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ink_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x7a45e79494e0c2776e6c751869d9aa0e09d0deeb8a3ee9a2c0bdddf153858955')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1743498436000)),
        location=Location.INK,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000026108517193'),
        location_label=(user := ink_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.INK,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(amount := '0.005'),
        location_label=user,
        notes=f'Send {amount} ETH to {(to_address := "0xE57a32aF6A57bCB996C7c3De3431A7993C8e83dD")}',  # noqa: E501
        address=to_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'], match_on=['match_rpc_calls'])
@pytest.mark.parametrize('ink_manager_connect_at_start', [(INK_MAINNET_NODE,)])
@pytest.mark.parametrize('ink_accounts', [['0xB5006cF67dC8883037617657032A93b4CF238FA2']])
def test_weth_wrap(ink_inquirer, ink_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ink_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x0284fb7af67bdc480c701fb254bcaefe36b2773e3618f820836f23a948d4a3e7')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1743498412000)),
        location=Location.INK,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000030797162263'),
        location_label=(user := ink_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.INK,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal('0.0002'),
        location_label=user,
        notes='Wrap 0.0002 ETH in WETH',
        counterparty=CPT_WETH,
        address=WETH_INK_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.INK,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_WETH_INK,
        amount=FVal('0.0002'),
        location_label=user,
        notes='Receive 0.0002 WETH',
        counterparty=CPT_WETH,
        address=WETH_INK_ADDRESS,
    )]


@pytest.mark.vcr(match_on=['match_rpc_calls'])
@pytest.mark.parametrize('ink_manager_connect_at_start', [(INK_MAINNET_NODE,)])
def test_balances_via_scanner(ink_manager):
    """Native balances, token detection, and cached token balances use the deployed scanner."""
    inquirer = ink_manager.node_inquirer
    weth = A_WETH_INK.resolve_to_evm_token()
    address = '0xB5006cF67dC8883037617657032A93b4CF238FA2'
    call_contract = inquirer.call_contract
    assert inquirer.get_multi_balance([]) == {}
    with patch.object(inquirer, 'call_contract', side_effect=lambda **kwargs: call_contract(
            **(kwargs | {'block_identifier': 55290055}),
    )):
        assert inquirer.get_multi_balance([WETH_INK_ADDRESS]) == {
            WETH_INK_ADDRESS: FVal('11369.338869313054068124'),
        }
        assert ink_manager.tokens._get_multicall_token_balances([(address, [weth])]) == {
            address: {weth: FVal('0.000090247339519783')},
        }
        assert ink_manager.tokens.get_token_balances(
            address=address,
            tokens=[EvmTokenDetectionData(weth.identifier, weth.evm_address, weth.decimals)],
            call_order=None,
        ) == {weth: FVal('0.000090247339519783')}
