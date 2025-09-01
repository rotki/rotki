from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_POLYGON_POS_MATIC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x1834E499eA7F6759992AAd97362D985AA2efa5fc']])
def test_swap(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x50c55589a2a7b97bdb0c46815783993133c8bd099d9fcc8b91e2e465f00f4687')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        timestamp=(timestamp := TimestampMS(1756239853000)),
        location=Location.POLYGON_POS,
        sequence_index=0,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_amount := '0.011052763177263014'),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=1,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:137/erc20:0xeB51D9A39AD5EEF215dC0Bf39a8821ff804A0F01'),
        amount=FVal(approval_amount := '115792089237316195423570985008687907853269984665640564039457584006926.433208663'),  # noqa: E501
        location_label=user_address,
        notes=f'Set LGNS spending approval of {user_address} by 0xf5b509bB0909a69B1c207E495f687a596C168E12 to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0xf5b509bB0909a69B1c207E495f687a596C168E12'),
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=2,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:137/erc20:0xeB51D9A39AD5EEF215dC0Bf39a8821ff804A0F01'),
        amount=FVal(spend_amount := '6'),
        location_label=user_address,
        notes=f'Swap {spend_amount} LGNS in Quickswap V3',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0xB135Aa990D02E0a31cE953Af2bD7ed0EF6587403'),
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=3,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'),
        amount=FVal(receive_amount := '60.81850271428595855'),
        location_label=user_address,
        notes=f'Receive {receive_amount} DAI as the result of a swap in Quickswap V3',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0xB135Aa990D02E0a31cE953Af2bD7ed0EF6587403'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x10cF3DE9B6657E0309324D17653dab2249E20B52']])
def test_create_lp_position(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf09695f1682f0e6a8bc80eb7cfb7f4e39da22022c283c4633096fcde4e9c5557')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        timestamp=(timestamp := TimestampMS(1756380415000)),
        location=Location.POLYGON_POS,
        sequence_index=0,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_amount := '0.019757940084300544'),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=1,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
        amount=FVal(deposit1_amount := '9.910173'),
        location_label=user_address,
        notes=f'Deposit {deposit1_amount} USDC to Quickswap V3 LP 170082',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0xE4Fd591b652CC3e566f1fA2f9891b58633A04c54'),
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=2,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:137/erc20:0x47C8017f1e8998455493175F308B8eEE59DD18C1'),
        amount=FVal(deposit2_amount := '499603.603806805364163316'),
        location_label=user_address,
        notes=f'Deposit {deposit2_amount} $FRITH to Quickswap V3 LP 170082',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0xE4Fd591b652CC3e566f1fA2f9891b58633A04c54'),
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=3,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:137/erc721:0x8eF88E4c7CfbbaC1C163f7eddd4B578792201de6/170082'),
        amount=ONE,
        location_label=user_address,
        notes='Create Quickswap V3 LP with id 170082',
        counterparty=CPT_QUICKSWAP_V3,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xCE339d926E20193d386299De8df6Ff071B6885fF']])
def test_add_liquidity(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x0898cb40572a122d377248eb7f7926fd2a913839318c3b4a8be2b082bfea5b55')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        timestamp=(timestamp := TimestampMS(1756388739000)),
        location=Location.POLYGON_POS,
        sequence_index=0,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_amount := '0.008028270073324866'),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=1,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
        amount=FVal(deposit1_amount := '0.122014'),
        location_label=user_address,
        notes=f'Deposit {deposit1_amount} USDC to Quickswap V3 LP 169502',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0x74D1578E3Db15AE7605E1420dFC3801eEe98428e'),
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=2,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:137/erc20:0x4aDe9f87c3c155ECbE96eFCa0950D9d5Bfef93Cc'),
        amount=FVal(deposit2_amount := '23309.824084423422982329'),
        location_label=user_address,
        notes=f'Deposit {deposit2_amount} FLIP to Quickswap V3 LP 169502',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0x74D1578E3Db15AE7605E1420dFC3801eEe98428e'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x510994fC08e0157e6224e335c7F5a76fC0cD069a']])
def test_remove_liquidity(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7d9aa2df466775303d7b9f3e108d2ae418b8940d2db3c0681b0fdc3d3f8dca3d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        timestamp=(timestamp := TimestampMS(1756389021000)),
        location=Location.POLYGON_POS,
        sequence_index=0,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_amount := '0.010401180111986038'),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=1,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
        amount=FVal(withdraw1_amount := '14.275954'),
        location_label=user_address,
        notes=f'Remove {withdraw1_amount} USDC from Quickswap V3 LP 170033',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0x14Ef96A0f7d738Db906bdD5260E46AA47B1e6E45'),
    ), EvmEvent(
        tx_hash=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=2,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset('eip155:137/erc20:0xB5C064F955D8e7F38fE0460C556a72987494eE17'),
        amount=FVal(withdraw2_amount := '958.728216407276018128'),
        location_label=user_address,
        notes=f'Remove {withdraw2_amount} QUICK from Quickswap V3 LP 170033',
        counterparty=CPT_QUICKSWAP_V3,
        address=string_to_evm_address('0x14Ef96A0f7d738Db906bdD5260E46AA47B1e6E45'),
    )]
