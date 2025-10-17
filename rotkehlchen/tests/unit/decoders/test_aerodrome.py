import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.base.modules.aerodrome.decoder import ROUTER
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    Location,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

A_AERO = Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631')
WETH_BASE_ADDRESS = string_to_evm_address('0x4200000000000000000000000000000000000006')
WSTETH_POOL_ADDRESS = string_to_evm_address('0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8')
WSTETH_GAUGE_ADDRESS = string_to_evm_address('0xDf7c8F17Ab7D47702A4a4b6D951d2A4c90F99bf4')
VELO_V2_TOKEN = evm_address_to_identifier(
    address=string_to_evm_address('0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
    chain_id=ChainID.OPTIMISM,
    token_type=TokenKind.ERC20,
)
VELO_V1_TOKEN = evm_address_to_identifier(
    address=string_to_evm_address('0x3c8B650257cFb5f272f799F5e2b4e65093a11a05'),
    chain_id=ChainID.OPTIMISM,
    token_type=TokenKind.ERC20,
)
WSTETH_TOKEN = Asset(evm_address_to_identifier(
    address=string_to_evm_address('0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452'),
    chain_id=ChainID.BASE,
    token_type=TokenKind.ERC20,
))
WETH_BASE = Asset(evm_address_to_identifier(
    address=WETH_BASE_ADDRESS,
    chain_id=ChainID.BASE,
    token_type=TokenKind.ERC20,
))


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x514c4BA193c698100DdC998F17F24bDF59c7b6fB']])
def test_add_liquidity(base_transaction_decoder, base_accounts, load_global_caches):
    tx_hash = deserialize_evm_tx_hash('0xb71a1339c700a110d61655387d422bb982252a3b55de7f571ced3b9f00d9beee')  # noqa: E501
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1706708913000)
    gas_amount, deposited_wsteth, deposited_weth, received_amount = '0.000071386738065118', '2.595314266724358628', '2.99450075155017638', '2.787544746858080184'  # noqa: E501
    pool_token = Asset('eip155:8453/erc20:0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
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
            asset=pool_token,
            amount=FVal(received_amount),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=ZERO_ADDRESS,
            notes=f'Receive {received_amount} vAMM-WETH/wstETH after depositing in aerodrome pool {WSTETH_POOL_ADDRESS}',  # noqa: E501
        ),
    ]
    assert events == expected_events
    assert EvmToken(pool_token.identifier).protocol == CPT_AERODROME


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x514c4BA193c698100DdC998F17F24bDF59c7b6fB']])
def test_stake_lp_token_to_gauge(base_accounts, base_transaction_decoder, load_global_caches):
    tx_hash = deserialize_evm_tx_hash('0x9a0cd1ab0b8e5dbf2718b1c87dad239f7f3a9ed8ff2e07643922b190f80ae898 ')  # noqa: E501
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    pool_token = Asset('eip155:8453/erc20:0xA6385c73961dd9C58db2EF0c4EB98cE4B60651e8')
    timestamp = TimestampMS(1706708947000)
    gas_amount, deposited_amount = '0.000038383457555312', '2.787544746858080184'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
            tx_ref=tx_hash,
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
        ),
    ]
    assert events == expected_events
    assert EvmToken(pool_token.identifier).protocol == CPT_AERODROME


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x61D90de4fa8cfbBD7A7650Ae01A39fD1B1863503']])
def test_remove_liquidity(base_accounts, base_transaction_decoder, load_global_caches):
    tx_hash = deserialize_evm_tx_hash('0x847ed0b6bd3f1b030cc84eee74c2c238dd93e0b689c87d44bce7f3591173ef0d')  # noqa: E501
    user_address = base_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1706789989000)
    gas_amount, lp_amount, aero_amount, usdbc_amount = '0.000088467182445046', '0.000053130643452706', '190.426331639958037231', '15.035115'  # noqa: E501
    pool_address = '0x2223F9FE624F69Da4D8256A7bCc9104FBA7F8f75'
    pool_token = Asset(evm_address_to_identifier(
        address=pool_address,
        chain_id=ChainID.BASE,
        token_type=TokenKind.ERC20,
    ))
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
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
            notes=f'Remove {aero_amount} AERO from aerodrome pool {pool_address}',
        ), EvmEvent(
            tx_ref=tx_hash,
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
            notes=f'Remove {usdbc_amount} USDbC from aerodrome pool {pool_address}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0x123509D7e9e6576263B10100cf7EB016C64F73Ce']])
def test_unlock_aero(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0xb4166c9b0c6076197ab2c17bdef8a55b050880d7005d874152a9f23ce7626790')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    expected_events = [
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
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631'),
            amount=FVal(withdrawn_amt),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
            notes=f'Receive {withdrawn_amt} AERO from vote escrow after burning veNFT-71294',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0x1453Acb73B4c13BCE00496Ae00DdC7E4cF484C6c']])
def test_lock_aero(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0xe129665629d4df774f6dcad6170bddec73a9a45aed4fb3c5084337b85addce71')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    expected_events = [
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
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
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
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0x0E9B063789909565CEdA1Fba162474405A151E66']])
def test_increase_locked_amount(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0xf92e665a95eb270e5362a890628198ac762f8d231754213b49360cce31ab2b86')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    expected_events = [
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
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631'),
            amount=FVal(lock_amount := '1.774997251222472588'),
            location_label=user_address,
            counterparty=CPT_AERODROME,
            address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
            notes=f'Increase locked amount in veNFT-3334 by {lock_amount} AERO',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0x7264A62ae2f2BbE5Fe003F29108afB3C3dA0Bc16']])
def test_increase_unlock_time(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0x6ac4bc89809ef7c5f0fd393fc6d162cb1c041f4d4ccc1ce3339f6c6e5614e753')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    expected_events = [
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
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0x051113f273942Ce806965F471665B6215B198A88']])
def test_vote(base_accounts, base_transaction_decoder):
    user_address, tx_hash = base_accounts[0], deserialize_evm_tx_hash('0x9f4cbe2d67c38f08595fee37b73c65c870dd4784e8756fe41e8bda0b5321ae16')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
    )
    expected_events = [
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
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_AERODROME]])
@pytest.mark.parametrize('base_accounts', [['0x7264A62ae2f2BbE5Fe003F29108afB3C3dA0Bc16']])
def test_swap(base_transaction_decoder, base_accounts, load_global_caches):
    """Test swapping fBOMB tokens on Aerodrome with decoded transaction events.

    fBOMB token has a 1% burn tax on transfers so it as appears a second transfer and isn't part of the swap.
    https://basescan.org/address/0x266c8f8cda4360506b8d32dc5c4102350a069acd#code#F1#L95
    """  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x260538961f3f2e17a43d26732f1105f739f9cf79622a3df8986c279c6d69a450')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_transaction_decoder.evm_inquirer,
        tx_hash=tx_hash,
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
