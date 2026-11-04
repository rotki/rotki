from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.kiln.constants import CPT_KILN
from rotkehlchen.chain.evm.decoding.kiln.decoder import KilnDefiCommonDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDT
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.locations.constants import LOCATION_ARBITRUM_ONE, LOCATION_ETHEREUM
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

CW_AAVE_USDT_VAULT = string_to_evm_address('0x924e38bdFDa04990Fc78FEc258E8B83B3478B1Af')
A_CW_AAVE_USDT = Asset(f'eip155:1/erc20:{CW_AAVE_USDT_VAULT}')
BN_COMP_USDC_VAULT = string_to_evm_address('0x19A0F016Ac3989e754ab8216810beD8503bDA37e')
A_BN_COMP_USDC = Asset(f'eip155:42161/erc20:{BN_COMP_USDC_VAULT}')
A_ARB_USDC = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5Bc69a1180F450Eeec975BD1A8A6c1a87a214ed0']])
def test_kiln_defi_deposit(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x122cdb872f547d10e7dbfa2d74c25616600546bb3a2a34faf0ec6175d90053a8')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1793775359000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000015261156078762'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_USDT,
        amount=FVal(deposited_amount := '25275.5'),
        location_label=user_address,
        notes=f'Deposit {deposited_amount} USDT in Kiln DeFi',
        counterparty=CPT_KILN,
        address=CW_AAVE_USDT_VAULT,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_CW_AAVE_USDT,
        amount=FVal(received_amount := '23464.479408'),
        location_label=user_address,
        notes=f'Receive {received_amount} cwAaveUSDT from depositing in Kiln DeFi',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    )]
    vault_token = A_CW_AAVE_USDT.resolve_to_evm_token()
    assert vault_token.protocol == CPT_KILN
    assert [x.address for x in vault_token.underlying_tokens] == [A_USDT.resolve_to_evm_token().evm_address]  # noqa: E501
    assert isinstance(kiln_decoder := decoder.decoders['KilnDefi'], KilnDefiCommonDecoder)
    assert kiln_decoder.vault_checks == {CW_AAVE_USDT_VAULT: True}
    usdt_address = A_USDT.resolve_to_evm_token().evm_address  # a contract not behind the beacon
    assert kiln_decoder._is_kiln_vault(usdt_address) is False
    assert kiln_decoder.vault_checks == {CW_AAVE_USDT_VAULT: True, usdt_address: False}


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5Bc69a1180F450Eeec975BD1A8A6c1a87a214ed0']])
def test_kiln_defi_redeem(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x9322138f4fa18f68dc909ab144861a3de30168326a84b11b616a5b3c35332bca')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1793775779000)),
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000014001394154016'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_CW_AAVE_USDT,
        amount=FVal(returned_amount := '23464.479408'),
        location_label=user_address,
        notes=f'Return {returned_amount} cwAaveUSDT to Kiln DeFi',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_USDT,
        amount=FVal(withdrawn_amount := '25275.51022'),
        location_label=user_address,
        notes=f'Withdraw {withdrawn_amount} USDT from Kiln DeFi',
        counterparty=CPT_KILN,
        address=CW_AAVE_USDT_VAULT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xAC3D21866c459E0E6bb3FEd1C12Ecb812CD035E7']])
def test_kiln_defi_deposit_arbitrum(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf19dec569a3cad66ee3cc9641cf63679f65896688861846fa71ad9f32e230ef0')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1766002251000)),
        location=LOCATION_ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00000293722'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ARB_USDC,
        amount=FVal(deposited_amount := '0.111'),
        location_label=user_address,
        notes=f'Deposit {deposited_amount} USDC in Kiln DeFi',
        counterparty=CPT_KILN,
        address=BN_COMP_USDC_VAULT,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_BN_COMP_USDC,
        amount=FVal(received_amount := '0.104991'),
        location_label=user_address,
        notes=f'Receive {received_amount} bnCompUSDC from depositing in Kiln DeFi',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xAC3D21866c459E0E6bb3FEd1C12Ecb812CD035E7']])
def test_kiln_defi_withdraw_arbitrum(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x822b41ff6ba5b9874acd66a47f740b0c19b959a9bca92c74de778d54c33c33a2')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1730758588000)),
        location=LOCATION_ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00000490167107'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=LOCATION_ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_BN_COMP_USDC,
        amount=FVal(returned_amount := '0.101443'),
        location_label=user_address,
        notes=f'Return {returned_amount} bnCompUSDC to Kiln DeFi',
        counterparty=CPT_KILN,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=LOCATION_ARBITRUM_ONE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ARB_USDC,
        amount=FVal(withdrawn_amount := '0.10261'),
        location_label=user_address,
        notes=f'Withdraw {withdrawn_amount} USDC from Kiln DeFi',
        counterparty=CPT_KILN,
        address=BN_COMP_USDC_VAULT,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2e2aB1C1383c7Be56ffb8c9039E2d85681C936FD']])
def test_kiln_defi_ignores_other_erc4626_vaults(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """A deposit in an ERC4626 vault of another protocol (Spark sUSDC) is left to that
    protocol's decoder, which claims the share transfer first, so the vault is not even
    queried for being a Kiln vault"""
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0xf6cbd0040b8ba30e9eea85358c1d99e2e7105aac919e2f5964786129d508f6f9'),
    )
    assert all(event.counterparty != CPT_KILN for event in events)
    assert isinstance(kiln_decoder := decoder.decoders['KilnDefi'], KilnDefiCommonDecoder)
    assert kiln_decoder.vault_checks == {}
