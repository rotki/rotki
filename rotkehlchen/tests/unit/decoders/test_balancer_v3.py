from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V3
from rotkehlchen.chain.evm.decoding.balancer.v3.constants import VAULT_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_XDAI
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    CacheType,
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.globaldb.handler import GlobalDBHandler


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x18B5602e067e8D21A077B81914a48f84Fe82Be82']])
def test_add_liquidity_imbalanced(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xbc89bf067bc7ca7cff308538c90401fce967bbfeb11c588454011ff5e1aa21a9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755582935000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.00004983752005185')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:1/erc20:0xb4444468e444f89e1c2CAc2F1D3ee7e336cBD1f5'),
        amount=(rzr_amount := FVal('5.202232006059568136')),
        location_label=user_address,
        notes=f'Deposit {rzr_amount} RZR to a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0xF2d8ad2984aA8050dD1CA1e74b862b165f7a622A'),
        amount=(pool_amount := FVal('0.984172588667883394')),
        location_label=user_address,
        notes=f'Receive {pool_amount} wstETHR from a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xF8E85fD6A2a73A5d2CC9df4209Ac0C1dc16E15a4']])
def test_add_liquidity_proportionally(arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x0ea5100f442d6a998af7c91226d9d5685acbc628e7c838703d30c5b3002cec6c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1754617078000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000003302741162')),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=20,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:42161/erc20:0xba5DdD1f9d7F570dc94a51479a000E3BCE967196'),
        amount=(approval_amount := FVal('115792089237316195423570985008687907853269984665640564039457.528612700754425203')),  # noqa: E501
        location_label=user_address,
        notes=f'Set AAVE spending approval of {user_address} by 0x000000000022D473030F116dDEE9F6B43aC78BA3 to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=21,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=(eth_amount := FVal('0.004580101204116616')),
        location_label=user_address,
        notes=f'Deposit {eth_amount} ETH to a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=string_to_evm_address('0xEAedc32a51c510d35ebC11088fD5fF2b47aACF2E'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=22,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:42161/erc20:0xba5DdD1f9d7F570dc94a51479a000E3BCE967196'),
        amount=(aave_amount := FVal('0.055395212375214732')),
        location_label=user_address,
        notes=f'Deposit {aave_amount} AAVE to a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=23,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:42161/erc20:0x5Ea58d57952b028c40Bd200E5AFF20FC4b590f51'),
        amount=(pool_amount := FVal('0.012845932155320774')),
        location_label=user_address,
        notes=f'Receive {pool_amount} reCLAMM-AAVE-WETH from a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xDDA0E94955C637E30052CB28e73ce04C265f328b']])
def test_remove_liquidity_imbalanced(base_inquirer: 'BaseInquirer', base_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x8c6721fe24583cc69a64aa656e2c2235c3a8631ae6d4573807e24cb7ed7ec342')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755641555000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000001874470426444')),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=9,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:8453/erc20:0x88C044Fb203b58B12252Be7242926b1eEB113b4A'),
        amount=(pool_amount := FVal('1904.78294817015615997')),
        location_label=user_address,
        notes=f'Set WETH-USDC spending approval of {user_address} by 0x3f170631ed9821Ca51A59D996aB095162438DC10 to {pool_amount}',  # noqa: E501
        address=string_to_evm_address('0x3f170631ed9821Ca51A59D996aB095162438DC10'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:8453/erc20:0x88C044Fb203b58B12252Be7242926b1eEB113b4A'),
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke WETH-USDC spending approval of {user_address} by 0x3f170631ed9821Ca51A59D996aB095162438DC10',  # noqa: E501
        address=string_to_evm_address('0x3f170631ed9821Ca51A59D996aB095162438DC10'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=12,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x88C044Fb203b58B12252Be7242926b1eEB113b4A'),
        amount=pool_amount,
        location_label=user_address,
        notes=f'Return {pool_amount} WETH-USDC to a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=(usdc_amount := FVal('1894.120179')),
        location_label=user_address,
        notes=f'Withdraw {usdc_amount} USDC from a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x4B5Bed4b42a629Fd6bFF77e6e4444A071f404862']])
def test_remove_liquidity_proportionally(gnosis_inquirer: 'GnosisInquirer', gnosis_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x6dc9174eb7a4cf8c39bc65b5166359c1de6da8e19c160d896bf4db588496e82a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1754669850000)),
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_XDAI,
        amount=(gas_amount := FVal('0.00000003232853047')),
        location_label=(user_address := gnosis_accounts[0]),
        notes=f'Burn {gas_amount} XDAI for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=7,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:100/erc20:0xca13F615035965Ca6E9103a620B4Ce0157324F71'),
        amount=(approval_amount := FVal('0.153384732332713085')),
        location_label=user_address,
        notes=f'Set 40WBTC-10WETH-50USDT spending approval of {user_address} by 0x4eff2d77D9fFbAeFB4b141A3e494c085b3FF4Cb5 to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0x4eff2d77D9fFbAeFB4b141A3e494c085b3FF4Cb5'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=9,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:100/erc20:0xca13F615035965Ca6E9103a620B4Ce0157324F71'),
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke 40WBTC-10WETH-50USDT spending approval of {user_address} by 0x4eff2d77D9fFbAeFB4b141A3e494c085b3FF4Cb5',  # noqa: E501
        address=string_to_evm_address('0x4eff2d77D9fFbAeFB4b141A3e494c085b3FF4Cb5'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=10,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:100/erc20:0xca13F615035965Ca6E9103a620B4Ce0157324F71'),
        amount=approval_amount,
        location_label=user_address,
        notes=f'Return {approval_amount} 40WBTC-10WETH-50USDT to a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:100/erc20:0x4ECaBa5870353805a9F068101A40E0f32ed605C6'),
        amount=(usdt_amount := FVal('48.15311')),
        location_label=user_address,
        notes=f'Withdraw {usdt_amount} USDT from a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=12,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:100/erc20:0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1'),
        amount=(weth_amount := FVal('0.002428675787440334')),
        location_label=user_address,
        notes=f'Withdraw {weth_amount} WETH from a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:100/erc20:0x8e5bBbb09Ed1ebdE8674Cda39A0c169401db4252'),
        amount=(wbtc_amount := FVal('0.000328')),
        location_label=user_address,
        notes=f'Withdraw {wbtc_amount} WBTC from a Balancer v3 pool',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x5aA57B34DaaDB76ea486157B3D4472C4DF536C82']])
def test_swap_via_batch_router(base_inquirer: 'BaseInquirer', base_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xbffb6bd2994f90676be45db667203317f0f70afb4eaa3832271e02e8dffb8101')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755679029000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000007558210030013')),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.SPEND,
        timestamp=timestamp,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=(out_amount := FVal('6.53544')),
        location_label=user_address,
        notes=f'Swap {out_amount} USDC in Balancer v3',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.RECEIVE,
        timestamp=timestamp,
        asset=A_ETH,
        amount=(in_amount := FVal('0.001549083846430882')),
        location_label=user_address,
        notes=f'Receive {in_amount} ETH as the result of a swap in Balancer v3',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD17AE94E595c3987c277114AEcb377e89450Bc07']])
def test_swap(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list['ChecksumEvmAddress']) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x3dabc20af2bc5bf72c42fd1e915578f789189c2f09ec8049c4a6e3a2921b1baf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755614699000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.0013000257121251')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        timestamp=timestamp,
        asset=Asset('eip155:1/erc20:0x7Bc3485026Ac48b6cf9BaF0A377477Fff5703Af8'),
        amount=(out_amount := FVal('217')),
        location_label=user_address,
        notes=f'Swap {out_amount} waEthUSDT in Balancer v3',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        timestamp=timestamp,
        asset=Asset('eip155:1/erc20:0xD4fa2D31b7968E448877f69A96DE69f5de8cD23E'),
        amount=(in_amount := FVal('215.913782')),
        location_label=user_address,
        notes=f'Receive {in_amount} waEthUSDC as the result of a swap in Balancer v3',
        counterparty=CPT_BALANCER_V3,
        address=VAULT_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_BALANCER_V3]])
@pytest.mark.parametrize('ethereum_accounts', [['0x719a143654a0C4621F49FA77077800ef3F5C3b40']])
def test_gauge_deposit(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
        globaldb: 'GlobalDBHandler',
):
    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.BALANCER_V3_POOLS, str(ethereum_inquirer.chain_id.value)),
            values=['0x57c23c58B1D8C3292c15BEcF07c62C5c52457A42'],
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.BALANCER_V3_GAUGES, str(ethereum_inquirer.chain_id.value)),
            values=['0x70A1c01902DAb7a45dcA1098Ca76A8314dd8aDbA'],
        )
    tx_hash = deserialize_evm_tx_hash('0x50ce5d69c6856fe4501b537b81cddea6327d3082a908e587775a6356a31ab6c8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755709055000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000616747733174853'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:1/erc20:0x57c23c58B1D8C3292c15BEcF07c62C5c52457A42'),
        amount=FVal(deposit_amount := '0.016912211753057734'),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} osETH-waWETH into balancer-v3 gauge',
        counterparty=CPT_BALANCER_V3,
        address=string_to_evm_address('0x70A1c01902DAb7a45dcA1098Ca76A8314dd8aDbA'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:1/erc20:0x70A1c01902DAb7a45dcA1098Ca76A8314dd8aDbA'),
        amount=FVal(receive_amount := '0.016912211753057734'),
        location_label=user_address,
        notes=f'Receive {receive_amount} osETH-waWETH-gauge after depositing in balancer-v3 gauge',
        counterparty=CPT_BALANCER_V3,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_BALANCER_V3]])
@pytest.mark.parametrize('base_accounts', [['0x9EE4d24dB1104bDF818391efCB8CCBa8Ff206159']])
def test_gauge_withdrawal(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
        globaldb: 'GlobalDBHandler',
):
    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.BALANCER_V3_POOLS, str(base_inquirer.chain_id.value)),
            values=['0x7AB124EC4029316c2A42F713828ddf2a192B36db'],
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.BALANCER_V3_GAUGES, str(base_inquirer.chain_id.value)),
            values=['0x70DB188E5953f67a4B16979a2ceA26248b315401'],
        )
    tx_hash = deserialize_evm_tx_hash('0xd00e99e4e26704e5207b7b322424fb7ee625b850726f599ddd4100a86844ecfb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1756113395000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000713702598843'),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x70DB188E5953f67a4B16979a2ceA26248b315401'),
        amount=FVal(return_amount := '7.452356019321253694'),
        location_label=user_address,
        notes=f'Return {return_amount} Aave USDC-Aave GHO-gauge after withdrawing from balancer-v3 gauge',  # noqa: E501
        counterparty=CPT_BALANCER_V3,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x7AB124EC4029316c2A42F713828ddf2a192B36db'),
        amount=FVal(receive_amount := '7.452356019321253694'),
        location_label=user_address,
        notes=f'Withdraw {receive_amount} Aave USDC-Aave GHO from balancer-v3 gauge',
        counterparty=CPT_BALANCER_V3,
        address=string_to_evm_address('0x70DB188E5953f67a4B16979a2ceA26248b315401'),
    )]
