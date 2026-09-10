from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.base.modules.aerodrome.decoder import ROUTER, SLIPSTREAM_NFPM
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME
from rotkehlchen.chain.evm.decoding.zerox.constants import CPT_ZEROX
from rotkehlchen.chain.evm.types import (
    NodeName,
    WeightedNode,
    string_to_evm_address,
)
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    Location,
    SupportedBlockchain,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder

A_AERO = Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631')
WETH_BASE_ADDRESS = string_to_evm_address('0x4200000000000000000000000000000000000006')
WSTETH_POOL_ADDRESS = string_to_evm_address('0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8')
WSTETH_GAUGE_ADDRESS = string_to_evm_address('0xDf7c8F17Ab7D47702A4a4b6D951d2A4c90F99bf4')
WSTETH_TOKEN = Asset(evm_address_to_identifier(
    address=string_to_evm_address('0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452'),
    chain_id=ChainID.BASE,
    token_type=TokenKind.ERC20,
))
WETH_VVV_POOL_ADDRESS = string_to_evm_address('0x01784ef301D79e4B2DF3a21ad9a536d4cF09A5Ce')
A_VVV = Asset('eip155:8453/erc20:0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf')
A_USDC_BASE = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
WETH_BASE = Asset(evm_address_to_identifier(
    address=WETH_BASE_ADDRESS,
    chain_id=ChainID.BASE,
    token_type=TokenKind.ERC20,
))


def _add_aerodrome_pool(pool: ChecksumEvmAddress) -> None:
    """Add a aerodrome pool to the cache so decoding is properly triggered for related events."""
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.AERODROME_POOL_ADDRESS,),
            values=(pool,),
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ), active=True, weight=ONE,
    ),
)])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x514c4BA193c698100DdC998F17F24bDF59c7b6fB']])
def test_add_liquidity(
        base_transaction_decoder: BaseTransactionDecoder,
        base_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
        allow_base_routescan: None,
) -> None:
    _add_aerodrome_pool(pool := string_to_evm_address('0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8'))  # noqa: E501
    GlobalDBHandler.delete_asset_by_identifier(
        identifier=evm_address_to_identifier(address=pool, chain_id=ChainID.BASE),
    )
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xb71a1339c700a110d61655387d422bb982252a3b55de7f571ced3b9f00d9beee')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    gas_amount, deposited_wsteth, deposited_weth, received_amount = '0.000071386738065118', '2.595314266724358628', '2.99450075155017638', '2.787544746858080184'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1706708913000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=WSTETH_TOKEN,
            amount=ZERO,
            location_label=user_address,
            address=ROUTER,
            notes=f'Revoke wstETH spending approval of {user_address} by {ROUTER}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=15,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=WSTETH_TOKEN,
            amount=FVal(deposited_wsteth),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=WSTETH_POOL_ADDRESS,
            notes=f'Deposit {deposited_wsteth} wstETH in aerodrome pool {WSTETH_POOL_ADDRESS}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=WETH_BASE,
            amount=FVal(deposited_weth),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=WSTETH_POOL_ADDRESS,
            notes=f'Deposit {deposited_weth} WETH in aerodrome pool {WSTETH_POOL_ADDRESS}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=17,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=(pool_token := Asset(f'eip155:8453/erc20:{pool}')),
            amount=FVal(received_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            notes=f'Receive {received_amount} vAMM-WETH/wstETH after depositing in aerodrome pool {WSTETH_POOL_ADDRESS}',  # noqa: E501
        ),
    ]
    assert EvmToken(pool_token.identifier).protocol == CPT_AERODROME


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ), active=True, weight=ONE,
    ),
)])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x514c4BA193c698100DdC998F17F24bDF59c7b6fB']])
def test_stake_lp_token_to_gauge(base_accounts, base_transaction_decoder, load_global_caches):
    _add_aerodrome_pool(pool := string_to_evm_address('0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8'))  # noqa: E501
    GlobalDBHandler.delete_asset_by_identifier(
        identifier=evm_address_to_identifier(address=pool, chain_id=ChainID.BASE),
    )
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x9a0cd1ab0b8e5dbf2718b1c87dad239f7f3a9ed8ff2e07643922b190f80ae898 ')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    gas_amount, deposited_amount = '0.000038383457555312', '2.787544746858080184'
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1706708947000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=(pool_token := Asset(f'eip155:8453/erc20:{pool}')),
            amount=ZERO,
            location_label=user_address,
            address=WSTETH_GAUGE_ADDRESS,
            notes=f'Revoke vAMM-WETH/wstETH spending approval of {user_address} by {WSTETH_GAUGE_ADDRESS}',  # noqa: E501
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=pool_token,
            amount=FVal(deposited_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=WSTETH_GAUGE_ADDRESS,
            notes=f'Deposit {deposited_amount} vAMM-WETH/wstETH into {WSTETH_GAUGE_ADDRESS} aerodrome gauge',  # noqa: E501
        ),
    ]
    assert EvmToken(pool_token.identifier).protocol == CPT_AERODROME


@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ), active=True, weight=ONE,
    ),
)])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x82599463FA2ea651C1F19e36c33b74CC68e2B4b5']])
def test_add_liquidity_eth(
        base_transaction_decoder: BaseTransactionDecoder,
        base_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
) -> None:
    """Test addLiquidityETH where the native asset goes to the router, which wraps it and
    refunds the unused part. The refund is netted out of the deposit."""
    _add_aerodrome_pool(pool := WETH_VVV_POOL_ADDRESS)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xe043bc98bae987c0ff5f06d66846835f768e7451972b3ac2cfd3eeac98362939')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    gas_amount, deposited_vvv, deposited_eth, received_amount = '0.000001154313217566', '2334.952575943785024472', '22.547191100210812527', '226.898798596223864348'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1789014349000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_VVV,
            amount=FVal(deposited_vvv),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Deposit {deposited_vvv} VVV in aerodrome pool {pool}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(deposited_eth),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Deposit {deposited_eth} ETH in aerodrome pool {pool}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:8453/erc20:{pool}'),
            amount=FVal(received_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            notes=f'Receive {received_amount} vAMM-WETH/VVV after depositing in aerodrome pool {pool}',  # noqa: E501
        ),
    ]


@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ), active=True, weight=ONE,
    ),
)])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0xAA069d6199E0f4FCC84C6354E050D5F25f74c429']])
def test_add_liquidity_eth_via_smart_wallet(
        base_transaction_decoder: BaseTransactionDecoder,
        base_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
) -> None:
    """Test addLiquidityETH from an ERC-4337 smart wallet. The transaction is sent by the
    bundler to the EntryPoint, so the native asset only moves in internal transactions and
    there is no gas event since a paymaster covered the gas."""
    _add_aerodrome_pool(pool := WETH_VVV_POOL_ADDRESS)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x41ebb0a9160727b4b10f5609fab68718071c8d0bb8c6a93327fa4fd546eff189')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    deposited_vvv, deposited_eth, received_amount = '0.000444771800647726', '0.000004238948818732', '0.000042939943095562'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1788985713000)),
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_VVV,
            amount=FVal(deposited_vvv),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Deposit {deposited_vvv} VVV in aerodrome pool {pool}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(deposited_eth),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Deposit {deposited_eth} ETH in aerodrome pool {pool}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:8453/erc20:{pool}'),
            amount=FVal(received_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            notes=f'Receive {received_amount} vAMM-WETH/VVV after depositing in aerodrome pool {pool}',  # noqa: E501
        ),
    ]


@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ), active=True, weight=ONE,
    ),
)])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x14ac952E2D149ac7e0ad0E4b9E9ba939fa51A0D6']])
def test_remove_liquidity_via_smart_wallet(
        base_transaction_decoder: BaseTransactionDecoder,
        base_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
) -> None:
    """Test removing liquidity from an ERC-4337 smart wallet that prefunds its own gas.
    The prefund paid to the EntryPoint is decoded as the fee of the transaction."""
    _add_aerodrome_pool(pool := WETH_VVV_POOL_ADDRESS)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x2adaf0f6a91354dc03bff3174726b7439388055c91a4f99f3b2bd33c8b204748')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    fee_amount, returned_amount, withdrawn_weth, withdrawn_vvv = '0.000002390325488', '0.094163995310674867', '0.009543351044635924', '0.949851488856336753'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1788924533000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=(user_address := base_accounts[0]),
            address=(entrypoint := string_to_evm_address('0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789')),  # noqa: E501
            notes=f'Spend {fee_amount} ETH as ERC-4337 fee via {entrypoint}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=490,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=(pool_token := Asset(f'eip155:8453/erc20:{pool}')),
            amount=ZERO,
            location_label=user_address,
            address=ROUTER,
            notes=f'Revoke vAMM-WETH/VVV spending approval of {user_address} by {ROUTER}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=491,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=pool_token,
            amount=FVal(returned_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Return {returned_amount} vAMM-WETH/VVV',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=492,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=WETH_BASE,
            amount=FVal(withdrawn_weth),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Remove {withdrawn_weth} WETH from aerodrome pool {pool}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=493,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_VVV,
            amount=FVal(withdrawn_vvv),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Remove {withdrawn_vvv} VVV from aerodrome pool {pool}',
        ),
    ]


@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ), active=True, weight=ONE,
    ),
)])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0xC216BfA5dA000965E820845c32e6FD88DB275743']])
def test_slipstream_create_position(
        base_transaction_decoder: BaseTransactionDecoder,
        base_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
) -> None:
    """Test minting a concentrated liquidity (Slipstream) position via the position manager"""
    _add_aerodrome_pool(pool := string_to_evm_address('0xCCd9cC53b63662088c738B8BC06E9078Fb8D9ad4'))  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xfaae3656738212f80efded0ed48ea307dd73f52da9330a42e042af9d10293101')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    gas_amount, deposited_usdc, deposited_aero, position_id = '0.000002461446742837', '1104.765404', '15960.348043137794181943', '76587643'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1789052943000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC_BASE,
            amount=FVal(deposited_usdc),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Deposit {deposited_usdc} USDC to Aerodrome Slipstream LP {position_id}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_AERO,
            amount=FVal(deposited_aero),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Deposit {deposited_aero} AERO to Aerodrome Slipstream LP {position_id}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(f'eip155:8453/erc721:{SLIPSTREAM_NFPM}/{position_id}'),
            amount=ONE,
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            notes=f'Create Aerodrome Slipstream LP with id {position_id}',
        ),
    ]
    assert EvmToken(f'eip155:8453/erc721:{SLIPSTREAM_NFPM}/{position_id}').symbol == f'AERO-CL-POS-{position_id}'  # noqa: E501


@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ), active=True, weight=ONE,
    ),
)])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0xd48c780b3c48d7bB43cB69dC179D62726F798E50']])
def test_slipstream_exit_position(
        base_transaction_decoder: BaseTransactionDecoder,
        base_accounts: list[ChecksumEvmAddress],
        load_global_caches: list[str],
) -> None:
    """Test removing all liquidity of a Slipstream position, collecting it and burning
    the position NFT in one multicall"""
    _add_aerodrome_pool(pool := string_to_evm_address('0xe30d5BF485F7476AC15884a28ffb3C9cEA635DCB'))  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x5d1f4682f36859e8a891cef5a1def7a4d1024a9e4314e646a513c5e1ce8f3c81')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    gas_amount, withdrawn_avnt, withdrawn_usdc, position_id = '0.000001617384886138', '318.095368286092717677', '59.719805', '76587599'  # noqa: E501
    position_token = Asset(f'eip155:8453/erc721:{SLIPSTREAM_NFPM}/{position_id}')
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1789052913000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=(user_address := base_accounts[0]),
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=579,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=position_token,
            amount=ZERO,
            location_label=user_address,
            address=ZERO_ADDRESS,
            notes=f'Revoke AERO-CL-POS spending approval of {user_address} by {ZERO_ADDRESS}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=580,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=position_token,
            amount=ONE,
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            notes=f'Exit Aerodrome Slipstream LP with id {position_id}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=581,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:8453/erc20:0x696F9436B67233384889472Cd7cD58A6fB5DF4f1'),
            amount=FVal(withdrawn_avnt),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Remove {withdrawn_avnt} AVNT from Aerodrome Slipstream LP {position_id}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=582,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_USDC_BASE,
            amount=FVal(withdrawn_usdc),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool,
            notes=f'Remove {withdrawn_usdc} USDC from Aerodrome Slipstream LP {position_id}',
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(
        node_info=NodeName(
            name='base mainnet',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ), active=True, weight=ONE,
    ),
)])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x61D90de4fa8cfbBD7A7650Ae01A39fD1B1863503']])
def test_remove_liquidity(base_accounts, base_transaction_decoder, load_global_caches):
    _add_aerodrome_pool(pool_address := string_to_evm_address('0x2223F9FE624F69Da4D8256A7bCc9104FBA7F8f75'))  # noqa: E501
    GlobalDBHandler.delete_asset_by_identifier(
        identifier=evm_address_to_identifier(address=pool_address, chain_id=ChainID.BASE),
    )
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x847ed0b6bd3f1b030cc84eee74c2c238dd93e0b689c87d44bce7f3591173ef0d')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    gas_amount, lp_amount, aero_amount, usdbc_amount = '0.000088467182445046', '0.000053130643452706', '190.426331639958037231', '15.035115'  # noqa: E501
    pool_token = Asset(evm_address_to_identifier(
        address=pool_address,
        chain_id=ChainID.BASE,
        token_type=TokenKind.ERC20,
    ))
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1706789989000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=pool_token,
            amount=ZERO,
            location_label=user_address,
            address=ROUTER,
            notes=f'Revoke vAMM-AERO/USDbC spending approval of {user_address} by {ROUTER}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=pool_token,
            amount=FVal(lp_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool_address,
            notes=f'Return {lp_amount} vAMM-AERO/USDbC',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_AERO,
            amount=FVal(aero_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool_address,
            notes=f'Remove {aero_amount} AERO from aerodrome pool {pool_address}',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:8453/erc20:0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA'),
            amount=FVal(usdbc_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool_address,
            notes=f'Remove {usdbc_amount} USDbC from aerodrome pool {pool_address}',
        ),
    ]
    assert EvmToken(pool_token.identifier).protocol == CPT_AERODROME


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x123509D7e9e6576263B10100cf7EB016C64F73Ce']])
def test_unlock_aero(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0xb4166c9b0c6076197ab2c17bdef8a55b050880d7005d874152a9f23ce7626790')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1740994131000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000002416100602324'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=140,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.BURN,
            event_subtype=HistoryEventSubType.NFT,
            asset=Asset('eip155:8453/erc721:0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4/71294'),
            amount=ONE,
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            notes=f'Burn veNFT-71294 to unlock {(withdrawn_amt := "320.702116818286038014")} AERO from vote escrow',  # noqa: E501
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=141,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631'),
            amount=FVal(withdrawn_amt),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
            notes=f'Receive {withdrawn_amt} AERO from vote escrow after burning veNFT-71294',
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x1453Acb73B4c13BCE00496Ae00DdC7E4cF484C6c']])
def test_lock_aero(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0xe129665629d4df774f6dcad6170bddec73a9a45aed4fb3c5084337b85addce71')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741005765000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000002595608432929'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=309,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631'),
            amount=ZERO,
            location_label=user_address,
            address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
            notes=f'Revoke AERO spending approval of {user_address} by 0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4',  # noqa: E501
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=310,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631'),
            amount=FVal(lock_amount := ONE),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
            notes=f'Lock {lock_amount} AERO in vote escrow until 06/03/2025',
            extra_data={'token_id': 71991, 'lock_time': 1741219200},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=311,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.MINT,
            event_subtype=HistoryEventSubType.NFT,
            asset=Asset('eip155:8453/erc721:0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4/71991'),
            amount=ONE,
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            notes=f'Receive veNFT-71991 for locking {lock_amount} AERO in vote escrow',
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x0E9B063789909565CEdA1Fba162474405A151E66']])
def test_increase_locked_amount(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0xf92e665a95eb270e5362a890628198ac762f8d231754213b49360cce31ab2b86')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741022997000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000001849342754159'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=271,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631'),
            amount=FVal(approval_amount := '49071.435306527359498584'),
            location_label=user_address,
            address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
            notes=f'Set AERO spending approval of {user_address} by 0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4 to {approval_amount}',  # noqa: E501
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=272,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631'),
            amount=FVal(lock_amount := '1.774997251222472588'),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
            notes=f'Increase locked amount in veNFT-3334 by {lock_amount} AERO',
            extra_data={'token_id': 3334},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x7264A62ae2f2BbE5Fe003F29108afB3C3dA0Bc16']])
def test_increase_unlock_time(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0x6ac4bc89809ef7c5f0fd393fc6d162cb1c041f4d4ccc1ce3339f6c6e5614e753')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741016501000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000008164704817624'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2854,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:8453/erc721:0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4/16247'),
            amount=ZERO,
            location_label=user_address,
            address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
            extra_data={'token_id': 16247, 'lock_time': 1744243200},
            counterparty=CPT_AERODROME,
            notes='Increase unlock time to 10/04/2025 for AERO veNFT-16247',
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x051113f273942Ce806965F471665B6215B198A88']])
def test_vote(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0x9f4cbe2d67c38f08595fee37b73c65c870dd4784e8756fe41e8bda0b5321ae16')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741030415000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000005544830737074'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=278,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:8453/erc721:0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4/3251'),
            amount=ZERO,
            location_label=user_address,
            address=string_to_evm_address('0x16613524e02ad97eDfeF371bC883F2F5d6C480A5'),
            counterparty=CPT_AERODROME,
            notes='Cast 1805.00657141664811293 votes for pool 0xDbdfAc0F9268EF02c34Ed58c9Fab3517a98444dc',  # noqa: E501
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x7264A62ae2f2BbE5Fe003F29108afB3C3dA0Bc16']])
def test_swap(base_transaction_decoder, base_accounts, load_global_caches):
    """Test swapping fBOMB tokens on Aerodrome with decoded transaction events.

    fBOMB token has a 1% burn tax on transfers so it as appears a second transfer and isn't part of the swap.
    https://basescan.org/address/0x266c8f8cda4360506b8d32dc5c4102350a069acd#code#F1#L95
    """  # noqa: E501
    _add_aerodrome_pool(string_to_evm_address('0x4F9Dc2229f2357B27C22db56cB39582c854Ad6d5'))
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x260538961f3f2e17a43d26732f1105f739f9cf79622a3df8986c279c6d69a450')),  # noqa: E501
        load_global_caches=load_global_caches,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1731334851000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000002909074528395'),
        location_label=(user_address := base_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=425,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:8453/erc20:0x74ccbe53F77b08632ce0CB91D3A545bF6B8E0979'),
        amount=FVal(burn_amount := '47.190173008930536473'),
        location_label=user_address,
        address=ZERO_ADDRESS,
        notes=f'Send {burn_amount} fBOMB from {user_address} to {ZERO_ADDRESS}',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=426,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:8453/erc20:0x74ccbe53F77b08632ce0CB91D3A545bF6B8E0979'),
        amount=ZERO,
        location_label=user_address,
        address=string_to_evm_address('0x6Cb442acF35158D5eDa88fe602221b67B400Be3E'),
        notes=f'Revoke fBOMB spending approval of {user_address} by 0x6Cb442acF35158D5eDa88fe602221b67B400Be3E',  # noqa: E501
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=427,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:8453/erc20:0x74ccbe53F77b08632ce0CB91D3A545bF6B8E0979'),
        amount=FVal(spend_amount := '4671.827127884123110821'),
        location_label=user_address,
        counterparty=CPT_AERODROME,
        address=string_to_evm_address('0x4F9Dc2229f2357B27C22db56cB39582c854Ad6d5'),
        notes=f'Swap {spend_amount} fBOMB in aerodrome',
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=428,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:8453/erc20:0x4200000000000000000000000000000000000006'),
        amount=FVal(receive_amount := '0.070849955500013335'),
        location_label=user_address,
        counterparty=CPT_AERODROME,
        address=string_to_evm_address('0x4F9Dc2229f2357B27C22db56cB39582c854Ad6d5'),
        notes=f'Receive {receive_amount} WETH as the result of a swap in aerodrome',
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_swap_via_settler_router_on_base(
        base_transaction_decoder: BaseTransactionDecoder,
        base_accounts: list[ChecksumEvmAddress],
        allow_base_routescan: None,
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x3a02a2df62ec9d633e73771b48806c2fc8a47f64bf97058cc561e20c6fe037c4')),  # noqa: E501
    )
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1769195677000)),
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000002425034605404')),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:8453/erc20:0x18b6f6049A0af4Ed2BBe0090319174EeeF89f53a'),
        amount=(swap_amount := FVal('46.75')),
        location_label=user_address,
        notes=f'Swap {swap_amount} RUNNER via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=(settler_address := string_to_evm_address('0x49fb9C16B9b2a19452633573603c837673fD7E04')),  # noqa: E501
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=(received_amount := FVal('10.631562')),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=settler_address,
    )]
    assert events == expected_events
