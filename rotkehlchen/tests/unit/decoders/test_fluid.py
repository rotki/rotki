from typing import TYPE_CHECKING, Final
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.fluid.constants import (
    CPT_FLUID,
    FLUID_LIQUIDITY,
    FLUID_VAULT_FACTORY,
    LIQUIDITY_LOG_OPERATE,
    VAULT_LOG_OPERATE,
)
from rotkehlchen.chain.evm.decoding.fluid.decoder import FluidCommonDecoder
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT, DecoderContext
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT, A_WBTC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ARBITRUM_ONE, LOCATION_ETHEREUM
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.fluid import add_fluid_position_event
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EventMetricKey,
    EvmTransaction,
    Timestamp,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

TEST_VAULT: Final = string_to_evm_address('0x3A0b7c8840D74D39552EF53F586dD8c3d1234C40')
TEST_NFT_ID: Final = 12345


def _vault_nft(nft_id: int, chain_id: ChainID = ChainID.ETHEREUM) -> Asset:
    return Asset(evm_address_to_identifier(
        address=FLUID_VAULT_FACTORY,
        chain_id=chain_id,
        token_type=TokenKind.ERC721,
        collectible_id=str(nft_id),
    ))


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6']])
def test_fluid_t1_mint_and_deposit_erc20(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x1fcf93b77b9a9078dd9fb5424386d00b2ee725e4318f8aaf2f9e06333566f328')),  # noqa: E501
    )
    assert (nft_asset := _vault_nft(19575)).resolve_to_evm_token().protocol == CPT_FLUID
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1793350811000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00004708400267444'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=527,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.MINT,
            event_subtype=HistoryEventSubType.NFT,
            asset=nft_asset,
            amount=ONE,
            location_label=user_address,
            notes='Create Fluid vault position 19575',
            counterparty=CPT_FLUID,
            address=(vault_address := string_to_evm_address('0x3A0b7c8840D74D39552EF53F586dD8c3d1234C40')),  # noqa: E501
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=529,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_WBTC,
            amount=FVal('0.026'),
            location_label=user_address,
            notes='Deposit 0.026 WBTC as collateral to Fluid',
            counterparty=CPT_FLUID,
            address=vault_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xe4637833F5513524D0B9337A75963619034fbB23']])
def test_fluid_t1_mint_and_deposit_native_eth(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf13ee83ff7b03e5a65332963c2454a1fda8e8afe85f5331c152bc80c3094ec32')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1793356319000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000143527925537763'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_ETH,
            amount=FVal('498'),
            location_label=user_address,
            notes='Deposit 498 ETH as collateral to Fluid',
            counterparty=CPT_FLUID,
            address=(vault_address := string_to_evm_address('0x0C8C77B7FF4c2aF7F6CEBbe67350A490E3DD6cB3')),  # noqa: E501
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=773,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.MINT,
            event_subtype=HistoryEventSubType.NFT,
            asset=_vault_nft(19578),
            amount=ONE,
            location_label=user_address,
            notes='Create Fluid vault position 19578',
            counterparty=CPT_FLUID,
            address=vault_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb60d601606351dC78a4f5493aa2AacC06A3B19E3']])
def test_fluid_t1_borrow(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x7d3ff3033b13a1abd0761dd79f4f16b0c85bbfa8ea9f84331602fcc2b22bc650')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794326387000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00077667552488244'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=532,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_USDT,
            amount=FVal('2000'),
            location_label=user_address,
            notes='Borrow 2000 USDT from Fluid',
            counterparty=CPT_FLUID,
            address=string_to_evm_address('0xE16A6f5359ABB1f61cE71e25dD0932e3E00B00eB'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x710541e9B9d900B9E340Aae7E3f90E208D129458']])
def test_fluid_t1_repay_erc20(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    add_fluid_position_event(
        database=ethereum_inquirer.database,
        nft_id=2063,
        timestamp=TimestampMS(1740000000000),
        location_label=ethereum_accounts[0],
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf6a74cf48d0025c634b7b99b0a72f828cce3523b5e8c487b663bd2c8dcc28189')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1744435967000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000204457418313292'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=389,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_USDC,
            amount=FVal('2413.118606'),
            location_label=user_address,
            notes='Repay 2413.118606 USDC to Fluid',
            counterparty=CPT_FLUID,
            address=string_to_evm_address('0x0C8C77B7FF4c2aF7F6CEBbe67350A490E3DD6cB3'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x43e00720bCbE904f70194300B58C46a3613bEF4C']])
def test_fluid_t1_withdraw_native_eth(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x1c6c4f59f406a2c08d53b3fc008d03e4d7e8578b22db61ad8f92670c9e6cf4bb')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1744431803000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000099828133976175'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_ETH,
            amount=FVal('8'),
            location_label=user_address,
            notes='Withdraw 8 ETH as collateral from Fluid',
            counterparty=CPT_FLUID,
            address=string_to_evm_address('0x0C8C77B7FF4c2aF7F6CEBbe67350A490E3DD6cB3'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x84378AaeAfFE1557d520f5347613715ACEA4A729']])
def test_fluid_t1_repay_native_eth_with_refund_and_withdraw(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Overpayment in a native ETH debt repayment refunds the excess; fold the refund out."""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf0cff2add92ff45414fbca009324b6d426a639250518060f7b76a20d6f78ead8')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1744436879000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00009312'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_ETH,
            amount=FVal('325.014252435855622278'),
            location_label=user_address,
            notes='Repay 325.014252435855622278 ETH to Fluid',
            counterparty=CPT_FLUID,
            address=(vault_address := string_to_evm_address('0xaD439b9D61b25af1ca4Cd211E3eCb9AfBaAEd84a')),  # noqa: E501
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=330,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_WBTC,
            amount=FVal('8.02631543'),
            location_label=user_address,
            notes='Withdraw 8.02631543 WBTC as collateral from Fluid',
            counterparty=CPT_FLUID,
            address=vault_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD7B2aF2Ea0Bed60E9f508D34e94eEc4ba7238e50']])
def test_fluid_t4_smart_collateral_deposit_and_smart_debt_borrow(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    add_fluid_position_event(
        database=ethereum_inquirer.database,
        nft_id=19744,
        timestamp=TimestampMS(1794000000000),
        location_label=ethereum_accounts[0],
    )
    deposit_events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(deposit_tx := deserialize_evm_tx_hash('0x75bad3dd9b7b4a338e689a927ab57488acd5b87e6027069109eabbc0159d7801')),  # noqa: E501
    )
    assert deposit_events == [
        EvmEvent(
            tx_ref=deposit_tx,
            sequence_index=0,
            timestamp=(deposit_ts := TimestampMS(1794323015000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000233772038946728'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=deposit_tx,
            sequence_index=526,
            timestamp=deposit_ts,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_WBTC,
            amount=FVal('0.001'),
            location_label=user_address,
            notes='Deposit 0.001 WBTC as collateral to Fluid',
            counterparty=CPT_FLUID,
            address=(vault_address := string_to_evm_address('0xDCe03288F9A109150f314ED0Ca9b59a690300d9d')),  # noqa: E501
        ),
    ]

    borrow_events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(borrow_tx := deserialize_evm_tx_hash('0x450d1ef4455cf690901ef7ddc4f7a1d5976862b83638a7e7cdc89f82050c5c5e')),  # noqa: E501
        evm_decoder=decoder,
    )
    assert borrow_events == [
        EvmEvent(
            tx_ref=borrow_tx,
            sequence_index=0,
            timestamp=(borrow_ts := TimestampMS(1794323087000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000264674775032385'),
            location_label=user_address,
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=borrow_tx,
            sequence_index=447,
            timestamp=borrow_ts,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_WBTC,
            amount=FVal('0.002845'),
            location_label=user_address,
            notes='Borrow 0.002845 WBTC from Fluid',
            counterparty=CPT_FLUID,
            address=vault_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf92D979ad76148eefd2C7800d57ce956860B0BC5']])
def test_fluid_t2_flash_leverage_router(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x10ad4b964d5fb11b22a746cdf8d672f0f580593c8f1d58b7a59ef7fad1d5aeb3')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794299315000)),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000035645487870392'),
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.TRANSACTION_TO_SELF,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Transaction to self of 0 ETH',
            address=user_address,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=935,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_USDC,
            amount=FVal('19197.792701'),
            location_label=user_address,
            address=string_to_evm_address('0x110c30efC1A0D378C22f01b08Cb52d27275EEd6e'),
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=938,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_USDC,
            amount=FVal('19197.792701'),
            location_label=user_address,
            notes='Deposit 19197.792701 USDC as collateral to Fluid',
            counterparty=CPT_FLUID,
            address=(vault_address := string_to_evm_address('0x01510793Df6aD5C1a8Ae592158713176Cbd17a62')),  # noqa: E501
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=953,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.MINT,
            event_subtype=HistoryEventSubType.NFT,
            asset=_vault_nft(19740),
            amount=ONE,
            location_label=user_address,
            notes='Create Fluid vault position 19740',
            counterparty=CPT_FLUID,
            address=vault_address,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=959,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_USDC,
            amount=FVal('79237.596619'),
            location_label=user_address,
            notes='Borrow 79237.596619 USDC from Fluid',
            counterparty=CPT_FLUID,
            address=vault_address,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=960,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=A_USDC,
            amount=FVal('79237.596619'),
            location_label=user_address,
            notes='Deposit 79237.596619 USDC as collateral to Fluid',
            counterparty=CPT_FLUID,
            address=vault_address,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9D6b911199b891c55a93e4bC635BF59E33d002d8']])
def test_fluid_liquidation(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xae41c596973d888bfd08c45ec4702cbb48b0367ca399aab2f86862d52d466edc'),
    )
    liquidator = ethereum_accounts[0]
    vault_address = string_to_evm_address('0x3A0b7c8840D74D39552EF53F586dD8c3d1234C40')
    assert any(
        isinstance(event, EvmSwapEvent) and
        event.event_type == HistoryEventType.TRADE and
        event.event_subtype == HistoryEventSubType.SPEND and
        event.asset == A_USDT and
        event.amount == FVal('23684.888485') and
        event.location_label == liquidator and
        event.counterparty == CPT_FLUID and
        event.address == vault_address and
        event.notes == 'Pay 23684.888485 USDT to liquidate Fluid vault'
        for event in events
    )
    assert any(
        isinstance(event, EvmSwapEvent) and
        event.event_type == HistoryEventType.TRADE and
        event.event_subtype == HistoryEventSubType.RECEIVE and
        event.asset == A_WBTC and
        event.amount == FVal('0.26601443') and
        event.location_label == liquidator and
        event.counterparty == CPT_FLUID and
        event.address == vault_address and
        event.notes == 'Receive 0.26601443 WBTC from Fluid vault liquidation'
        for event in events
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x471eC7404c89CB6C9570114B4030480CcDfEa2CA']])
def test_fluid_arbitrum_deposit(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
) -> None:
    add_fluid_position_event(
        database=arbitrum_one_inquirer.database,
        nft_id=13322,
        timestamp=TimestampMS(1794000000000),
        location_label=arbitrum_one_accounts[0],
        chain_id=ChainID.ARBITRUM_ONE,
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xb5cee36d3b065b7e2d15648b1c9a5ff2e9e524f37e9f15a16424a113d2d7e485')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1794790111000)),
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00000388182'),
            location_label=(user_address := arbitrum_one_accounts[0]),
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=FVal('320.637693'),
            location_label=user_address,
            notes='Deposit 320.637693 USDT0 as collateral to Fluid',
            counterparty=CPT_FLUID,
            address=(vault_address := string_to_evm_address('0xD9A7Dcdc57C6e44f00740dC73664fA456B983669')),  # noqa: E501
        ),
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=LOCATION_ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),
            amount=FVal('0'),
            location_label=user_address,
            address=vault_address,
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6',
    '0xe4637833F5513524D0B9337A75963619034fbB23',
]])
def test_fluid_nft_secondary_transfers_and_non_vault_liquidity_ignored(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    fluid_decoder = ethereum_transaction_decoder.decoders['Fluid']
    assert isinstance(fluid_decoder, FluidCommonDecoder)
    assert fluid_decoder.counterparties() == (CounterpartyDetails(
        identifier=CPT_FLUID,
        label='Fluid',
        image='fluid.svg',
    ),)
    tx = EvmTransaction(
        tx_hash=make_evm_tx_hash(),
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1790000000),
        block_number=26000000,
        from_address=ethereum_accounts[0],
        to_address=FLUID_VAULT_FACTORY,
        value=0,
        gas=100000,
        gas_price=0,
        gas_used=50000,
        input_data=b'',
        nonce=0,
    )
    non_vault_liq_log = EvmTxReceiptLog(
        log_index=0,
        data=b'\x00' * 64,
        address=FLUID_LIQUIDITY,
        topics=[LIQUIDITY_LOG_OPERATE, b'\x00' * 32, b'\x00' * 32],
    )
    assert fluid_decoder._decode_liquidity_log(DecoderContext(
        tx_log=non_vault_liq_log,
        transaction=tx,
        decoded_events=[],
        action_items=[],
        all_logs=[non_vault_liq_log],
    )) == DEFAULT_EVM_DECODING_OUTPUT

    external_sender = make_evm_address()
    transfer_log = EvmTxReceiptLog(
        log_index=1,
        data=b'',
        address=FLUID_VAULT_FACTORY,
        topics=[
            ERC20_OR_ERC721_TRANSFER,
            b'\x00' * 12 + hexstring_to_bytes(ethereum_accounts[0]),
            b'\x00' * 12 + hexstring_to_bytes(ethereum_accounts[1]),
            (42).to_bytes(32, 'big'),
        ],
    )
    receive_log = EvmTxReceiptLog(
        log_index=2,
        data=b'',
        address=FLUID_VAULT_FACTORY,
        topics=[
            ERC20_OR_ERC721_TRANSFER,
            b'\x00' * 12 + hexstring_to_bytes(external_sender),
            b'\x00' * 12 + hexstring_to_bytes(ethereum_accounts[0]),
            (99).to_bytes(32, 'big'),
        ],
    )
    with (
        patch_decoder_reload_data(),
        patch.object(ethereum_transaction_decoder.base, 'maybe_get_proxy_owner', return_value=None),  # noqa: E501
        ethereum_transaction_decoder.database.conn.read_ctx() as cursor,
    ):
        ethereum_transaction_decoder.reload_data(cursor=cursor)
        transfer_output = fluid_decoder._decode_vault_factory_log(DecoderContext(
            tx_log=transfer_log,
            transaction=tx,
            decoded_events=[],
            action_items=[],
            all_logs=[transfer_log, receive_log],
        ))
        receive_output = fluid_decoder._decode_vault_factory_log(DecoderContext(
            tx_log=receive_log,
            transaction=tx,
            decoded_events=[],
            action_items=[],
            all_logs=[transfer_log, receive_log],
        ))

    assert transfer_output.matched_counterparty == CPT_FLUID
    assert transfer_output.events is not None
    assert len(transfer_output.events) == 1
    assert transfer_output.events[0].event_type == HistoryEventType.TRANSFER
    assert transfer_output.events[0].event_subtype == HistoryEventSubType.NONE
    assert transfer_output.events[0].asset == _vault_nft(42)
    assert transfer_output.events[0].counterparty == CPT_FLUID
    assert transfer_output.events[0].notes == f'Transfer Fluid vault position 42 from {ethereum_accounts[0]} to {ethereum_accounts[1]}'  # noqa: E501

    assert receive_output.matched_counterparty == CPT_FLUID
    assert receive_output.events is not None
    assert len(receive_output.events) == 1
    assert receive_output.events[0].event_type == HistoryEventType.RECEIVE
    assert receive_output.events[0].event_subtype == HistoryEventSubType.NONE
    assert receive_output.events[0].asset == _vault_nft(99)
    assert receive_output.events[0].counterparty == CPT_FLUID
    assert receive_output.events[0].notes == f'Receive Fluid vault position 99 from {external_sender}'  # noqa: E501


def _pad_addr(address: ChecksumEvmAddress) -> bytes:
    return b'\x00' * 12 + hexstring_to_bytes(address)


def _make_tx(from_address: ChecksumEvmAddress, timestamp: Timestamp) -> EvmTransaction:
    return EvmTransaction(
        tx_hash=make_evm_tx_hash(),
        chain_id=ChainID.ETHEREUM,
        timestamp=timestamp,
        block_number=26000000,
        from_address=from_address,
        to_address=TEST_VAULT,
        value=0,
        gas=100000,
        gas_price=0,
        gas_used=50000,
        input_data=b'',
        nonce=0,
    )


def _nft_transfer_log(
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress,
) -> EvmTxReceiptLog:
    return EvmTxReceiptLog(
        log_index=0,
        data=b'',
        address=FLUID_VAULT_FACTORY,
        topics=[
            ERC20_OR_ERC721_TRANSFER,
            _pad_addr(from_address),
            _pad_addr(to_address),
            TEST_NFT_ID.to_bytes(32, 'big'),
        ],
    )


def _operate_logs(
        operate_user: ChecksumEvmAddress,
        col_raw: int,
        debt_raw: int,
        first_log_index: int = 0,
        to_address: ChecksumEvmAddress = ZERO_ADDRESS,
) -> list[EvmTxReceiptLog]:
    """FluidLiquidity and vault LogOperate pair of a native ETH operation on TEST_NFT_ID."""
    return [EvmTxReceiptLog(
        log_index=first_log_index,
        data=col_raw.to_bytes(32, 'big', signed=True) + debt_raw.to_bytes(32, 'big', signed=True),
        address=FLUID_LIQUIDITY,
        topics=[LIQUIDITY_LOG_OPERATE, _pad_addr(TEST_VAULT), _pad_addr(ETH_SPECIAL_ADDRESS)],
    ), EvmTxReceiptLog(
        log_index=first_log_index + 1,
        data=(
            _pad_addr(operate_user) +
            TEST_NFT_ID.to_bytes(32, 'big') +
            col_raw.to_bytes(32, 'big', signed=True) +
            debt_raw.to_bytes(32, 'big', signed=True) +
            _pad_addr(to_address)
        ),
        address=TEST_VAULT,
        topics=[VAULT_LOG_OPERATE],
    )]


def _eth_spend(tx: EvmTransaction, payer: ChecksumEvmAddress, amount: str) -> EvmEvent:
    return EvmEvent(
        tx_ref=tx.tx_hash,
        sequence_index=0,
        timestamp=ts_sec_to_ms(tx.timestamp),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=payer,
        address=FLUID_LIQUIDITY,
    )


def _eth_receive(tx: EvmTransaction, receiver: ChecksumEvmAddress, amount: str) -> EvmEvent:
    return EvmEvent(
        tx_ref=tx.tx_hash,
        sequence_index=0,
        timestamp=ts_sec_to_ms(tx.timestamp),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=receiver,
        address=FLUID_LIQUIDITY,
    )


def _load_tracked_accounts(tx_decoder: EthereumTransactionDecoder) -> None:
    with (
        patch_decoder_reload_data(),
        patch.object(tx_decoder.base, 'maybe_get_proxy_owner', return_value=None),
        tx_decoder.database.conn.read_ctx() as cursor,
    ):
        tx_decoder.reload_data(cursor=cursor)


def _decode_vault_operation(
        tx_decoder: EthereumTransactionDecoder,
        tx: EvmTransaction,
        decoded_events: list[EvmEvent],
        all_logs: list[EvmTxReceiptLog],
) -> list[EvmEvent]:
    """Run the Fluid post-decoding rule on synthetic logs and already decoded transfers."""
    fluid_decoder = tx_decoder.decoders['Fluid']
    assert isinstance(fluid_decoder, FluidCommonDecoder)
    tx_decoder.base.reset_sequence_counter(EvmTxReceipt(
        tx_hash=tx.tx_hash,
        chain_id=ChainID.ETHEREUM,
        contract_address=None,
        status=True,
        tx_type=0,
        logs=all_logs,
    ))
    return fluid_decoder._decode_vault_events(
        transaction=tx,
        decoded_events=decoded_events,
        all_logs=all_logs,
    )


@pytest.mark.parametrize('ethereum_accounts', [['0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6']])
def test_fluid_funding_untracked_nft_not_classified(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Deposits and repayments into a position last held by an untracked owner stay spends."""
    alice, bob = ethereum_accounts[0], make_evm_address()
    add_fluid_position_event(
        database=ethereum_transaction_decoder.database,
        nft_id=TEST_NFT_ID,
        timestamp=TimestampMS(1780000000000),
        location_label=alice,
    )
    add_fluid_position_event(
        database=ethereum_transaction_decoder.database,
        nft_id=TEST_NFT_ID,
        timestamp=TimestampMS(1780000001000),
        location_label=alice,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        address=bob,
    )
    _load_tracked_accounts(ethereum_transaction_decoder)
    tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000000))
    for operate_user, amount, col_raw, debt_raw in (
        (alice, '1', 10**18, 0),  # direct collateral deposit
        (alice, '2', 0, -(2 * 10**18)),  # direct debt repayment
        (make_evm_address(), '1', 10**18, 0),  # deposit through a router
    ):
        assert _decode_vault_operation(
            tx_decoder=ethereum_transaction_decoder,
            tx=tx,
            decoded_events=[_eth_spend(tx=tx, payer=alice, amount=amount)],
            all_logs=_operate_logs(operate_user=operate_user, col_raw=col_raw, debt_raw=debt_raw),
        ) == [_eth_spend(tx=tx, payer=alice, amount=amount)]


@pytest.mark.parametrize('ethereum_accounts', [['0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6']])
def test_fluid_position_owner_is_the_holder_at_operation_time(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """NFT transfers after an operation don't change who held the position when it happened."""
    alice, carol = ethereum_accounts[0], make_evm_address()
    add_fluid_position_event(
        database=ethereum_transaction_decoder.database,
        nft_id=TEST_NFT_ID,
        timestamp=TimestampMS(1780000000000),
        location_label=alice,
    )
    _load_tracked_accounts(ethereum_transaction_decoder)
    deposit_tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000000))
    expected_deposit = EvmEvent(
        tx_ref=deposit_tx.tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1790000000000),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
        asset=A_ETH,
        amount=ONE,
        location_label=alice,
        notes='Deposit 1 ETH as collateral to Fluid',
        counterparty=CPT_FLUID,
        address=TEST_VAULT,
    )
    assert _decode_vault_operation(
        tx_decoder=ethereum_transaction_decoder,
        tx=deposit_tx,
        decoded_events=[_eth_spend(tx=deposit_tx, payer=alice, amount='1')],
        all_logs=_operate_logs(operate_user=alice, col_raw=10**18, debt_raw=0),
    ) == [expected_deposit]

    add_fluid_position_event(  # alice sends the position to carol after the deposit
        database=ethereum_transaction_decoder.database,
        nft_id=TEST_NFT_ID,
        timestamp=TimestampMS(1790000100000),
        location_label=alice,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        address=carol,
    )
    assert _decode_vault_operation(  # redecoding the deposit still attributes it to alice
        tx_decoder=ethereum_transaction_decoder,
        tx=deposit_tx,
        decoded_events=[_eth_spend(tx=deposit_tx, payer=alice, amount='1')],
        all_logs=_operate_logs(operate_user=alice, col_raw=10**18, debt_raw=0),
    ) == [expected_deposit]

    later_tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000200))
    assert _decode_vault_operation(  # once carol holds it, alice's funding is a plain spend
        tx_decoder=ethereum_transaction_decoder,
        tx=later_tx,
        decoded_events=[_eth_spend(tx=later_tx, payer=alice, amount='1')],
        all_logs=_operate_logs(operate_user=alice, col_raw=10**18, debt_raw=0),
    ) == [_eth_spend(tx=later_tx, payer=alice, amount='1')]

    handover_tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000000))
    assert _decode_vault_operation(  # alice hands the position to carol, then funds it
        tx_decoder=ethereum_transaction_decoder,
        tx=handover_tx,
        decoded_events=[_eth_spend(tx=handover_tx, payer=alice, amount='1')],
        all_logs=[
            _nft_transfer_log(from_address=alice, to_address=carol),
            *_operate_logs(operate_user=alice, col_raw=10**18, debt_raw=0, first_log_index=1),
        ],
    ) == [_eth_spend(tx=handover_tx, payer=alice, amount='1')]


@pytest.mark.parametrize('ethereum_accounts', [['0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6']])
def test_fluid_later_received_position_not_owned_before(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Repaying a position that alice only receives afterwards is not alice's position activity."""
    alice = ethereum_accounts[0]
    add_fluid_position_event(
        database=ethereum_transaction_decoder.database,
        nft_id=TEST_NFT_ID,
        timestamp=TimestampMS(1790000100000),
        location_label=alice,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        address=make_evm_address(),
    )
    _load_tracked_accounts(ethereum_transaction_decoder)
    tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000000))
    assert _decode_vault_operation(
        tx_decoder=ethereum_transaction_decoder,
        tx=tx,
        decoded_events=[_eth_spend(tx=tx, payer=alice, amount='2')],
        all_logs=_operate_logs(operate_user=alice, col_raw=0, debt_raw=-(2 * 10**18)),
    ) == [_eth_spend(tx=tx, payer=alice, amount='2')]


def _decode_alice_funding_bob(
        tx_decoder: EthereumTransactionDecoder,
        alice: ChecksumEvmAddress,
        bob: ChecksumEvmAddress,
) -> tuple[list[EvmEvent], list[EvmEvent]]:
    """Decode alice depositing 1 ETH into, then repaying 2 ETH of, bob's position."""
    add_fluid_position_event(
        database=tx_decoder.database,
        nft_id=TEST_NFT_ID,
        timestamp=TimestampMS(1780000000000),
        location_label=bob,
    )
    _load_tracked_accounts(tx_decoder)
    deposit_tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000000))
    repay_tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000100))
    return _decode_vault_operation(
        tx_decoder=tx_decoder,
        tx=deposit_tx,
        decoded_events=[_eth_spend(tx=deposit_tx, payer=alice, amount='1')],
        all_logs=_operate_logs(operate_user=alice, col_raw=10**18, debt_raw=0),
    ), _decode_vault_operation(
        tx_decoder=tx_decoder,
        tx=repay_tx,
        decoded_events=[_eth_spend(tx=repay_tx, payer=alice, amount='2')],
        all_logs=_operate_logs(operate_user=alice, col_raw=0, debt_raw=-(2 * 10**18)),
    )


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6',
    '0xe4637833F5513524D0B9337A75963619034fbB23',
]])
def test_fluid_funding_another_tracked_account_nft(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Alice paying into bob's position is a transfer to bob followed by bob's protocol event."""
    alice, bob = ethereum_accounts
    deposit_events, repay_events = _decode_alice_funding_bob(
        tx_decoder=ethereum_transaction_decoder,
        alice=alice,
        bob=bob,
    )
    for events, amount, event_type, event_subtype, notes in (
        (
            deposit_events,
            '1',
            HistoryEventType.DEPOSIT,
            HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            'Deposit 1 ETH as collateral to Fluid',
        ), (
            repay_events,
            '2',
            HistoryEventType.SPEND,
            HistoryEventSubType.PAYBACK_DEBT,
            'Repay 2 ETH to Fluid',
        ),
    ):
        assert events == [EvmEvent(
            tx_ref=(tx_ref := events[0].tx_ref),
            sequence_index=0,
            timestamp=(timestamp := events[0].timestamp),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=alice,
            notes=f'Transfer {amount} ETH to {bob} for Fluid vault position {TEST_NFT_ID}',
            counterparty=CPT_FLUID,
            address=bob,
        ), EvmEvent(
            tx_ref=tx_ref,
            sequence_index=2,
            timestamp=timestamp,
            location=LOCATION_ETHEREUM,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=bob,
            notes=notes,
            counterparty=CPT_FLUID,
            address=TEST_VAULT,
        )]


@pytest.mark.accounting_update
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6',
    '0xe4637833F5513524D0B9337A75963619034fbB23',
]])
def test_fluid_funding_another_tracked_account_historical_balances(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
        database: DBHandler,
        messages_aggregator: MessagesAggregator,
) -> None:
    """Alice's funding of bob's position leaves the combined wallets once, not twice."""
    alice, bob = ethereum_accounts
    deposit_events, repay_events = _decode_alice_funding_bob(
        tx_decoder=ethereum_transaction_decoder,
        alice=alice,
        bob=bob,
    )
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1780000000000),
                location=LOCATION_ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('3'),
                location_label=alice,
            ), *deposit_events, *repay_events],
        )

    process_historical_balances(database=database, msg_aggregator=messages_aggregator)
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT timestamp, sequence_index, location_label, protocol, metric_value '
            'FROM event_metrics WHERE asset = ? AND metric_key = ? '
            'ORDER BY timestamp, sequence_index, location_label, protocol NULLS FIRST',
            (A_ETH.identifier, EventMetricKey.BALANCE.serialize()),
        ).fetchall() == [
            (1780000000000, 0, alice, None, '3'),
            (1790000000000, 0, alice, None, '2'),
            (1790000000000, 0, bob, None, '1'),
            (1790000000000, 2, bob, None, '0'),
            (1790000000000, 2, bob, CPT_FLUID, '1'),
            (1790000100000, 0, alice, None, '0'),
            (1790000100000, 0, bob, None, '2'),
            (1790000100000, 2, bob, None, '0'),
        ]
    assert DataIssuesManager(database).list_issues() == []


def _decode_alice_payouts(
        tx_decoder: EthereumTransactionDecoder,
        alice: ChecksumEvmAddress,
        bob: ChecksumEvmAddress,
        carol: ChecksumEvmAddress,
) -> tuple[list[EvmEvent], list[EvmEvent], list[EvmEvent]]:
    """Decode alice withdrawing 1 ETH to bob, borrowing 2 ETH to bob, and 1 ETH to carol."""
    _load_tracked_accounts(tx_decoder)
    withdraw_tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000000))
    borrow_bob_tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000100))
    borrow_carol_tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000200))
    return (
        _decode_vault_operation(
            tx_decoder=tx_decoder,
            tx=withdraw_tx,
            decoded_events=[_eth_receive(tx=withdraw_tx, receiver=bob, amount='1')],
            all_logs=_operate_logs(
                operate_user=alice,
                col_raw=-(10**18),
                debt_raw=0,
                to_address=bob,
            ),
        ),
        _decode_vault_operation(
            tx_decoder=tx_decoder,
            tx=borrow_bob_tx,
            decoded_events=[_eth_receive(tx=borrow_bob_tx, receiver=bob, amount='2')],
            all_logs=_operate_logs(
                operate_user=alice,
                col_raw=0,
                debt_raw=2 * 10**18,
                to_address=bob,
            ),
        ),
        _decode_vault_operation(
            tx_decoder=tx_decoder,
            tx=borrow_carol_tx,
            decoded_events=[],
            all_logs=_operate_logs(
                operate_user=alice,
                col_raw=0,
                debt_raw=10**18,
                to_address=carol,
            ),
        ),
    )


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6',
    '0xe4637833F5513524D0B9337A75963619034fbB23',
]])
def test_fluid_payout_to_another_account(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Withdrawals and borrows sent to another address book the owner leg then move value out."""
    alice, bob = ethereum_accounts
    carol = make_evm_address()
    withdraw_bob, borrow_bob, borrow_carol = _decode_alice_payouts(
        tx_decoder=ethereum_transaction_decoder,
        alice=alice,
        bob=bob,
        carol=carol,
    )
    assert withdraw_bob == [EvmEvent(
        tx_ref=(tx_ref := withdraw_bob[0].tx_ref),
        sequence_index=0,
        timestamp=(timestamp := withdraw_bob[0].timestamp),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        asset=A_ETH,
        amount=ONE,
        location_label=alice,
        notes='Withdraw 1 ETH as collateral from Fluid',
        counterparty=CPT_FLUID,
        address=TEST_VAULT,
    ), EvmEvent(
        tx_ref=tx_ref,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ONE,
        location_label=alice,
        notes=f'Transfer 1 ETH to {bob} for Fluid vault position {TEST_NFT_ID}',
        counterparty=CPT_FLUID,
        address=bob,
    )]
    assert borrow_bob == [EvmEvent(
        tx_ref=(tx_ref := borrow_bob[0].tx_ref),
        sequence_index=0,
        timestamp=(timestamp := borrow_bob[0].timestamp),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.GENERATE_DEBT,
        asset=A_ETH,
        amount=FVal('2'),
        location_label=alice,
        notes='Borrow 2 ETH from Fluid',
        counterparty=CPT_FLUID,
        address=TEST_VAULT,
    ), EvmEvent(
        tx_ref=tx_ref,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal('2'),
        location_label=alice,
        notes=f'Transfer 2 ETH to {bob} for Fluid vault position {TEST_NFT_ID}',
        counterparty=CPT_FLUID,
        address=bob,
    )]
    assert borrow_carol == [EvmEvent(
        tx_ref=(tx_ref := borrow_carol[0].tx_ref),
        sequence_index=2,
        timestamp=(timestamp := borrow_carol[0].timestamp),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.GENERATE_DEBT,
        asset=A_ETH,
        amount=ONE,
        location_label=alice,
        notes='Borrow 1 ETH from Fluid',
        counterparty=CPT_FLUID,
        address=TEST_VAULT,
    ), EvmEvent(
        tx_ref=tx_ref,
        sequence_index=3,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ONE,
        location_label=alice,
        notes=f'Send 1 ETH to {carol} for Fluid vault position {TEST_NFT_ID}',
        counterparty=CPT_FLUID,
        address=carol,
    )]


@pytest.mark.accounting_update
@pytest.mark.parametrize('ethereum_accounts', [[
    '0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6',
    '0xe4637833F5513524D0B9337A75963619034fbB23',
]])
def test_fluid_payout_to_another_account_historical_balances(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
        database: DBHandler,
        messages_aggregator: MessagesAggregator,
) -> None:
    """Payouts from alice's position to bob or untracked carol credit wallets once."""
    alice, bob = ethereum_accounts
    carol = make_evm_address()
    withdraw_bob, borrow_bob, borrow_carol = _decode_alice_payouts(
        tx_decoder=ethereum_transaction_decoder,
        alice=alice,
        bob=bob,
        carol=carol,
    )
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1780000000000),
                location=LOCATION_ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                location_label=alice,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=1,
                timestamp=TimestampMS(1780000000000),
                location=LOCATION_ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                asset=A_ETH,
                amount=ONE,
                location_label=alice,
                counterparty=CPT_FLUID,
                address=TEST_VAULT,
            ), *withdraw_bob, *borrow_bob, *borrow_carol],
        )

    process_historical_balances(database=database, msg_aggregator=messages_aggregator)
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT timestamp, sequence_index, location_label, protocol, metric_value '
            'FROM event_metrics WHERE asset = ? AND metric_key = ? '
            'ORDER BY timestamp, sequence_index, location_label, protocol NULLS FIRST',
            (A_ETH.identifier, EventMetricKey.BALANCE.serialize()),
        ).fetchall() == [
            (1780000000000, 0, alice, None, '1'),
            (1780000000000, 1, alice, None, '0'),
            (1780000000000, 1, alice, CPT_FLUID, '1'),
            (1790000000000, 0, alice, None, '1'),
            (1790000000000, 0, alice, CPT_FLUID, '0'),
            (1790000000000, 2, alice, None, '0'),
            (1790000000000, 2, bob, None, '1'),
            (1790000100000, 0, alice, None, '2'),
            (1790000100000, 2, alice, None, '0'),
            (1790000100000, 2, bob, None, '3'),
            (1790000200000, 2, alice, None, '1'),
            (1790000200000, 3, alice, None, '0'),
        ]
    assert DataIssuesManager(database).list_issues() == []


@pytest.mark.parametrize('ethereum_accounts', [['0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6']])
def test_fluid_untracked_operate_user_not_attributed_to_tx_sender(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Withdraw and borrow through an untracked smart account are not booked on from_address."""
    alice, smart_account = ethereum_accounts[0], make_evm_address()
    _load_tracked_accounts(ethereum_transaction_decoder)
    tx = _make_tx(from_address=alice, timestamp=Timestamp(1790000000))
    assert _decode_vault_operation(
        tx_decoder=ethereum_transaction_decoder,
        tx=tx,
        decoded_events=[],
        all_logs=_operate_logs(
            operate_user=smart_account,
            col_raw=0,
            debt_raw=10**18,
            to_address=smart_account,
        ),
    ) == []
    assert _decode_vault_operation(
        tx_decoder=ethereum_transaction_decoder,
        tx=tx,
        decoded_events=[_eth_receive(tx=tx, receiver=alice, amount='1')],
        all_logs=_operate_logs(
            operate_user=smart_account,
            col_raw=-(10**18),
            debt_raw=0,
            to_address=alice,
        ),
    ) == [EvmEvent(
        tx_ref=tx.tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1790000000000),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ONE,
        location_label=alice,
        notes=f'Receive 1 ETH from a Fluid withdrawal by {smart_account}',
        counterparty=CPT_FLUID,
        address=FLUID_LIQUIDITY,
    )]
