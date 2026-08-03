from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.modules.project_x.constants import (
    CPT_PROJECT_X,
    PROJECT_X_NFT_MANAGER,
    PROJECT_X_SWAP_ROUTER,
)
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.hyperliquid import HYPERLIQUID_PUBLIC_RPC_NODES
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [HYPERLIQUID_PUBLIC_RPC_NODES])
def test_project_x_remove_liquidity(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x3ee329d9d1e36ee245be047722375722ed8cf3f1dbe179c0b963261e6f4fd208')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1759126087000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.00002794716'),
            location_label=(user_address := hyperliquid_accounts[0]),
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_HYPE,
            amount=FVal(hype_amount := '6.354190175639524452'),
            location_label=user_address,
            notes=f'Remove {hype_amount} HYPE from Project X LP 194165',
            counterparty=CPT_PROJECT_X,
            address=PROJECT_X_NFT_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=Asset('eip155:999/erc20:0x33Af3c2540Ba72054e044EFe504867B39aE421f5'),
            amount=FVal(xpl_amount := '325.892481110519187375'),
            location_label=user_address,
            notes=f'Remove {xpl_amount} UXPL from Project X LP 194165',
            counterparty=CPT_PROJECT_X,
            address=PROJECT_X_NFT_MANAGER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [HYPERLIQUID_PUBLIC_RPC_NODES])
def test_project_x_deposit(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x0c376aa1b6479f4cda44121bffb25c13f4b239fd21db3eb72f5a727a63228127')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1758911312000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.001936671899605165'),
            location_label=(user_address := hyperliquid_accounts[0]),
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
            amount=FVal(hype_amount := '17.323403742507013919'),
            location_label=user_address,
            notes=f'Deposit {hype_amount} HYPE to Project X LP 194165',
            counterparty=CPT_PROJECT_X,
            address=PROJECT_X_NFT_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:999/erc20:0x33Af3c2540Ba72054e044EFe504867B39aE421f5'),
            amount=FVal(uxpl_amount := '479.845881806888583935'),
            location_label=user_address,
            notes=f'Deposit {uxpl_amount} UXPL to Project X LP 194165',
            counterparty=CPT_PROJECT_X,
            address=string_to_evm_address('0xBD0CF45A8f47E27257F441529Aa684684dCd13c9'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:999/erc721:0xeaD19AE861c29bBb2101E834922B2FEee69B9091/194165'),
            amount=ONE,
            location_label=user_address,
            notes='Create Project X LP with id 194165',
            counterparty=CPT_PROJECT_X,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [HYPERLIQUID_PUBLIC_RPC_NODES])
def test_project_x_collect_multiple_positions(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x687e863cac346ecf9fd9207e89e2c6932bda9508ed9343dae87b0f2152f8a532')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1759050575000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.002159563979601392'),
            location_label=(user_address := hyperliquid_accounts[0]),
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_HYPE,
            amount=FVal(hype_amount := '0.242168189683634854'),
            location_label=user_address,
            notes=f'Collect {hype_amount} HYPE as Project X LP fees',
            counterparty=CPT_PROJECT_X,
            address=PROJECT_X_NFT_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=22,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:999/erc20:0x33Af3c2540Ba72054e044EFe504867B39aE421f5'),
            amount=FVal(uxpl_amount := '6.808632161878741005'),
            location_label=user_address,
            notes=f'Collect {uxpl_amount} UXPL as Project X LP fees',
            counterparty=CPT_PROJECT_X,
            address=PROJECT_X_NFT_MANAGER,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=23,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:999/erc20:0xB8CE59FC3717ada4C02eaDF9682A9e934F625ebb'),
            amount=FVal(usdt0_amount := '0.012114'),
            location_label=user_address,
            notes=f'Collect {usdt0_amount} USDT0 as Project X LP fees',
            counterparty=CPT_PROJECT_X,
            address=PROJECT_X_NFT_MANAGER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xA06c44151E84a85456A1370CC73a23848D1802fF']])
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [HYPERLIQUID_PUBLIC_RPC_NODES])
def test_project_x_collect_single_position(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xd034062c4f3847df06c615246ce3da62d76ce80734b4bdf4f73c5aca78fac7c3')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1769802719000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.000114288561200199'),
            location_label=(user_address := hyperliquid_accounts[0]),
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:999/erc20:0x27eC642013bcB3D80CA3706599D3cdA04F6f4452'),
            amount=FVal(upump_amount := '35417.508814'),
            location_label=user_address,
            notes=f'Collect {upump_amount} UPUMP as Project X LP fees for position 344049',
            counterparty=CPT_PROJECT_X,
            address=(pool_address := string_to_evm_address(
                '0x043538c4d9dF365833b741BA2a3555787DE947d3',
            )),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:999/erc20:0xB8CE59FC3717ada4C02eaDF9682A9e934F625ebb'),
            amount=FVal(usdt0_amount := '103.372953'),
            location_label=user_address,
            notes=f'Collect {usdt0_amount} USDT0 as Project X LP fees for position 344049',
            counterparty=CPT_PROJECT_X,
            address=pool_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0x2E0940A7934A11a2ba03A8297A0e72b047196235']])
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [HYPERLIQUID_PUBLIC_RPC_NODES])
def test_project_x_swap_router(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xbf1fc862b5c4fa9f828a7a8b79acf9a7b8b7691c13127fd6d0a2d012d036ed9e')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1758894288000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.000226547'),
            location_label=(user_address := hyperliquid_accounts[0]),
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_HYPE,
            amount=ONE,
            location_label=user_address,
            notes='Swap 1 HYPE in Project X',
            counterparty=CPT_PROJECT_X,
            address=PROJECT_X_SWAP_ROUTER,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:999/erc20:0x33Af3c2540Ba72054e044EFe504867B39aE421f5'),
            amount=FVal(uxpl_amount := '35.321460680290600636'),
            location_label=user_address,
            notes=f'Receive {uxpl_amount} UXPL as the result of a swap in Project X',
            counterparty=CPT_PROJECT_X,
            address=PROJECT_X_SWAP_ROUTER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [HYPERLIQUID_PUBLIC_RPC_NODES])
@pytest.mark.parametrize('tx_hash_hex', [
    '0xf857c5618ea0a84386856e02baa068ec35e4caf142f4371f059563bba6ccab1c',
    '0x6b780ce9ce6f0b9b2d13f741b75f7a867bcdd20ec3b711d0622241cd4abfb090',
    '0xaca539a38c68d436958ffd4f6c8c15ff8793e4f1612202aa57f5c99105f3c076',
])
def test_project_x_position_operations(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
        tx_hash_hex: str,
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash(tx_hash_hex)),
    )
    user_address = hyperliquid_accounts[0]
    uxpl = Asset('eip155:999/erc20:0x33Af3c2540Ba72054e044EFe504867B39aE421f5')
    usdt0 = Asset('eip155:999/erc20:0xB8CE59FC3717ada4C02eaDF9682A9e934F625ebb')
    pool_address = string_to_evm_address('0xC8257742C0fB75EF6a6b7f31cbB10A3c313D9DF0')
    position_asset = Asset('eip155:999/erc721:0xeaD19AE861c29bBb2101E834922B2FEee69B9091/192020')
    if tx_hash_hex == '0xf857c5618ea0a84386856e02baa068ec35e4caf142f4371f059563bba6ccab1c':
        expected_events = [
            EvmEvent(
                tx_ref=tx_hash,
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1759919686000)),
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_HYPE,
                amount=FVal(gas_amount := '0.000018733358137287'),
                location_label=user_address,
                notes=f'Burn {gas_amount} HYPE for gas',
                counterparty=CPT_GAS,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=21,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REWARD,
                asset=uxpl,
                amount=FVal(uxpl_amount := '0.097366748274519809'),
                location_label=user_address,
                notes=f'Collect {uxpl_amount} UXPL as Project X LP fees for position 192020',
                counterparty=CPT_PROJECT_X,
                address=pool_address,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=22,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.REWARD,
                asset=usdt0,
                amount=FVal(usdt0_amount := '0.086071'),
                location_label=user_address,
                notes=f'Collect {usdt0_amount} USDT0 as Project X LP fees for position 192020',
                counterparty=CPT_PROJECT_X,
                address=pool_address,
            ),
        ]
    elif tx_hash_hex == '0x6b780ce9ce6f0b9b2d13f741b75f7a867bcdd20ec3b711d0622241cd4abfb090':
        expected_events = [
            EvmEvent(
                tx_ref=tx_hash,
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1783330711000)),
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_HYPE,
                amount=FVal(gas_amount := '0.000030671853341283'),
                location_label=user_address,
                notes=f'Burn {gas_amount} HYPE for gas',
                counterparty=CPT_GAS,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=26,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.APPROVE,
                asset=position_asset,
                amount=ZERO,
                location_label=user_address,
                notes=f'Revoke PRJX-V3-POS spending approval of {user_address} by {ZERO_ADDRESS}',
                address=ZERO_ADDRESS,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=27,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                asset=position_asset,
                amount=ONE,
                location_label=user_address,
                notes='Exit Project X LP with id 192020',
                counterparty=CPT_PROJECT_X,
                address=ZERO_ADDRESS,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=28,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                asset=uxpl,
                amount=FVal(uxpl_amount := '2.345212099724275851'),
                location_label=user_address,
                notes=f'Remove {uxpl_amount} UXPL from Project X LP 192020',
                counterparty=CPT_PROJECT_X,
                address=pool_address,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=29,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                asset=usdt0,
                amount=FVal(usdt0_amount := '0.001783'),
                location_label=user_address,
                notes=f'Remove {usdt0_amount} USDT0 from Project X LP 192020',
                counterparty=CPT_PROJECT_X,
                address=pool_address,
            ),
        ]
    else:
        expected_events = [
            EvmEvent(
                tx_ref=tx_hash,
                sequence_index=0,
                timestamp=(timestamp := TimestampMS(1758877711000)),
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_HYPE,
                amount=FVal(gas_amount := '0.000173324668414979'),
                location_label=user_address,
                notes=f'Burn {gas_amount} HYPE for gas',
                counterparty=CPT_GAS,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=3,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.APPROVE,
                asset=usdt0,
                amount=ZERO,
                location_label=user_address,
                notes=(
                    f'Revoke USDT0 spending approval of {user_address} '
                    f'by {PROJECT_X_NFT_MANAGER}'
                ),
                address=PROJECT_X_NFT_MANAGER,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=4,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                asset=uxpl,
                amount=FVal(uxpl_amount := '0.823276654566826262'),
                location_label=user_address,
                notes=f'Deposit {uxpl_amount} UXPL to Project X LP 192020',
                counterparty=CPT_PROJECT_X,
                address=pool_address,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=5,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                asset=usdt0,
                amount=FVal(usdt0_amount := '1.5'),
                location_label=user_address,
                notes=f'Deposit {usdt0_amount} USDT0 to Project X LP 192020',
                counterparty=CPT_PROJECT_X,
                address=pool_address,
            ), EvmEvent(
                tx_ref=tx_hash,
                sequence_index=6,
                timestamp=timestamp,
                location=Location.HYPERLIQUID,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                asset=position_asset,
                amount=ONE,
                location_label=user_address,
                notes='Create Project X LP with id 192020',
                counterparty=CPT_PROJECT_X,
                address=ZERO_ADDRESS,
            ),
        ]

    assert events == expected_events
