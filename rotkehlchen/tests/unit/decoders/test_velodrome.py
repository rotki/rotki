import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.velodrome.decoder import ROUTER_V1, ROUTER_V2
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_OP, A_WETH_OPT
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    CacheType,
    ChainID,
    Location,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)

WETH_OP_POOL_ADDRESS = string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3')
WETH_OP_GAUGE_ADDRESS = string_to_evm_address('0xCC53CD0a8EC812D46F0E2c7CC5AADd869b6F0292')
WETH_OP_LP_TOKEN = evm_address_to_identifier(
    address=WETH_OP_POOL_ADDRESS,
    chain_id=ChainID.OPTIMISM,
    token_type=TokenKind.ERC20,
)
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


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_add_liquidity_v2(optimism_transaction_decoder, optimism_accounts, load_global_caches):
    """Check that adding liquidity to a velodrome v2 pool is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0xa1cf038ca08b51971314b4f8e006b455f2a82f113899e5eb7818ac1528605bfc')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1693573631000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000054658008447046'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000054658008447046 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=68,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_WETH_OPT,
            amount=FVal('0.005'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes=f'Deposit 0.005 WETH in velodrome pool {WETH_OP_POOL_ADDRESS}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=69,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_OP,
            amount=ZERO,
            location_label=user_address,
            address=ROUTER_V2,
            notes=f'Revoke OP spending approval of {user_address} by {ROUTER_V2}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=70,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_OP,
            amount=FVal('5.960043211306826894'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes=f'Deposit 5.960043211306826894 OP in velodrome pool {WETH_OP_POOL_ADDRESS}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=71,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(WETH_OP_LP_TOKEN),
            amount=FVal('0.172627291949741834'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ZERO_ADDRESS,
            notes=f'Receive 0.172627291949741834 vAMMV2-WETH/OP after depositing in velodrome pool {WETH_OP_POOL_ADDRESS}',  # noqa: E501
        ),
    ]
    assert events == expected_events
    assert EvmToken(WETH_OP_LP_TOKEN).protocol == CPT_VELODROME


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0xE1343a4b5e64d47B0c0f208d05Fb4B5973443818']])
def test_add_liquidity_v1(optimism_transaction_decoder, optimism_accounts, load_global_caches):
    """Check that adding liquidity to a velodrome v1 pool is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x779c2c762ed7ca5d2236ac548f9e9bdc723a8bc9d6d8feba9e3baea9456bbac9')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1685968046000)
    pool = string_to_evm_address('0x6fE665F19517Cd6076866dB0548177d0E628156a')
    lp_token_identifier = evm_address_to_identifier(pool, ChainID.OPTIMISM, TokenKind.ERC20)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00016522650722948'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.00016522650722948 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:10/erc20:0x3417E54A51924C225330f8770514aD5560B9098D'),
            amount=FVal('3.58533080911795905'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            notes=f'Deposit 3.58533080911795905 RED in velodrome pool {pool}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset(VELO_V1_TOKEN),
            amount=FVal('124.057046'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            notes=f'Deposit 124.057046 VELO in velodrome pool {pool}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(lp_token_identifier),
            amount=FVal('21.069827457300304618'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ZERO_ADDRESS,
            notes=f'Receive 21.069827457300304618 vAMM-RED/VELO after depositing in velodrome pool {pool}',  # noqa: E501
        ),
    ]
    assert events == expected_events
    assert EvmToken(lp_token_identifier).protocol == CPT_VELODROME


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_remove_liquidity_v2(optimism_transaction_decoder, optimism_accounts, load_global_caches):
    """Check that removing liquidity from a velodrome v2 pool is properly decoded."""
    get_or_create_evm_token(  # the token is needed for the approval event to be created
        userdb=optimism_transaction_decoder.evm_inquirer.database,
        evm_address=string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3'),
        chain_id=ChainID.OPTIMISM,
        protocol=CPT_VELODROME,
        symbol='vAMMV2-WETH/OP',
    )
    evmhash = deserialize_evm_tx_hash('0x81351bf9ca6d78bff92d2b714d68dd7c785bb70de0e250bc7bc6ab073736d1ce')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1694677251000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000024369543627752'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000024369543627752 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=33,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset(WETH_OP_LP_TOKEN),
            amount=ZERO,
            location_label=user_address,
            address=ROUTER_V2,
            notes=f'Revoke vAMMV2-WETH/OP spending approval of {user_address} by {ROUTER_V2}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=34,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset(WETH_OP_LP_TOKEN),
            amount=FVal('0.086313645974870917'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes='Return 0.086313645974870917 vAMMV2-WETH/OP',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_WETH_OPT,
            amount=FVal('0.002487103206849621'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes=f'Remove 0.002487103206849621 WETH from velodrome pool {WETH_OP_POOL_ADDRESS}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=37,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_OP,
            amount=FVal('2.995474411210852897'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes=f'Remove 2.995474411210852897 OP from velodrome pool {WETH_OP_POOL_ADDRESS}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0xe435BEbA6DEE3D6F99392ab9568777EB8165719d']])
def test_remove_liquidity_v1(optimism_transaction_decoder, optimism_accounts, load_global_caches):
    """Check that removing liquidity from a velodrome v1 pool is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x9b564c266aea871c14fbe120d060d1713f0ba524452906af3592360594b946f6')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1695202305000)
    pool = string_to_evm_address('0x47029bc8f5CBe3b464004E87eF9c9419a48018cd')
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000037049807135563'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000037049807135563 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=39,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset(evm_address_to_identifier(address=pool, chain_id=ChainID.OPTIMISM, token_type=TokenKind.ERC20)),  # noqa: E501
            amount=ZERO,
            location_label=user_address,
            notes=f'Revoke vAMM-OP/USDC spending approval of {user_address} by 0x9c12939390052919aF3155f41Bf4160Fd3666A6f',  # noqa: E501
            address=string_to_evm_address('0x9c12939390052919aF3155f41Bf4160Fd3666A6f'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=40,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:10/erc20:0x47029bc8f5CBe3b464004E87eF9c9419a48018cd'),
            amount=FVal('0.000174407012524167'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            notes='Return 0.000174407012524167 vAMM-OP/USDC',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=42,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_OP,
            amount=FVal('148.123832466418929782'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            notes=f'Remove 148.123832466418929782 OP from velodrome pool {pool}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=43,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal('205.545843'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            notes=f'Remove 205.545843 USDC.e from velodrome pool {pool}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_swap_eth_to_token_v2(optimism_accounts, optimism_transaction_decoder, load_global_caches):
    """Check that swapping eth to token in velodrome v2 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x8d65dc5a77aaceabac3b80fd28f8fa3cd45143748c2d31598706580f68d724da')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1693572877000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000044146364876824'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000044146364876824 ETH for gas',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.01'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ROUTER_V2,
            notes=f'Swap 0.01 ETH in {CPT_VELODROME}',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_OP,
            amount=FVal('11.895061655417592619'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ROUTER_V2,
            notes=f'Receive 11.895061655417592619 OP as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0xB1D34002ee676516787fd8CDb9C549a415F68aA8']])
def test_swap_eth_to_token_v1(optimism_accounts, optimism_transaction_decoder, load_global_caches):
    """Check that swapping eth to token in velodrome v1 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0xaa6b816c09863eab80f6184ab4112d7fea3a813c194dcebf08b6d4e13df22354')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1695194435000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000184626805145159'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000184626805145159 ETH for gas',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.0000857'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ROUTER_V1,
            notes=f'Swap 0.0000857 ETH in {CPT_VELODROME}',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:10/erc20:0x9485aca5bbBE1667AD97c7fE7C4531a624C8b1ED'),
            amount=FVal('0.130694520044655821'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ROUTER_V1,
            notes=f'Receive 0.130694520044655821 agEUR as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x2359497cc3F8F11A80d775715367d5CB3D0fD274']])
def test_swap_token_to_eth_v2(optimism_accounts, optimism_transaction_decoder, load_global_caches):
    """Check that swapping token to eth in velodrome v2 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x15c46045b9a4b03d15f0260f6518563f9a050fd693712330d9c05bedef833886')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1695108881000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000059095022720367'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000059095022720367 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=97,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_OP,
            amount=ZERO,
            location_label=user_address,
            address=ROUTER_V2,
            notes=f'Revoke OP spending approval of {user_address} by {ROUTER_V2}',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=98,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_OP,
            amount=FVal('91.173214418890299607'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes=f'Swap 91.173214418890299607 OP in {CPT_VELODROME}',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=99,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.0770899907450713'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes=f'Receive 0.0770899907450713 ETH as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0xeEf53a1f4eb3846f33C3E549D6FDF130fa4f8b27']])
def test_swap_token_to_eth_v1(optimism_accounts, optimism_transaction_decoder, load_global_caches):
    """Check that swapping token to eth in velodrome v1 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x10d52ec5cf06d1b5b48a346334c8f0e6ef83bd281c371d762d3c163e37f629d8')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1695155023000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000076204005061914'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000076204005061914 ETH for gas',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset(VELO_V1_TOKEN),
            amount=FVal('5165.602591359381942771'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=(address := string_to_evm_address('0xe8537b6FF1039CB9eD0B71713f697DDbaDBb717d')),  # velo_usdc_pool_address  # noqa: E501
            notes=f'Swap 5165.602591359381942771 VELO in {CPT_VELODROME}',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.181508840163183003'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=address,
            notes=f'Receive 0.181508840163183003 ETH as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x60583f22aDA7B1352bB2faF694b3eAaf942696DD']])
def test_swap_tokens_v2(optimism_accounts, optimism_transaction_decoder, load_global_caches):
    """Check that swapping tokens in velodrome v2 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x8c36e51bc4d3deec6a4c06a59179083adfd9caa8a5ad7e957e639d5792c9e139')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1697106165000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000034672969663309'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000034672969663309 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=92,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x8aE125E8653821E851F12A49F7765db9a9ce7384'),
            amount=ZERO,
            location_label=user_address,
            address=ROUTER_V2,
            notes=f'Revoke DOLA spending approval of {user_address} by {ROUTER_V2}',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=93,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:10/erc20:0x8aE125E8653821E851F12A49F7765db9a9ce7384'),
            amount=FVal('1177.178869111912387354'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=(address := string_to_evm_address('0x1f8b46abe1EAbF5A60CbBB5Fb2e4a6A46fA0b6e6')),  # noqa: E501
            notes=f'Swap 1177.178869111912387354 DOLA in {CPT_VELODROME}',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=94,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:10/erc20:0xb396b31599333739A97951b74652c117BE86eE1D'),
            amount=FVal('1122.945013439390360367'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=address,
            notes=f'Receive 1122.945013439390360367 DUSD as the result of a swap in {CPT_VELODROME}',  # noqa: E501
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0xC6d5Ad3C4002A1b48d87b83939698660516ae142']])
def test_swap_tokens_v1(optimism_accounts, optimism_transaction_decoder, load_global_caches):
    """Check that swapping tokens in velodrome v1 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x398538615367f778e9bb7fd95b3f96ee52e2192880b6f6331f91530ae4c829d9')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1695193815000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00003955388723844'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.00003955388723844 ETH for gas',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WETH_OPT,
            amount=FVal('0.056827266981849464'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0xcdd41009E74bD1AE4F7B2EeCF892e4bC718b9302'),  # weth_op_pool_address_v1  # noqa: E501
            notes=f'Swap 0.056827266981849464 WETH in {CPT_VELODROME}',
        ), EvmSwapEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_OP,
            amount=FVal('67.507104801871949085'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0xcdd41009E74bD1AE4F7B2EeCF892e4bC718b9302'),
            notes=f'Receive 67.507104801871949085 OP as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_stake_lp_token_to_gauge_v2(optimism_accounts, optimism_transaction_decoder, load_global_caches):  # noqa: E501
    """Check that depositing lp tokens to a velodrome v2 gauge is properly decoded."""
    get_or_create_evm_token(  # the token is needed for the approval event to be created
        userdb=optimism_transaction_decoder.evm_inquirer.database,
        evm_address=string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3'),
        chain_id=ChainID.OPTIMISM,
        protocol=CPT_VELODROME,
        symbol='vAMMV2-WETH/OP',
    )
    evmhash = deserialize_evm_tx_hash('0x1bfa588dc839b13205e80bbfd7b7748a4c599854a03b52bb5476d6edae2e95a9')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1694639877000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000019177994860846'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000019177994860846 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=19,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset(WETH_OP_LP_TOKEN),
            amount=ZERO,
            location_label=user_address,
            address=WETH_OP_GAUGE_ADDRESS,
            notes=f'Revoke vAMMV2-WETH/OP spending approval of {user_address} by {WETH_OP_GAUGE_ADDRESS}',  # noqa: E501
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=20,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(WETH_OP_LP_TOKEN),
            amount=FVal('0.172627291949741834'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_GAUGE_ADDRESS,
            notes=f'Deposit 0.172627291949741834 vAMMV2-WETH/OP into {WETH_OP_GAUGE_ADDRESS} velodrome gauge',  # noqa: E501,
        ),
    ]
    assert events == expected_events
    assert EvmToken(WETH_OP_LP_TOKEN).protocol == CPT_VELODROME


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_unstake_lp_token_to_gauge_v2(optimism_accounts, optimism_transaction_decoder, load_global_caches):  # noqa: E501
    """Check that withdrawing lp tokens from a velodrome v2 gauge is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0xe774e27053cab2c9cc293d6b1010d024a9a6af57fb6645ca52f0c5a26d117eeb')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1694676717000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00001849989800651'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.00001849989800651 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=85,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset(WETH_OP_LP_TOKEN),
            amount=FVal('0.172627291949741834'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_GAUGE_ADDRESS,
            notes=f'Withdraw 0.172627291949741834 vAMMV2-WETH/OP from {WETH_OP_GAUGE_ADDRESS} velodrome gauge',  # noqa: E501,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('load_global_caches', [[CPT_VELODROME]])
@pytest.mark.parametrize('optimism_accounts', [['0xf9AEb52bB4eF74E1987dd295E4Df326d41D0d0fF']])
def test_get_reward_from_gauge_v2(optimism_accounts, optimism_transaction_decoder, load_global_caches):  # noqa: E501
    """Check claiming rewards from a velodrome v2 gauge is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x9d0eae3c2d2cda853e77a2571a7c702507beb015c08b40406e03baa4b1dde505')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
        load_global_caches=load_global_caches,
    )
    timestamp = TimestampMS(1695116021000)
    gauge_address = string_to_evm_address('0x84195De69B8B131ddAa4Be4F75633fCD7F430b7c')
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000024794371949528'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burn 0.000024794371949528 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=35,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset(VELO_V2_TOKEN),
            amount=FVal('872.22115188616298484'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=gauge_address,
            notes=f'Receive 872.22115188616298484 VELO rewards from {gauge_address} velodrome gauge',  # noqa: E501,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x04b0f18b9b1FF987C5D5e134516f449aA9a2E004']])
def test_unlock_velo(optimism_accounts, optimism_transaction_decoder):
    user_address, evmhash = optimism_accounts[0], deserialize_evm_tx_hash('0x4389501a597f87f6f4c9042704f0040e5327251857d9a5043e4efff873787862')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741003701000)),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000000699973735595'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.BURN,
            event_subtype=HistoryEventSubType.NFT,
            asset=Asset('eip155:10/erc721:0xFAf8FD17D9840595845582fCB047DF13f006787d/27891'),
            amount=ONE,
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ZERO_ADDRESS,
            notes=f'Burn veNFT-27891 to unlock {(withdrawn_amt := "59.364651461725644131")} VELO from vote escrow',  # noqa: E501
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
            amount=FVal(withdrawn_amt),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0xFAf8FD17D9840595845582fCB047DF13f006787d'),
            notes=f'Receive {withdrawn_amt} VELO from vote escrow after burning veNFT-27891',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x6725BF01bF6Ca11FF3bd9Bd6701991DC4EBf24fa']])
def test_lock_velo(optimism_accounts, optimism_transaction_decoder):
    user_address, evmhash = optimism_accounts[0], deserialize_evm_tx_hash('0xd5e3d9c5142cf4dd948ad5582a9fa3392e21238a2ae698cb73bafd8c4e02101f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741011431000)),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000001167814501718'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=99,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
            amount=ZERO,
            location_label=user_address,
            address=string_to_evm_address('0xFAf8FD17D9840595845582fCB047DF13f006787d'),
            notes=f'Revoke VELO spending approval of {user_address} by 0xFAf8FD17D9840595845582fCB047DF13f006787d',  # noqa: E501
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=100,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
            amount=FVal(lock_amount := '110.000687505447225215'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0xFAf8FD17D9840595845582fCB047DF13f006787d'),
            notes=f'Lock {lock_amount} VELO in vote escrow until 01/03/2029',
            extra_data={'token_id': 30079, 'lock_time': 1867017600},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=101,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.MINT,
            event_subtype=HistoryEventSubType.NFT,
            asset=Asset('eip155:10/erc721:0xFAf8FD17D9840595845582fCB047DF13f006787d/30079'),
            amount=ONE,
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ZERO_ADDRESS,
            notes=f'Receive veNFT-30079 for locking {lock_amount} VELO in vote escrow',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x9844c3688dAaA98De18fBe52499A6B152236896b']])
def test_increase_locked_amount(optimism_accounts, optimism_transaction_decoder):
    user_address, evmhash = optimism_accounts[0], deserialize_evm_tx_hash('0x56a1e78a374981e5ebcfb605cd0835bee4b73a3221b908789fc917d11619ac9b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741006069000)),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.00000136036499356'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
            amount=FVal(approval_amount := '366860.961209203199646747'),
            location_label=user_address,
            address=string_to_evm_address('0xFAf8FD17D9840595845582fCB047DF13f006787d'),
            notes=f'Set VELO spending approval of {user_address} by 0xFAf8FD17D9840595845582fCB047DF13f006787d to {approval_amount}',  # noqa: E501
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
            amount=FVal(lock_amount := '18792.568241261307681904'),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0xFAf8FD17D9840595845582fCB047DF13f006787d'),
            notes=f'Increase locked amount in veNFT-20820 by {lock_amount} VELO',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x923CD36115817D59c51f33e0b5832d7b70ef2530']])
def test_increase_unlock_time(optimism_accounts, optimism_transaction_decoder):
    user_address, evmhash = optimism_accounts[0], deserialize_evm_tx_hash('0x513039d46a9b541e2cb7feb798060271a7b58e9e9ed80681c5d5b18f26fb8bfc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1740997763000)),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000000573869266137'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=19,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('eip155:10/erc721:0xFAf8FD17D9840595845582fCB047DF13f006787d/30064'),
            amount=ZERO,
            location_label=user_address,
            address=string_to_evm_address('0xFAf8FD17D9840595845582fCB047DF13f006787d'),
            extra_data={'token_id': 30064, 'lock_time': 1749686400},
            counterparty=CPT_VELODROME,
            notes='Increase unlock time to 12/06/2025 for VELO veNFT-30064',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x21814F7481f07BA48d2CA224dBA62Bc1f5B447D0']])
def test_claim_bribes(optimism_accounts, optimism_transaction_decoder, globaldb):
    user_address, evmhash = optimism_accounts[0], deserialize_evm_tx_hash('0xfc2df8e001236e5d4d2026f7d9943ef782d225af8676189f684347b1053776bc')  # noqa: E501
    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.VELODROME_GAUGE_BRIBE_ADDRESS,),
            values=[string_to_evm_address('0x9015Af1A94d0c9896DB9BF359b62dc9B114d5587')],
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.VELODROME_GAUGE_FEE_ADDRESS,),
            values=[string_to_evm_address('0x7A67D98C71Ca627547c191d8C32d1bcD4d36d823')],
        )

    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        tx_hash=evmhash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1741027977000)),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000001246550912592'),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes=f'Burn {gas_str} ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=143,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:10/erc20:0x747e42Eb0591547a0ab429B3627816208c734EA7'),
            amount=FVal(receive_amount_1 := '0.088944623183973897'),
            location_label=user_address,
            address=string_to_evm_address('0x9015Af1A94d0c9896DB9BF359b62dc9B114d5587'),
            counterparty=CPT_VELODROME,
            notes=f'Claim {receive_amount_1} T from velodrome as a bribe',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=145,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:10/erc20:0x4200000000000000000000000000000000000042'),
            amount=FVal(receive_amount_2 := '0.01121889586000788'),
            location_label=user_address,
            address=string_to_evm_address('0x9015Af1A94d0c9896DB9BF359b62dc9B114d5587'),
            counterparty=CPT_VELODROME,
            notes=f'Claim {receive_amount_2} OP from velodrome as a bribe',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=147,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:10/erc20:0x0a7B751FcDBBAA8BB988B9217ad5Fb5cfe7bf7A0'),
            amount=FVal(receive_amount_3 := '0.000002754529300195'),
            location_label=user_address,
            address=string_to_evm_address('0x9015Af1A94d0c9896DB9BF359b62dc9B114d5587'),
            counterparty=CPT_VELODROME,
            notes=f'Claim {receive_amount_3} ITP from velodrome as a bribe',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=149,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:10/erc20:0x6c84a8f1c29108F47a79964b5Fe888D4f4D0dE40'),
            amount=FVal(receive_amount_4 := '0.000000003860478715'),
            location_label=user_address,
            address=string_to_evm_address('0x7A67D98C71Ca627547c191d8C32d1bcD4d36d823'),
            counterparty=CPT_VELODROME,
            notes=f'Claim {receive_amount_4} tBTC from velodrome as a fee',
        ),
    ]
    assert events == expected_events
