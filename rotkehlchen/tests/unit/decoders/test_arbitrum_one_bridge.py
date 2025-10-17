import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.arbitrum_one.modules.arbitrum_one_bridge.decoder import BRIDGE_ADDRESS
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.arbitrum_one_bridge.decoder import (
    BRIDGE_ADDRESS_MAINNET,
    L1_GATEWAY_ROUTER,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4e7DF0FDa2d203f5DFbaa34b9FB64DDe5133196e']])
def test_deposit_eth_from_ethereum_to_arbitrum_one(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xbe5b747193c68a7d1844053996e1a27a1279a4f1743f4b9a00e5a14152ee8641')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1690789463000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001207084037700187'),
            location_label=user_address,
            notes='Burn 0.001207084037700187 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1690789463000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.008374552015335015'),
            location_label=user_address,
            notes='Bridge 0.008374552015335015 ETH from Ethereum to Arbitrum One via Arbitrum One bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f'),  # DELAYED_INBOX_ADDRESS  # noqa: E501
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x4e7DF0FDa2d203f5DFbaa34b9FB64DDe5133196e']])
def test_receive_eth_on_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x30505174f2f82a6513f21eb5177e59935a6da95d057e4c1972e65da90ea1c547')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1690789735000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.008374552015335015'),
            location_label=user_address,
            notes='Bridge 0.008374552015335015 ETH from Ethereum to Arbitrum One via Arbitrum One bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0x5F8EF0FdA2d203f5DfbAa34B9fB64DDe51332A7f'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x5EA45c8E36704d7F4053Bb0e23cDd96E4d8b80F7']])
def test_withdraw_eth_from_arbitrum_one_to_ethereum(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xdb8e29f27a7b7b416f168e8135347703268a142b6776503e26419dbfc43bcabf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1688139924000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0000646535'),
            location_label=user_address,
            notes='Burn 0.0000646535 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1688139924000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('98.34759123048141'),
            location_label=user_address,
            notes='Bridge 98.34759123048141 ETH from Arbitrum One to Ethereum via Arbitrum One bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address(BRIDGE_ADDRESS),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x5EA45c8E36704d7F4053Bb0e23cDd96E4d8b80F7']])
def test_receive_eth_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2698916bd8d658ce6cfe032e5526fa345b3656a849870e72b1e853d22efdd7ac')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1688931083000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001688346842833805'),
            location_label=user_address,
            notes='Burn 0.001688346842833805 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1688931083000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('98.34759123048141'),
            location_label=user_address,
            notes='Bridge 98.34759123048141 ETH from Arbitrum One to Ethereum via Arbitrum One bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address(BRIDGE_ADDRESS_MAINNET),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xBEEC919d69FB1a5195964ee90959C413CDbACe28']])
def test_deposit_erc20_from_ethereum_to_arbitrum_one(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2eb4686e6b9857f02c1c8a035dc1ac7dcaf160fd52248b56a76de7774482390d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1690864931000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('ETH'),
            amount=FVal('0.002442413931855385'),
            location_label=user_address,
            notes='Burn 0.002442413931855385 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1690864931000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset('ETH'),
            amount=FVal('0.000225651577545344'),
            location_label=user_address,
            notes='Spend 0.000225651577545344 ETH to bridge ERC20 tokens to Arbitrum One',
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address(L1_GATEWAY_ROUTER),
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=208,
            timestamp=TimestampMS(1690864931000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            amount=FVal('25000'),
            location_label=user_address,
            notes='Bridge 25000 DAI from Ethereum to Arbitrum One via Arbitrum One bridge',
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0xA10c7CE4b876998858b1a9E12b10092229539400'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x78C13393Aee675DD7ED07ce992210750D1F5dB88']])
def test_receive_erc20_on_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x80e6c0835c3ead90dde524c3dfe49a067fd5b5cda93d5a223707e686d910d8a2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1691230958000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'),
            amount=FVal('0.00032674'),
            location_label=user_address,
            notes='Bridge 0.00032674 WBTC from Ethereum to Arbitrum One via Arbitrum One bridge',
            counterparty=CPT_ARBITRUM_ONE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xbD91C9DF3C30F0e43B19b1dd05888CF9b647b781']])
def test_withdraw_erc20_from_arbitrum_one_to_ethereum(arbitrum_one_inquirer, arbitrum_one_accounts, caplog):  # noqa: E501
    """Test that LPT withdrawals from arbitrum to L1 work fine"""
    tx_hash = deserialize_evm_tx_hash('0x90ca8a767118c27aa4f6370bc06d9f952ab88a9219431f68d8e2d33b4a15b395')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    gateway_address = '0x6D2457a4ad276000A615295f7A80F79E48CcD318'
    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1689533783000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0000597064'),
            location_label=user_address,
            notes='Burn 0.0000597064 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=TimestampMS(1689533783000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x289ba1701c2f088cf0faf8b3705246331cb8a839'),
            amount=FVal('115792089237316195423570985008687907853269984665640564015506.584007913129639935'),
            location_label=user_address,
            notes=f'Set LPT spending approval of {user_address} by {gateway_address} to 115792089237316195423570985008687907853269984665640564015506.584007913129639935',  # noqa: E501
            address=gateway_address,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=TimestampMS(1689533783000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0x289ba1701c2f088cf0faf8b3705246331cb8a839'),
            amount=FVal('6000'),
            location_label=user_address,
            notes='Bridge 6000 LPT from Arbitrum One to Ethereum via Arbitrum One bridge',
            counterparty=CPT_ARBITRUM_ONE,
            address=ZERO_ADDRESS,
        ),
    ]
    # also check that we only capture the erc20 log event and nothing else. Regression test for
    # https://github.com/orgs/rotki/projects/11?pane=issue&itemId=54372368
    assert '_decode_eth_withdraw_event failed due to Invalid ethereum address' not in caplog.text


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_withdraw_dai_from_arbitrum_one_to_ethereum(arbitrum_one_inquirer, arbitrum_one_accounts):
    """
    Test that DAI withdrawals from arbitrum to L1 work fine. This is just to test that
    our code is not token/gateway specific"""
    tx_hash = deserialize_evm_tx_hash('0xb425d3f1bfeb5438930115345ad2e3a4fb415db76f845e652d9b5ba945a484e2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )

    user_address = arbitrum_one_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1654845413000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00032141102469615'),
            location_label=user_address,
            notes='Burn 0.00032141102469615 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=7,
            timestamp=TimestampMS(1654845413000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'),
            amount=FVal('39566.332611058195231384'),
            location_label=user_address,
            notes='Bridge 39566.332611058195231384 DAI from Arbitrum One to Ethereum via Arbitrum One bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=ZERO_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xbD91C9DF3C30F0e43B19b1dd05888CF9b647b781']])
def test_receive_erc20_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa235be4bde09d215518485acf55a577ca0662f27ff4af2a33f6867e4847596b8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1690311851000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.006476938263774547'),
            location_label=user_address,
            notes='Burn 0.006476938263774547 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=206,
            timestamp=TimestampMS(1690311851000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0x58b6A8A3302369DAEc383334672404Ee733aB239'),
            amount=FVal('6000'),
            location_label=user_address,
            notes='Bridge 6000 LPT from Arbitrum One to Ethereum via Arbitrum One bridge',
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0x6A23F4940BD5BA117Da261f98aae51A8BFfa210A'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_receive_erc20_on_ethereum_old_bridge(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xdd71f6b50a24b2f6704819579cb4c0d27cf3d56bd3ba03fe8a7a9f9dc56eea52')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas, withdraw_amount = ethereum_accounts[0], TimestampMS(1655573929000), '0.003627235640125152', '39566.332611058195231384'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=278,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'),
            amount=FVal(withdraw_amount),
            location_label=user_address,
            notes=f'Bridge {withdraw_amount} DAI from Arbitrum One to Ethereum via Arbitrum One bridge',  # noqa: E501
            counterparty=CPT_ARBITRUM_ONE,
            address=string_to_evm_address('0xA10c7CE4b876998858b1a9E12b10092229539400'),
        ),
    ]
