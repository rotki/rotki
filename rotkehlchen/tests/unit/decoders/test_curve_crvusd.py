from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    CacheType,
    ChainID,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.fixture(name='crvusd_controller')
def fixture_crvusd_controller(request) -> 'ChecksumEvmAddress':
    """Fixture to set a crvUSD controller address in the GlobalDB
    so decoding works correctly in the tests.
    """
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(
                CacheType.CURVE_CRVUSD_CONTROLLERS,
                str(ChainID.ETHEREUM.serialize_for_db()),
            ),
            values=[addr := string_to_evm_address(request.param)],
        )
    return addr


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x23F8C7dB7A1B656652e9726ab264c5B181418B9f']])
@pytest.mark.parametrize('crvusd_controller', ['0x100dAa78fC509Db39Ef7D04DE0c1ABD299f4C6CE'], indirect=True)  # noqa: E501
def test_create_loan(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        crvusd_controller: 'ChecksumEvmAddress',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x164fc91dc34c9107715bbdc9a43f038e5c5e6b578bea535557f66328434f553a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount, receive_amount, approve_amount = TimestampMS(1741679231000), ethereum_accounts[0], '0.000893214862428306', '16', '26000', '115792089237316195423570985008687907853269984665640564039441.584007913129639935'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=178,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0'),
            amount=FVal(approve_amount),
            location_label=user_address,
            notes=f'Set wstETH spending approval of {user_address} by {crvusd_controller} to {approve_amount}',  # noqa: E501
            address=crvusd_controller,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=179,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} wstETH as collateral on Curve',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0x37417B2238AA52D0DD2D6252d989E728e8f706e4'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=180,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Borrow {receive_amount} crvUSD from Curve',
            counterparty=CPT_CURVE,
            product=EvmProduct.MINTING,
            address=crvusd_controller,
            extra_data={'controller_address': crvusd_controller},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9A778F01bc2D3c4DcFc5cA8eFE88a004566a8e0A']])
@pytest.mark.parametrize('crvusd_controller', ['0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67'], indirect=True)  # noqa: E501
def test_borrow_more(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        crvusd_controller: 'ChecksumEvmAddress',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xdb0872be57c7354043b578739c9d2566ec79dddf7ca7f93201b334f9c46cd15a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, receive_amount = TimestampMS(1742385419000), ethereum_accounts[0], '0.001382156244932288', '500'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=338,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Borrow {receive_amount} crvUSD from Curve',
            counterparty=CPT_CURVE,
            product=EvmProduct.MINTING,
            address=crvusd_controller,
            extra_data={'controller_address': crvusd_controller},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x684566C9FFcAC7F6A04C3a9997000d2d58C00824']])
@pytest.mark.parametrize('crvusd_controller', ['0xA920De414eA4Ab66b97dA1bFE9e6EcA7d4219635'], indirect=True)  # noqa: E501
def test_repay(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        crvusd_controller: 'ChecksumEvmAddress',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xe899e752f17209be62d912c24585823df2d53fda0b84d8a16901015b4a947e77')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, repay_amount = TimestampMS(1742391011000), ethereum_accounts[0], '0.00256845168196309', '100931.806980654679668337'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=217,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=ZERO,
            location_label=user_address,
            notes=f'Revoke crvUSD spending approval of {user_address} by {crvusd_controller}',
            address=crvusd_controller,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=218,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=Asset('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),
            amount=FVal(repay_amount),
            location_label=user_address,
            notes=f'Repay {repay_amount} crvUSD to Curve',
            counterparty=CPT_CURVE,
            address=crvusd_controller,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbbD9FB5A548e09D0B6E8B8197e38c5ac925cc973']])
@pytest.mark.parametrize('crvusd_controller', ['0x1C91da0223c763d2e0173243eAdaA0A2ea47E704'], indirect=True)  # noqa: E501
def test_remove_collateral(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        crvusd_controller: 'ChecksumEvmAddress',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xe53f1e91d37d06c9c1408be97dd6c5ed9701ca56fb6dbe46f1567d022e2f8783')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, withdraw_amount = TimestampMS(1742411687000), ethereum_accounts[0], '0.0018137064', '0.3'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=206,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0x18084fbA666a33d37592fA2633fD49a74DD93a88'),
            amount=FVal(withdraw_amount),
            location_label=user_address,
            notes=f'Withdraw {withdraw_amount} tBTC from Curve loan collateral',
            counterparty=CPT_CURVE,
            address=string_to_evm_address('0xf9bD9da2427a50908C4c6D1599D8e62837C2BCB0'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x53f2736FaE551C998D4e72E519F1aCf474264de4']])
@pytest.mark.parametrize('crvusd_controller', ['0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67'], indirect=True)  # noqa: E501
def test_borrow_extended(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        crvusd_controller: 'ChecksumEvmAddress',
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf79aa5972f2233b65f32cfdaa9ea14d7a325ebae85c633be7ebd37677903a032')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, deposit_amount = TimestampMS(1742167583000), ethereum_accounts[0], '0.00154011', '0.30677231'  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),
        amount=FVal(deposit_amount),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} WBTC into a leveraged Curve position',
        counterparty=CPT_CURVE,
        product=EvmProduct.MINTING,
        address=string_to_evm_address('0xE0438Eb3703bF871E31Ce639bd351109c88666ea'),
        extra_data={'controller_address': '0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67'},
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0E7e679C659Ee55b8cfA9B6D855faFE68B2F79Ab']])
def test_peg_keeper_update_provide(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xb557deee6fcf5fcbb03b539f81413a32e5ac40ccbc4915bcab291136b2049461')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, reward_amount = TimestampMS(1742991251000), ethereum_accounts[0], '0.00040529528116216', '0.263578930549885631'  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=145,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E'),
        amount=FVal(reward_amount),
        location_label=user_address,
        notes=f'Receive {reward_amount} crvUSDUSDC-f from Curve peg keeper update',
        counterparty=CPT_CURVE,
        address=string_to_evm_address('0x9201da0D97CaAAff53f01B2fB56767C7072dE340'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd740F5932F59d221a51ACa4891Cb79Cdf48e189C']])
def test_peg_keeper_update_withdraw(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x26ef0b958dcfe3bb3d27232a90cac132d4387e7e5b2f40f48b0e32080c154b32')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount, reward_amount = TimestampMS(1742617019000), ethereum_accounts[0], '0.0002972191728', '0.801175881145139442'  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=189,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E'),
        amount=FVal(reward_amount),
        location_label=user_address,
        notes=f'Receive {reward_amount} crvUSDUSDC-f from Curve peg keeper update',
        counterparty=CPT_CURVE,
        address=string_to_evm_address('0x9201da0D97CaAAff53f01B2fB56767C7072dE340'),
    )]
