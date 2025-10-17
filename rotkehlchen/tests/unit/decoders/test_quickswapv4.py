from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V4
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x9ba704115F0ed3a431A025ffa0525fDD1D507C3c']])
def test_swap(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x16b0e096358a955edc51479fc3b32056c2fe5afc4d33ae9b31c36326e4e2426b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1756472597000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000001787593774673'),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=FVal(spend_amount := '0.01'),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in Quickswap V4',
        counterparty=CPT_QUICKSWAP_V4,
        address=(pool_address := string_to_evm_address('0xB780BD13876Dd8219d06aD88F88D6C72C35B902F')),  # noqa: E501
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:8453/erc20:0xe5f2fe713CDB192C85e67A912Ff8891b4E636614'),
        amount=FVal(receive_amount := '0.009988'),
        location_label=user_address,
        notes=f'Receive {receive_amount} stratUSD after a swap in Quickswap V4',
        counterparty=CPT_QUICKSWAP_V4,
        address=pool_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x6D2e91D1Ca448825909205aC1F60808999CdA5c1']])
def test_create_lp_position(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xd28c90ff2cf141de71eb3dc55505f97b6004c4bc6a2172f25204ccd7141e3f6f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1757008753000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.0000005922873229'),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x4200000000000000000000000000000000000006'),
        amount=FVal(weth_amount := '0.002319999929485927'),
        location_label=user_address,
        notes=f'Deposit {weth_amount} WETH to Quickswap V4 LP 520',
        counterparty=CPT_QUICKSWAP_V4,
        address=string_to_evm_address('0x5a9Ad2BB92B0B3E5C571FDD5125114E04E02be1a'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=FVal(usdc_amount := '10.075755'),
        location_label=user_address,
        notes=f'Deposit {usdc_amount} USDC to Quickswap V4 LP 520',
        counterparty=CPT_QUICKSWAP_V4,
        address=string_to_evm_address('0x5a9Ad2BB92B0B3E5C571FDD5125114E04E02be1a'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:8453/erc721:0x84715977598247125C3D6E2e85370d1F6fDA1eaF/520'),
        amount=ONE,
        location_label=user_address,
        notes='Create Quickswap V4 LP with id 520',
        counterparty=CPT_QUICKSWAP_V4,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x63aefe505c6F12e4D9EB8F404f4f4d19533dE681']])
def test_increase_liquidity(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7a75d3e6fc9eb896b445592c2f532e0ef481e76342c2b94dfac564e4e4a20ffd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1757070031000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000354774408415'),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=FVal(usdc_amount := '636.053256'),
        location_label=user_address,
        notes=f'Deposit {usdc_amount} USDC to Quickswap V4 LP 516',
        counterparty=CPT_QUICKSWAP_V4,
        address=string_to_evm_address('0x5D0bC342178C8Fe2c2f9A9fcC9D52555C99936db'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:8453/erc20:0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA'),
        amount=FVal(usdbc_amount := '1361.836043'),
        location_label=user_address,
        notes=f'Deposit {usdbc_amount} USDbC to Quickswap V4 LP 516',
        counterparty=CPT_QUICKSWAP_V4,
        address=string_to_evm_address('0x5D0bC342178C8Fe2c2f9A9fcC9D52555C99936db'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xF60De76791c2F09995df52Aa1c6e2E7DcF1E75d7']])
def test_decrease_liquidity(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x8adf08ff1a8e96ce3415f4bb6db694cd8e035cdafa760c151f7ee5c6b8164db0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1757077915000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00000248952938231'),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_ETH,
        amount=FVal(eth_amount := '0.027769801601916722'),
        location_label=user_address,
        notes=f'Remove {eth_amount} ETH from Quickswap V4 LP 531',
        counterparty=CPT_QUICKSWAP_V4,
        address=string_to_evm_address('0x84715977598247125C3D6E2e85370d1F6fDA1eaF'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset('eip155:8453/erc20:0x88Fb150BDc53A65fe94Dea0c9BA0a6dAf8C6e196'),
        amount=FVal(link_amount := '6.294089370856403526'),
        location_label=user_address,
        notes=f'Remove {link_amount} LINK from Quickswap V4 LP 531',
        counterparty=CPT_QUICKSWAP_V4,
        address=string_to_evm_address('0x84715977598247125C3D6E2e85370d1F6fDA1eaF'),
    )]
