import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.base.modules.aerodrome.decoder import ROUTER
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    AERODROME_POOL_PROTOCOL,
    ChainID,
    EvmTokenKind,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

A_AERO = Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631')
WETH_BASE_ADDRESS = string_to_evm_address('0x4200000000000000000000000000000000000006')
WSTETH_POOL_ADDRESS = string_to_evm_address('0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8')
WSTETH_GAUGE_ADDRESS = string_to_evm_address('0xDf7c8F17Ab7D47702A4a4b6D951d2A4c90F99bf4')
VELO_V2_TOKEN = evm_address_to_identifier(
    address=string_to_evm_address('0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
    chain_id=ChainID.OPTIMISM,
    token_type=EvmTokenKind.ERC20,
)
VELO_V1_TOKEN = evm_address_to_identifier(
    address=string_to_evm_address('0x3c8B650257cFb5f272f799F5e2b4e65093a11a05'),
    chain_id=ChainID.OPTIMISM,
    token_type=EvmTokenKind.ERC20,
)
WSTETH_TOKEN = Asset(evm_address_to_identifier(
    address=string_to_evm_address('0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452'),
    chain_id=ChainID.BASE,
    token_type=EvmTokenKind.ERC20,
))
WETH_BASE = Asset(evm_address_to_identifier(
    address=WETH_BASE_ADDRESS,
    chain_id=ChainID.BASE,
    token_type=EvmTokenKind.ERC20,
))


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x514c4BA193c698100DdC998F17F24bDF59c7b6fB']])
def test_add_liquidity(base_transaction_decoder, base_accounts, load_global_caches):
    evmhash = deserialize_evm_tx_hash('0xb71a1339c700a110d61655387d422bb982252a3b55de7f571ced3b9f00d9beee')  # noqa: E501
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1706708913000)
    gas_amount, deposited_wsteth, deposited_weth, received_amount = '0.000071386738065118', '2.595314266724358628', '2.99450075155017638', '2.787544746858080184'  # noqa: E501
    pool_token = Asset('eip155:8453/erc20:0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8')
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
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
            product=EvmProduct.POOL,
            notes=f'Deposit {deposited_wsteth} wstETH in aerodrome pool {WSTETH_POOL_ADDRESS}',
        ), EvmEvent(
            tx_hash=evmhash,
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
            product=EvmProduct.POOL,
            notes=f'Deposit {deposited_weth} WETH in aerodrome pool {WSTETH_POOL_ADDRESS}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=17,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=pool_token,
            amount=FVal(received_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            product=EvmProduct.POOL,
            notes=f'Receive {received_amount} vAMM-WETH/wstETH after depositing in aerodrome pool {WSTETH_POOL_ADDRESS}',  # noqa: E501
        ),
    ]
    assert events == expected_events
    assert EvmToken(pool_token.identifier).protocol == AERODROME_POOL_PROTOCOL


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x514c4BA193c698100DdC998F17F24bDF59c7b6fB']])
def test_stake_lp_token_to_gauge(base_accounts, base_transaction_decoder, load_global_caches):
    evmhash = deserialize_evm_tx_hash('0x9a0cd1ab0b8e5dbf2718b1c87dad239f7f3a9ed8ff2e07643922b190f80ae898 ')  # noqa: E501
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    pool_token = Asset('eip155:8453/erc20:0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8')
    timestamp = TimestampMS(1706708947000)
    gas_amount, deposited_amount = '0.000038383457555312', '2.787544746858080184'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=pool_token,
            amount=ZERO,
            location_label=user_address,
            address=WSTETH_GAUGE_ADDRESS,
            notes=f'Revoke vAMM-WETH/wstETH spending approval of {user_address} by {WSTETH_GAUGE_ADDRESS}',  # noqa: E501
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=pool_token,
            amount=FVal(deposited_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=WSTETH_GAUGE_ADDRESS,
            notes=f'Deposit {deposited_amount} vAMM-WETH/wstETH into {WSTETH_GAUGE_ADDRESS} aerodrome gauge',  # noqa: E501
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events
    assert EvmToken(pool_token.identifier).protocol == AERODROME_POOL_PROTOCOL


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x61D90de4fa8cfbBD7A7650Ae01A39fD1B1863503']])
def test_remove_liquidity(base_accounts, base_transaction_decoder, load_global_caches):
    evmhash = deserialize_evm_tx_hash('0x847ed0b6bd3f1b030cc84eee74c2c238dd93e0b689c87d44bce7f3591173ef0d')  # noqa: E501
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1706789989000)
    gas_amount, lp_amount, aero_amount, usdbc_amount = '0.000088467182445046', '0.000053130643452706', '190.426331639958037231', '15.035115'  # noqa: E501
    pool_address = '0x2223F9FE624F69Da4D8256A7bCc9104FBA7F8f75'
    pool_token = Asset(evm_address_to_identifier(
        address=pool_address,
        chain_id=ChainID.BASE,
        token_type=EvmTokenKind.ERC20,
    ))
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_amount} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
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
            tx_hash=evmhash,
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
            product=EvmProduct.POOL,
            notes=f'Return {lp_amount} vAMM-AERO/USDbC',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_AERO,
            amount=FVal(aero_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool_address,
            product=EvmProduct.POOL,
            notes=f'Remove {aero_amount} AERO from aerodrome pool {pool_address}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=6,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:8453/erc20:0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA'),
            amount=FVal(usdbc_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=pool_address,
            product=EvmProduct.POOL,
            notes=f'Remove {usdbc_amount} USDbC from aerodrome pool {pool_address}',
        ),
    ]
    assert events == expected_events
