from typing import TYPE_CHECKING
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
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT, A_WBTC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ARBITRUM_ONE, LOCATION_ETHEREUM
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    Timestamp,
    TimestampMS,
    TokenKind,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


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
    with patch.object(FluidCommonDecoder, '_get_nft_owner', return_value=ethereum_accounts[0]):
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
    with patch.object(FluidCommonDecoder, '_get_nft_owner', return_value=ethereum_accounts[0]):
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
    with patch.object(FluidCommonDecoder, '_get_nft_owner', return_value=arbitrum_one_accounts[0]):
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


@pytest.mark.parametrize('ethereum_accounts', [['0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6']])
def test_fluid_funding_untracked_nft_not_classified(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Permissionless deposits/repayments into an untracked owner's NFT stay plain spends."""
    fluid_decoder = ethereum_transaction_decoder.decoders['Fluid']
    assert isinstance(fluid_decoder, FluidCommonDecoder)

    alice = ethereum_accounts[0]
    bob = make_evm_address()
    router = make_evm_address()
    vault_address = string_to_evm_address('0x3A0b7c8840D74D39552EF53F586dD8c3d1234C40')
    nft_id = 12345
    tx_hash = make_evm_tx_hash()
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1790000000),
        block_number=26000000,
        from_address=alice,
        to_address=vault_address,
        value=0,
        gas=100000,
        gas_price=0,
        gas_used=50000,
        input_data=b'',
        nonce=0,
    )

    def _pad_addr(addr: ChecksumEvmAddress) -> bytes:
        return b'\x00' * 12 + hexstring_to_bytes(addr)

    def _make_liq_log(log_index: int, col_raw: int, debt_raw: int) -> EvmTxReceiptLog:
        return EvmTxReceiptLog(
            log_index=log_index,
            data=(
                col_raw.to_bytes(32, 'big', signed=True) +
                debt_raw.to_bytes(32, 'big', signed=True)
            ),
            address=FLUID_LIQUIDITY,
            topics=[
                LIQUIDITY_LOG_OPERATE,
                _pad_addr(vault_address),
                _pad_addr(ETH_SPECIAL_ADDRESS),
            ],
        )

    def _make_vault_log(
            log_index: int,
            operate_user: ChecksumEvmAddress,
            col_amt: int,
            debt_amt: int,
    ) -> EvmTxReceiptLog:
        return EvmTxReceiptLog(
            log_index=log_index,
            data=(
                _pad_addr(operate_user) +
                nft_id.to_bytes(32, 'big') +
                col_amt.to_bytes(32, 'big', signed=True) +
                debt_amt.to_bytes(32, 'big', signed=True) +
                _pad_addr(ZERO_ADDRESS)
            ),
            address=vault_address,
            topics=[VAULT_LOG_OPERATE],
        )

    def _make_spend_event(sequence_index: int, amount: str) -> EvmEvent:
        return EvmEvent(
            tx_ref=tx_hash,
            sequence_index=sequence_index,
            timestamp=TimestampMS(1790000000000),
            location=LOCATION_ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(amount),
            location_label=alice,
            address=FLUID_LIQUIDITY,
        )

    with (
        patch_decoder_reload_data(),
        patch.object(ethereum_transaction_decoder.base, 'maybe_get_proxy_owner', return_value=None),  # noqa: E501
        patch.object(fluid_decoder, '_call_view', return_value=bob),
        ethereum_transaction_decoder.database.conn.read_ctx() as cursor,
    ):
        ethereum_transaction_decoder.reload_data(cursor=cursor)

        # 1. Direct collateral deposit by Alice into Bob's NFT.
        deposit_spend = _make_spend_event(sequence_index=1, amount='1')
        deposit_events = fluid_decoder._decode_vault_events(
            transaction=tx,
            decoded_events=[deposit_spend],
            all_logs=[
                _make_liq_log(log_index=0, col_raw=10**18, debt_raw=0),
                _make_vault_log(log_index=1, operate_user=alice, col_amt=10**18, debt_amt=0),
            ],
        )
        assert deposit_events == [deposit_spend]
        assert deposit_spend.event_type == HistoryEventType.SPEND
        assert deposit_spend.event_subtype == HistoryEventSubType.NONE
        assert deposit_spend.counterparty is None

        # 2. Direct debt repayment by Alice on Bob's NFT.
        repay_spend = _make_spend_event(sequence_index=2, amount='2')
        repay_events = fluid_decoder._decode_vault_events(
            transaction=tx,
            decoded_events=[repay_spend],
            all_logs=[
                _make_liq_log(log_index=0, col_raw=0, debt_raw=-(2 * 10**18)),
                _make_vault_log(log_index=1, operate_user=alice, col_amt=0, debt_amt=-(2 * 10**18)),  # noqa: E501
            ],
        )
        assert repay_events == [repay_spend]
        assert repay_spend.event_type == HistoryEventType.SPEND
        assert repay_spend.event_subtype == HistoryEventSubType.NONE
        assert repay_spend.counterparty is None

        # 3. Router-mediated deposit where transaction.from_address is Alice, NFT is Bob's.
        router_spend = _make_spend_event(sequence_index=3, amount='1')
        router_events = fluid_decoder._decode_vault_events(
            transaction=tx,
            decoded_events=[router_spend],
            all_logs=[
                _make_liq_log(log_index=0, col_raw=10**18, debt_raw=0),
                _make_vault_log(log_index=1, operate_user=router, col_amt=10**18, debt_amt=0),
            ],
        )
        assert router_events == [router_spend]
        assert router_spend.event_type == HistoryEventType.SPEND
        assert router_spend.event_subtype == HistoryEventSubType.NONE
        assert router_spend.counterparty is None

        # 4. Alice transfers NFT to Bob in the same tx, then deposits collateral.
        transfer_and_deposit_spend = _make_spend_event(sequence_index=4, amount='1')
        nft_transfer_log = EvmTxReceiptLog(
            log_index=0,
            data=b'',
            address=FLUID_VAULT_FACTORY,
            topics=[
                ERC20_OR_ERC721_TRANSFER,
                _pad_addr(alice),
                _pad_addr(bob),
                nft_id.to_bytes(32, 'big'),
            ],
        )
        transfer_deposit_events = fluid_decoder._decode_vault_events(
            transaction=tx,
            decoded_events=[transfer_and_deposit_spend],
            all_logs=[
                nft_transfer_log,
                _make_liq_log(log_index=1, col_raw=10**18, debt_raw=0),
                _make_vault_log(log_index=2, operate_user=alice, col_amt=10**18, debt_amt=0),
            ],
        )
        assert transfer_deposit_events == [transfer_and_deposit_spend]
        assert transfer_and_deposit_spend.event_type == HistoryEventType.SPEND
        assert transfer_and_deposit_spend.event_subtype == HistoryEventSubType.NONE
        assert transfer_and_deposit_spend.counterparty is None


@pytest.mark.parametrize('ethereum_accounts', [[
    '0xB83E6edF8325e7d1Fc916A021866BeFe475DdbB6',
    '0xe4637833F5513524D0B9337A75963619034fbB23',
]])
def test_fluid_funding_another_tracked_account_nft(
        ethereum_transaction_decoder: EthereumTransactionDecoder,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """When tracked Alice funds tracked Bob's NFT, Alice keeps SPEND and Bob gets DEPOSIT."""
    fluid_decoder = ethereum_transaction_decoder.decoders['Fluid']
    assert isinstance(fluid_decoder, FluidCommonDecoder)

    alice, bob = ethereum_accounts[0], ethereum_accounts[1]
    vault_address = string_to_evm_address('0x3A0b7c8840D74D39552EF53F586dD8c3d1234C40')
    tx_hash = make_evm_tx_hash()
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1790000000),
        block_number=26000000,
        from_address=alice,
        to_address=vault_address,
        value=0,
        gas=100000,
        gas_price=0,
        gas_used=50000,
        input_data=b'',
        nonce=0,
    )

    def _pad_addr(addr: ChecksumEvmAddress) -> bytes:
        return b'\x00' * 12 + hexstring_to_bytes(addr)

    liq_log = EvmTxReceiptLog(
        log_index=0,
        data=(10**18).to_bytes(32, 'big', signed=True) + (0).to_bytes(32, 'big', signed=True),
        address=FLUID_LIQUIDITY,
        topics=[
            LIQUIDITY_LOG_OPERATE,
            _pad_addr(vault_address),
            _pad_addr(ETH_SPECIAL_ADDRESS),
        ],
    )
    vault_log = EvmTxReceiptLog(
        log_index=1,
        data=(
            _pad_addr(alice) +
            (12345).to_bytes(32, 'big') +
            (10**18).to_bytes(32, 'big', signed=True) +
            (0).to_bytes(32, 'big', signed=True) +
            _pad_addr(ZERO_ADDRESS)
        ),
        address=vault_address,
        topics=[VAULT_LOG_OPERATE],
    )
    alice_spend = EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=TimestampMS(1790000000000),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal('1'),
        location_label=alice,
        address=FLUID_LIQUIDITY,
    )

    with (
        patch_decoder_reload_data(),
        patch.object(ethereum_transaction_decoder.base, 'maybe_get_proxy_owner', return_value=None),  # noqa: E501
        patch.object(fluid_decoder, '_call_view', return_value=bob),
        ethereum_transaction_decoder.database.conn.read_ctx() as cursor,
    ):
        ethereum_transaction_decoder.reload_data(cursor=cursor)
        events = fluid_decoder._decode_vault_events(
            transaction=tx,
            decoded_events=[alice_spend],
            all_logs=[liq_log, vault_log],
        )

    assert len(events) == 2
    assert events[0] is alice_spend
    assert alice_spend.event_type == HistoryEventType.SPEND
    assert alice_spend.event_subtype == HistoryEventSubType.NONE
    assert alice_spend.location_label == alice
    assert alice_spend.counterparty is None

    assert events[1].event_type == HistoryEventType.DEPOSIT
    assert events[1].event_subtype == HistoryEventSubType.DEPOSIT_TO_PROTOCOL
    assert events[1].asset == A_ETH
    assert events[1].amount == FVal('1')
    assert events[1].location_label == bob
    assert events[1].counterparty == CPT_FLUID
    assert events[1].address == vault_address
