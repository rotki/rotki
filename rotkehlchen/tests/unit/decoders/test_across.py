from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.across.constants import CPT_ACROSS
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    SupportedBlockchain,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_socket_across_receive_on_arbitrum(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0x0fe6509df413361b7aa903ca810aa91151a1e44f51dd05c6fbc838d506e17704',
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=TimestampMS(1739477346000),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
        amount=FVal('365.669864'),
        location_label=user_address,
        notes='Bridge 365.669864 USDC from Scroll to Arbitrum One via Across',
        counterparty=CPT_ACROSS,
        address=string_to_evm_address('0xCad97616f91872C02BA3553dB315Db4015cBE850'),
        extra_data={'bridge': {
            'from_chain': 534352,
            'to_chain': 42161,
            'from_address': user_address,
            'to_address': user_address,
            'transfer_id': '1295289',
        }},
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(
    WeightedNode(  # give some open RPC for Base to get the data from
        node_info=NodeName(
            name='base-open-rpc',
            endpoint='https://mainnet.base.org',
            owned=False,
            blockchain=SupportedBlockchain.BASE,
        ),
        active=True,
        weight=ONE,
    ),
)])
@pytest.mark.parametrize('base_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_across_bridge_receive_on_base(
        base_inquirer: BaseInquirer,
        base_accounts: list[ChecksumEvmAddress],
        allow_base_routescan,
):
    """Test that a Across bridge fill (withdrawal) on Base is decoded correctly.

    Transaction: 0xcc6297f80c413865b7dcc269f305e79216befd98d393a2ce89fe67131c6b4172
    The user (0xc37b...) receives 0.01 ETH on Base bridged from Arbitrum One via Across.
    """
    tx_hash = deserialize_evm_tx_hash('0xcc6297f80c413865b7dcc269f305e79216befd98d393a2ce89fe67131c6b4172')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1696328659000),
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount := '0.00980467456898255'),
            location_label=base_accounts[0],
            notes=f'Bridge {bridge_amount} ETH from Arbitrum One to Base via Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0x09aea4b2242abC8bb4BB78D537A67a245A7bEC64'),
            extra_data={'bridge': {
                'from_chain': 42161,
                'to_chain': 8453,
                'from_address': '0x41ee28EE05341E7fdDdc8d433BA66054Cd302cA1',
                'to_address': '0xc37b40ABdB939635068d3c5f13E7faF686F03B65',
                'transfer_id': '1142258',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xF5d90Ac6747CB3352F05BF61f48b991ACeaE28eB']])
def test_across_relayed_bridge_receive_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x742fbbe405ea7a547e30895719e3de09b852f5540a67b6bbd0cc8546131c6318')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1771136963000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_ETH,
        amount=FVal(bridge_amount := '0.041982585504559745'),
        location_label=ethereum_accounts[0],
        notes=f'Bridge {bridge_amount} ETH from Arbitrum One to Ethereum via Across',
        counterparty=CPT_ACROSS,
        address=string_to_evm_address('0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5'),
        extra_data={'bridge': {
            'from_chain': 42161,
            'to_chain': 1,
            'from_address': '0xF5d90Ac6747CB3352F05BF61f48b991ACeaE28eB',
            'to_address': '0xF5d90Ac6747CB3352F05BF61f48b991ACeaE28eB',
            'transfer_id': '4207290',
        }},
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf70da97812CB96acDF810712Aa562db8dfA3dbEF']])
def test_across_relayed_bridge_receive_usdc_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xee7641ad46d4367a371a7320767323a0a7cb1f5301b27235e884551d715b2e0f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=150,
        timestamp=TimestampMS(1782487955000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_USDC,
        amount=FVal(bridge_amount := '99970.446325'),
        location_label=ethereum_accounts[0],
        notes=f'Bridge {bridge_amount} USDC from Binance Smart Chain to Ethereum via Across',
        counterparty=CPT_ACROSS,
        address=string_to_evm_address('0x07aE8551Be970cB1cCa11Dd7a11F47Ae82e70E67'),
        extra_data={'bridge': {
            'from_chain': 56,
            'to_chain': 1,
            'from_address': '0xf70da97812CB96acDF810712Aa562db8dfA3dbEF',
            'to_address': '0xf70da97812CB96acDF810712Aa562db8dfA3dbEF',
            'transfer_id': '778375',
        }},
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6b21bb0D79C543B13DEE153700788D2c008633E5']])
def test_across_bridge_deposit_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x01456be6d500a21b91941e569df54ec4760868d4b51ba9ef2ddab59d33d3c21f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1782469871000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000078206217311286'),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=364,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDT,
            amount=FVal(bridge_amount := '422.866751'),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDT from Ethereum to Arbitrum One via Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5'),
            extra_data={'bridge': {
                'from_chain': 1,
                'to_chain': 42161,
                'from_address': '0x6b21bb0D79C543B13DEE153700788D2c008633E5',
                'to_address': '0x6b21bb0D79C543B13DEE153700788D2c008633E5',
                'transfer_id': '4024312',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x56a1A34F0d33788ebA53e2706854A37A5F275536']])
def test_across_bridge_deposit_to_solana(
        arbitrum_one_inquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xb8b7c18165533055bd9bd136b1bf67d817f4100725b6dfd051ed359cf7ea2182')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1762471058000)),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0000008075'),
            location_label=(user_address := arbitrum_one_accounts[0]),
            notes='Burn 0.0000008075 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal('120'),
            location_label=user_address,
            notes='Bridge 120 USDC from Arbitrum One to Solana via Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A'),
            extra_data={'bridge': {
                'from_chain': 42161,
                'to_chain': 'solana',
                'from_address': user_address,
                'to_address': '7T8ckKtdc5DH7ACS5AnCny7rVXYJPEsaAbdBri1FhPxY',
                'transfer_id': '3982708',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2b0989d09867f9a54EcB7c1b5F2F5960f199e6a8']])
def test_across_remove_liquidity_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5a10ed0c32f81029b6693c60289817f24d45e937b926ff80b9732b9280651610')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1782437855000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.0000111586464'),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xb0C8fEf534223B891D4A430e49537143829c4817'),
            amount=FVal(lp_amount := '0.712671566804358911'),
            location_label=user_address,
            notes=f'Return {lp_amount} Av2-ACX-LP to Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0x0000000000000000000000000000000000000000'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x44108f0223A3C3028F5Fe7AEC7f9bb2E66beF82F'),
            amount=FVal(receive_amount := '0.713737293741463927'),
            location_label=user_address,
            notes=f'Receive {receive_amount} ACX after removing liquidity from Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0xc186fA914353c44b2E33eBE05f21846F1048bEda'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x58D7Fc9319c926e21cea96A32B230B71B244196D']])
def test_across_add_liquidity_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x17244a522c12ab3edc12ddf0722cdfbb95eb5068a56159f4e551cb0265912071')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1782455999000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000078615407463768'),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC,
            amount=FVal(deposit_amount := '1'),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} USDC to Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0xc186fA914353c44b2E33eBE05f21846F1048bEda'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xC9b09405959f63F72725828b5d449488b02be1cA'),
            amount=FVal(lp_amount := '0.941792'),
            location_label=user_address,
            notes=f'Receive {lp_amount} Av2-USDC-LP from Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0x0000000000000000000000000000000000000000'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xa25Ad78E8BF1Ff9e5872662934eC4984b92611Ff']])
def test_across_stake_lp_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x7d5719bed42d5013ea52fa6dc5d868b28795ed6d2f784214ebbcfd7c9087bbf1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1782314207000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000149178245272874'),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=231,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=Asset('eip155:1/erc20:0x59C1427c658E97a7d568541DaC780b2E5c8affb4'),
            amount=FVal(lp_amount := '0.02093904'),
            location_label=user_address,
            notes=f'Deposit {lp_amount} Av2-WBTC-LP into Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0x9040e41eF5E8b281535a96D9a48aCb8cfaBD9a48'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x8780b720095923F4c1D6D84b52772aC188914d67']])
def test_across_unstake_lp_on_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa28735c30fb6a83b490bfc669259315e1ed1ac66d5783e0c478f38ce84dfb12d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1782252815000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.000222559515065628'),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=294,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=Asset('eip155:1/erc20:0x59C1427c658E97a7d568541DaC780b2E5c8affb4'),
            amount=FVal(lp_amount := '0.1'),
            location_label=user_address,
            notes=f'Withdraw {lp_amount} Av2-WBTC-LP from Across',
            counterparty=CPT_ACROSS,
            address=string_to_evm_address('0x9040e41eF5E8b281535a96D9a48aCb8cfaBD9a48'),
        ),
    ]
