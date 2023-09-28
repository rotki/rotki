import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.velodrome.constants import CPT_VELODROME
from rotkehlchen.chain.optimism.modules.velodrome.decoder import ROUTER_V1, ROUTER_V2
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_OP, A_WETH_OPT
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    VELODROME_POOL_PROTOCOL,
    ChainID,
    EvmTokenKind,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

WETH_OP_POOL_ADDRESS = string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3')
WETH_OP_GAUGE_ADDRESS = string_to_evm_address('0xCC53CD0a8EC812D46F0E2c7CC5AADd869b6F0292')
WETH_OP_LP_TOKEN = evm_address_to_identifier(
    address=WETH_OP_POOL_ADDRESS,
    chain_id=ChainID.OPTIMISM,
    token_type=EvmTokenKind.ERC20,
)
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


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_add_liquidity_v2(optimism_transaction_decoder, optimism_accounts):
    """Check that adding liquidity to a velodrome v2 pool is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0xa1cf038ca08b51971314b4f8e006b455f2a82f113899e5eb7818ac1528605bfc')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000054658008447046')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000054658008447046 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=68,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_WETH_OPT,
            balance=Balance(FVal('0.005')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            product=EvmProduct.POOL,
            notes=f'Deposit 0.005 WETH in velodrome pool {WETH_OP_POOL_ADDRESS}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=69,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_OP,
            balance=Balance(ZERO),
            location_label=user_address,
            address=ROUTER_V2,
            notes=f'Revoke OP spending approval of {user_address} by {ROUTER_V2}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=70,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_OP,
            balance=Balance(FVal('5.960043211306826894')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            product=EvmProduct.POOL,
            notes=f'Deposit 5.960043211306826894 OP in velodrome pool {WETH_OP_POOL_ADDRESS}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=71,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(WETH_OP_LP_TOKEN),
            balance=Balance(FVal('0.172627291949741834')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ZERO_ADDRESS,
            product=EvmProduct.POOL,
            notes=f'Receive 0.172627291949741834 vAMMV2-WETH/OP after depositing in velodrome pool {WETH_OP_POOL_ADDRESS}',  # noqa: E501
        ),
    ]
    assert events == expected_events
    assert EvmToken(WETH_OP_LP_TOKEN).protocol == VELODROME_POOL_PROTOCOL


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0xE1343a4b5e64d47B0c0f208d05Fb4B5973443818']])
def test_add_liquidity_v1(optimism_transaction_decoder, optimism_accounts):
    """Check that adding liquidity to a velodrome v1 pool is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x779c2c762ed7ca5d2236ac548f9e9bdc723a8bc9d6d8feba9e3baea9456bbac9')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
    )
    timestamp = TimestampMS(1685968046000)
    pool = string_to_evm_address('0x6fE665F19517Cd6076866dB0548177d0E628156a')
    lp_token_identifier = evm_address_to_identifier(pool, ChainID.OPTIMISM, EvmTokenKind.ERC20)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal('0.00016522650722948')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.00016522650722948 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:10/erc20:0x3417E54A51924C225330f8770514aD5560B9098D'),
            balance=Balance(FVal('3.58533080911795905')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            product=EvmProduct.POOL,
            notes=f'Deposit 3.58533080911795905 RED in velodrome pool {pool}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(VELO_V1_TOKEN),
            balance=Balance(FVal('124.057046')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            product=EvmProduct.POOL,
            notes=f'Deposit 124.057046 VELO in velodrome pool {pool}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset(lp_token_identifier),
            balance=Balance(FVal('21.069827457300304618')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ZERO_ADDRESS,
            product=EvmProduct.POOL,
            notes=f'Receive 21.069827457300304618 vAMM-RED/VELO after depositing in velodrome pool {pool}',  # noqa: E501
        ),
    ]
    assert events == expected_events
    assert EvmToken(lp_token_identifier).protocol == VELODROME_POOL_PROTOCOL


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_remove_liquidity_v2(optimism_transaction_decoder, optimism_accounts):
    """Check that removing liquidity from a velodrome v2 pool is properly decoded."""
    get_or_create_evm_token(  # the token is needed for the approval event to be created
        userdb=optimism_transaction_decoder.evm_inquirer.database,
        evm_address=string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3'),
        chain_id=ChainID.OPTIMISM,
        protocol=VELODROME_POOL_PROTOCOL,
        symbol='vAMMV2-WETH/OP',
    )
    evmhash = deserialize_evm_tx_hash('0x81351bf9ca6d78bff92d2b714d68dd7c785bb70de0e250bc7bc6ab073736d1ce')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000024369543627752')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000024369543627752 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=33,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset(WETH_OP_LP_TOKEN),
            balance=Balance(ZERO),
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
            balance=Balance(FVal('0.086313645974870917')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            product=EvmProduct.POOL,
            notes='Return 0.086313645974870917 vAMMV2-WETH/OP',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_WETH_OPT,
            balance=Balance(FVal('0.002487103206849621')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            product=EvmProduct.POOL,
            notes=f'Remove 0.002487103206849621 WETH from velodrome pool {WETH_OP_POOL_ADDRESS}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=37,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_OP,
            balance=Balance(FVal('2.995474411210852897')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            product=EvmProduct.POOL,
            notes=f'Remove 2.995474411210852897 OP from velodrome pool {WETH_OP_POOL_ADDRESS}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0xe435BEbA6DEE3D6F99392ab9568777EB8165719d']])
def test_remove_liquidity_v1(optimism_transaction_decoder, optimism_accounts):
    """Check that removing liquidity from a velodrome v1 pool is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x9b564c266aea871c14fbe120d060d1713f0ba524452906af3592360594b946f6')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000037049807135563')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000037049807135563 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=40,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:10/erc20:0x47029bc8f5CBe3b464004E87eF9c9419a48018cd'),
            balance=Balance(FVal('0.000174407012524167')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            product=EvmProduct.POOL,
            notes='Return 0.000174407012524167 vAMM-OP/USDC',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=42,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_OP,
            balance=Balance(FVal('148.123832466418929782')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            product=EvmProduct.POOL,
            notes=f'Remove 148.123832466418929782 OP from velodrome pool {pool}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=43,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            balance=Balance(FVal('205.545843')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=pool,
            product=EvmProduct.POOL,
            notes=f'Remove 205.545843 USDC from velodrome pool {pool}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_swap_eth_to_token_v2(optimism_accounts, optimism_transaction_decoder):
    """Check that swapping eth to token in velodrome v2 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x8d65dc5a77aaceabac3b80fd28f8fa3cd45143748c2d31598706580f68d724da')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000044146364876824')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000044146364876824 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(FVal('0.01')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ROUTER_V2,
            notes=f'Swap 0.01 ETH in {CPT_VELODROME}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=83,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_OP,
            balance=Balance(FVal('11.895061655417592619')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0x2fE304b407c7fAb2a3c10962F14dB751468a4f5b'),  # op_frxeth_pool_address  # noqa: E501
            notes=f'Receive 11.895061655417592619 OP as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0xB1D34002ee676516787fd8CDb9C549a415F68aA8']])
def test_swap_eth_to_token_v1(optimism_accounts, optimism_transaction_decoder):
    """Check that swapping eth to token in velodrome v1 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0xaa6b816c09863eab80f6184ab4112d7fea3a813c194dcebf08b6d4e13df22354')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000184626805145159')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000184626805145159 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(FVal('0.0000857')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ROUTER_V1,
            notes=f'Swap 0.0000857 ETH in {CPT_VELODROME}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:10/erc20:0x9485aca5bbBE1667AD97c7fE7C4531a624C8b1ED'),
            balance=Balance(FVal('0.130694520044655821')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0x7866C6072B09539fC0FDE82963846b80203d7beb'),
            notes=f'Receive 0.130694520044655821 agEUR as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x2359497cc3F8F11A80d775715367d5CB3D0fD274']])
def test_swap_token_to_eth_v2(optimism_accounts, optimism_transaction_decoder):
    """Check that swapping token to eth in velodrome v2 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x15c46045b9a4b03d15f0260f6518563f9a050fd693712330d9c05bedef833886')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000059095022720367')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000059095022720367 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=97,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_OP,
            balance=Balance(ZERO),
            location_label=user_address,
            address=ROUTER_V2,
            notes=f'Revoke OP spending approval of {user_address} by {ROUTER_V2}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=98,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_OP,
            balance=Balance(FVal('91.173214418890299607')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes=f'Swap 91.173214418890299607 OP in {CPT_VELODROME}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=99,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(FVal('0.0770899907450713')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ROUTER_V2,
            notes=f'Receive 0.0770899907450713 ETH as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0xeEf53a1f4eb3846f33C3E549D6FDF130fa4f8b27']])
def test_swap_token_to_eth_v1(optimism_accounts, optimism_transaction_decoder):
    """Check that swapping token to eth in velodrome v1 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x10d52ec5cf06d1b5b48a346334c8f0e6ef83bd281c371d762d3c163e37f629d8')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000076204005061914')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000076204005061914 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset(VELO_V1_TOKEN),
            balance=Balance(FVal('5165.602591359381942771')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0xe8537b6FF1039CB9eD0B71713f697DDbaDBb717d'),  # velo_usdc_pool_address  # noqa: E501
            notes=f'Swap 5165.602591359381942771 VELO in {CPT_VELODROME}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(FVal('0.181508840163183003')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=ROUTER_V1,
            notes=f'Receive 0.181508840163183003 ETH as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_swap_tokens_v2(optimism_accounts, optimism_transaction_decoder):
    """Check that swapping tokens in velodrome v2 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x0cca192bce4a72059c255e5000a0ba1e716f1059d2a388167165e41d9269aa24')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
    )
    timestamp = TimestampMS(1694638139000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal('0.000051606343716023')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000051606343716023 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=96,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_OP,
            balance=Balance(ZERO),
            location_label=user_address,
            address=ROUTER_V2,
            notes=f'Revoke OP spending approval of {user_address} by {ROUTER_V2}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=97,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_OP,
            balance=Balance(FVal('1.5')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_POOL_ADDRESS,
            notes=f'Swap 1.5 OP in {CPT_VELODROME}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=109,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset(VELO_V2_TOKEN),
            balance=Balance(FVal('50.633275729041219862')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0x0af32614EEa68B8D2232B9592FbdB6512ab6DA73'),
            notes=f'Receive 50.633275729041219862 VELO as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0xC6d5Ad3C4002A1b48d87b83939698660516ae142']])
def test_swap_tokens_v1(optimism_accounts, optimism_transaction_decoder):
    """Check that swapping tokens in velodrome v1 is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x398538615367f778e9bb7fd95b3f96ee52e2192880b6f6331f91530ae4c829d9')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.00003955388723844')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.00003955388723844 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WETH_OPT,
            balance=Balance(FVal('0.056827266981849464')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0xcdd41009E74bD1AE4F7B2EeCF892e4bC718b9302'),  # weth_op_pool_address_v1  # noqa: E501
            notes=f'Swap 0.056827266981849464 WETH in {CPT_VELODROME}',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_OP,
            balance=Balance(FVal('67.507104801871949085')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=string_to_evm_address('0xcdd41009E74bD1AE4F7B2EeCF892e4bC718b9302'),
            notes=f'Receive 67.507104801871949085 OP as the result of a swap in {CPT_VELODROME}',
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_stake_lp_token_to_gauge_v2(optimism_accounts, optimism_transaction_decoder):
    """Check that depositing lp tokens to a velodrome v2 gauge is properly decoded."""
    get_or_create_evm_token(  # the token is needed for the approval event to be created
        userdb=optimism_transaction_decoder.evm_inquirer.database,
        evm_address=string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3'),
        chain_id=ChainID.OPTIMISM,
        protocol=VELODROME_POOL_PROTOCOL,
        symbol='vAMMV2-WETH/OP',
    )
    evmhash = deserialize_evm_tx_hash('0x1bfa588dc839b13205e80bbfd7b7748a4c599854a03b52bb5476d6edae2e95a9')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000019177994860846')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000019177994860846 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=19,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset(WETH_OP_LP_TOKEN),
            balance=Balance(ZERO),
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
            balance=Balance(FVal('0.172627291949741834')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_GAUGE_ADDRESS,
            notes=f'Deposit 0.172627291949741834 vAMMV2-WETH/OP into {WETH_OP_GAUGE_ADDRESS} velodrome gauge',  # noqa: E501
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events
    assert EvmToken(WETH_OP_LP_TOKEN).protocol == VELODROME_POOL_PROTOCOL


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_unstake_lp_token_to_gauge_v2(optimism_accounts, optimism_transaction_decoder):
    """Check that withdrawing lp tokens from a velodrome v2 gauge is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0xe774e27053cab2c9cc293d6b1010d024a9a6af57fb6645ca52f0c5a26d117eeb')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.00001849989800651')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.00001849989800651 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=85,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset(WETH_OP_LP_TOKEN),
            balance=Balance(FVal('0.172627291949741834')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=WETH_OP_GAUGE_ADDRESS,
            notes=f'Withdraw 0.172627291949741834 vAMMV2-WETH/OP from {WETH_OP_GAUGE_ADDRESS} velodrome gauge',  # noqa: E501
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0xf9AEb52bB4eF74E1987dd295E4Df326d41D0d0fF']])
def test_get_reward_from_gauge_v2(optimism_accounts, optimism_transaction_decoder):
    """Check claiming rewards from a velodrome v2 gauge is properly decoded."""
    evmhash = deserialize_evm_tx_hash('0x9d0eae3c2d2cda853e77a2571a7c702507beb015c08b40406e03baa4b1dde505')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_transaction_decoder.evm_inquirer,
        database=optimism_transaction_decoder.database,
        tx_hash=evmhash,
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
            balance=Balance(FVal('0.000024794371949528')),
            location_label=user_address,
            counterparty=CPT_GAS,
            notes='Burned 0.000024794371949528 ETH for gas',
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=35,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset(VELO_V2_TOKEN),
            balance=Balance(FVal('872.22115188616298484')),
            location_label=user_address,
            counterparty=CPT_VELODROME,
            address=gauge_address,
            notes=f'Receive 872.22115188616298484 VELO rewards from {gauge_address} velodrome gauge',  # noqa: E501
            product=EvmProduct.GAUGE,
        ),
    ]
    assert events == expected_events
