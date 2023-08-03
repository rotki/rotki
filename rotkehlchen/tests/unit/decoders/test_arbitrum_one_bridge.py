import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.arbitrum_one.modules.arbitrum_one_bridge.decoder import BRIDGE_ADDRESS
from rotkehlchen.chain.ethereum.modules.arbitrum_one_bridge.decoder import (
    BRIDGE_ADDRESS_MAINNET,
    L1_GATEWAY_ROUTER,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x4e7DF0FDa2d203f5DFbaa34b9FB64DDe5133196e']])
def test_deposit_eth_from_ethereum_to_arbitrum_one(database, ethereum_inquirer, ethereum_accounts):
    """Data is taken from
    https://etherscan.io/tx/0xbe5b747193c68a7d1844053996e1a27a1279a4f1743f4b9a00e5a14152ee8641
    """
    evmhash = deserialize_evm_tx_hash('0xbe5b747193c68a7d1844053996e1a27a1279a4f1743f4b9a00e5a14152ee8641')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1690789463000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001207084037700187')),
            location_label=user_address,
            notes='Burned 0.001207084037700187 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1690789463000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.008374552015335015')),
            location_label=user_address,
            notes=f'Bridge 0.008374552015335015 ETH from ethereum address {user_address} to arbitrum_one address {user_address} via arbitrum_one bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f'),  # DELAYED_INBOX_ADDRESS  # noqa: E501
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x4e7DF0FDa2d203f5DFbaa34b9FB64DDe5133196e']])
def test_receive_eth_on_arbitrum_one(database, arbitrum_one_inquirer, arbitrum_one_accounts):
    """Data is taken from
    https://arbiscan.io/tx/0x30505174f2f82a6513f21eb5177e59935a6da95d057e4c1972e65da90ea1c547
    """
    evmhash = deserialize_evm_tx_hash('0x30505174f2f82a6513f21eb5177e59935a6da95d057e4c1972e65da90ea1c547')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1690789735000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.008374552015335015')),
            location_label=user_address,
            notes=f'Bridge 0.008374552015335015 ETH from ethereum address {user_address} to arbitrum_one address {user_address} via arbitrum_one bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0x5F8EF0FdA2d203f5DfbAa34B9fB64DDe51332A7f'),
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x5EA45c8E36704d7F4053Bb0e23cDd96E4d8b80F7']])
def test_withdraw_eth_from_arbitrum_one_to_ethereum(database, arbitrum_one_inquirer, arbitrum_one_accounts):  # noqa: E501
    """Data is taken from
    https://arbiscan.io/tx/0xdb8e29f27a7b7b416f168e8135347703268a142b6776503e26419dbfc43bcabf
    """
    evmhash = deserialize_evm_tx_hash('0xdb8e29f27a7b7b416f168e8135347703268a142b6776503e26419dbfc43bcabf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1688139924000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0000646535')),
            location_label=user_address,
            notes='Burned 0.0000646535 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1688139924000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('98.34759123048141')),
            location_label=user_address,
            notes=f'Bridge 98.34759123048141 ETH from arbitrum_one address {user_address} to ethereum address {user_address} via arbitrum_one bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address(BRIDGE_ADDRESS),
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x5EA45c8E36704d7F4053Bb0e23cDd96E4d8b80F7']])
def test_receive_eth_on_ethereum(database, ethereum_inquirer, ethereum_accounts):
    """Data is taken from
    https://etherscan.io/tx/0x2698916bd8d658ce6cfe032e5526fa345b3656a849870e72b1e853d22efdd7ac
    """
    evmhash = deserialize_evm_tx_hash('0x2698916bd8d658ce6cfe032e5526fa345b3656a849870e72b1e853d22efdd7ac')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1688931083000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001688346842833805')),
            location_label=user_address,
            notes='Burned 0.001688346842833805 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1688931083000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('98.34759123048141')),
            location_label=user_address,
            notes=f'Bridge 98.34759123048141 ETH from arbitrum_one address {user_address} to ethereum address {user_address} via arbitrum_one bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address(BRIDGE_ADDRESS_MAINNET),
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xBEEC919d69FB1a5195964ee90959C413CDbACe28']])
def test_deposit_erc20_from_ethereum_to_arbitrum_one(database, ethereum_inquirer, ethereum_accounts):  # noqa: E501
    """Data is taken from
    https://etherscan.io/tx/0x2eb4686e6b9857f02c1c8a035dc1ac7dcaf160fd52248b56a76de7774482390d
    """
    evmhash = deserialize_evm_tx_hash('0x2eb4686e6b9857f02c1c8a035dc1ac7dcaf160fd52248b56a76de7774482390d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1690864931000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.002442413931855385')),
            location_label=user_address,
            notes='Burned 0.002442413931855385 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=TimestampMS(1690864931000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('ETH'),
            balance=Balance(amount=FVal('0.000225651577545344')),
            location_label=user_address,
            notes=f'Send 0.000225651577545344 ETH to {L1_GATEWAY_ROUTER} for bridging erc20 tokens to arbitrum_one',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address(L1_GATEWAY_ROUTER),
        ),
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=208,
            timestamp=TimestampMS(1690864931000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            balance=Balance(amount=FVal('25000')),
            location_label=user_address,
            notes=f'Bridge 25000 DAI from ethereum address {user_address} to arbitrum_one address {user_address} via arbitrum_one bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0xA10c7CE4b876998858b1a9E12b10092229539400'),
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_receive_erc20_on_arbitrum_one(database, arbitrum_one_inquirer, arbitrum_one_accounts):
    """Data is taken from
    https://arbiscan.io/tx/0x80e6c0835c3ead90dde524c3dfe49a067fd5b5cda93d5a223707e686d910d8a2
    """
    evmhash = deserialize_evm_tx_hash('0x80e6c0835c3ead90dde524c3dfe49a067fd5b5cda93d5a223707e686d910d8a2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1691230958000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'),
            balance=Balance(amount=FVal('0.00032674')),
            location_label=user_address,
            notes=f'Bridge 0.00032674 WBTC from ethereum address {user_address} to arbitrum_one address {user_address} via arbitrum_one bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xbD91C9DF3C30F0e43B19b1dd05888CF9b647b781']])
def test_withdraw_erc20_from_arbitrum_one_to_ethereum(database, arbitrum_one_inquirer, arbitrum_one_accounts):  # noqa: E501
    """Data is taken from
    https://arbiscan.io/tx/0x90ca8a767118c27aa4f6370bc06d9f952ab88a9219431f68d8e2d33b4a15b395
    """
    evmhash = deserialize_evm_tx_hash('0x90ca8a767118c27aa4f6370bc06d9f952ab88a9219431f68d8e2d33b4a15b395')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1689533783000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0000597064')),
            location_label=user_address,
            notes='Burned 0.0000597064 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=TimestampMS(1689533783000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0x289ba1701c2f088cf0faf8b3705246331cb8a839'),
            balance=Balance(amount=FVal('6000')),
            location_label=user_address,
            notes=f'Bridge 6000 LPT from arbitrum_one address {user_address} to ethereum address {user_address} via arbitrum_one bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xbD91C9DF3C30F0e43B19b1dd05888CF9b647b781']])
def test_receive_erc20_on_ethereum(database, ethereum_inquirer, ethereum_accounts):
    """Data is taken from
    https://etherscan.io/tx/0xa235be4bde09d215518485acf55a577ca0662f27ff4af2a33f6867e4847596b8
    """
    evmhash = deserialize_evm_tx_hash('0xa235be4bde09d215518485acf55a577ca0662f27ff4af2a33f6867e4847596b8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=evmhash,
    )
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1690311851000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.006476938263774547')),
            location_label=user_address,
            notes='Burned 0.006476938263774547 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=206,
            timestamp=TimestampMS(1690311851000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0x58b6A8A3302369DAEc383334672404Ee733aB239'),
            balance=Balance(amount=FVal('6000')),
            location_label=user_address,
            notes=f'Bridge 6000 LPT from arbitrum_one address {user_address} to ethereum address {user_address} via arbitrum_one bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0x6A23F4940BD5BA117Da261f98aae51A8BFfa210A'),
        ),
    ]
