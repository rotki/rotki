from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.solana.decoding.constants import (
    ANCHOR_EVENT_DISCRIMINATOR,
    SPL_TOKEN_CLOSE_ACCOUNT_DISCRIMINATOR,
    SPL_TOKEN_PROGRAM,
    SPL_TOKEN_SYNC_NATIVE_DISCRIMINATOR,
    SYSTEM_PROGRAM,
)
from rotkehlchen.chain.solana.decoding.structures import SolanaDecoderContext
from rotkehlchen.chain.solana.decoding.tools import SolanaDecoderTools
from rotkehlchen.chain.solana.modules.okx.constants import (
    CPT_OKX,
    OKX_DEX_ROUTER_V2_PROGRAM,
    SWAP_CPI_EVENT2_DISCRIMINATOR,
    SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR,
    SWAP_TOC_V2_CPI_EVENT2_DISCRIMINATOR,
    SWAP_WITH_FEES_CPI_EVENT2_DISCRIMINATOR,
    SWAP_WITH_FEES_CPI_EVENT_DISCRIMINATOR,
    SWAP_WITH_FEES_CPI_EVENT_ENHANCED2_DISCRIMINATOR,
)
from rotkehlchen.chain.solana.modules.okx.decoder import OkxDecoder, _parse_cpi_event_fees
from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.constants.assets import A_WSOL
from rotkehlchen.errors.misc import NotSPLConformant
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.solana_swap import SolanaSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import (
    deserialize_solana_pubkey,
    deserialize_tx_signature,
)
from rotkehlchen.tests.utils.constants import A_SOL
from rotkehlchen.tests.utils.solana import get_decoded_events_of_solana_tx
from rotkehlchen.types import SolanaAddress, Timestamp, TimestampMS
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['399WCXP1i2V2VM5DvCz1U5jN8jE4U8cuor9W7h8ri3Wu']])
def test_swap_tob_sol_to_token_with_commission(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Swap SOL -> token via OKX SwapTob with commission paid in SOL."""
    signature = deserialize_tx_signature('7weJDgQqqkjTLxEAPRs2c247KTkjMMsXAspWwhLostyZmx74ZhSGHCkmg2jDagDH2gJxRB2BZsn3QHD8CFr2At3')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1795114989000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal('0.000080001'),
        location_label=(user_address := solana_accounts[0]),
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=(tip_amount := FVal('0.000006')),
        location_label=user_address,
        notes=f'Send {tip_amount} SOL to 4gQT88rvHr6ay8XvmUUriL5FTjsSuvkvH8ybz3etVLBb',
        address=SolanaAddress('4gQT88rvHr6ay8XvmUUriL5FTjsSuvkvH8ybz3etVLBb'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=4,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_SOL,
        amount=(spend_amount := FVal('0.045571061')),
        location_label=user_address,
        notes=f'Swap {spend_amount} SOL in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=5,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:HGHJCdysTaaYDJKwwQ3UmcodCw9xjpfFDvcShVVBpump'),
        amount=(receive_amount := FVal('611224.436101')),
        location_label=user_address,
        notes=f'Receive {receive_amount} sexcoin as the result of a swap in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=6,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=(fee_amount := FVal('0.000390674')),
        location_label=user_address,
        notes=f'Spend {fee_amount} SOL as OKX swap fee',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['5Zq2sTUPVnbYGDR5VQmtQodspXehhtBuky59iTcajrn8']])
def test_swap_tob_v3_token_to_token(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Multi-hop token-to-token swap via OKX SwapTobV3."""
    signature = deserialize_tx_signature('53A53g2Sw3Tj45CXb3scmQ2EjUmbK96NgEWcJjbwzx5JkagBNHpVFqcsgszURttgH5yDXZRqGukBeWjz2BTzkqtx')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=(timestamp := TimestampMS(1795790331000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=(transfer_amount := FVal('0.30171')),
        location_label=(user_address := solana_accounts[0]),
        notes=f'Send {transfer_amount} USDC to R4rNJHaffSUotNmqSKNEfDcJE8A7zJUkaoM5Jkd7cYX',
        address=SolanaAddress('R4rNJHaffSUotNmqSKNEfDcJE8A7zJUkaoM5Jkd7cYX'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=(spend_amount := FVal('14.783784')),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=4,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:39nuVgw8RCVC8PgGuuuaa8WoAERA61cTw85oUvBLT2va'),
        amount=(receive_amount := FVal('242287.292533')),
        location_label=user_address,
        notes=f'Receive {receive_amount} COMPUTE as the result of a swap in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['EJD4kAw5TuFP4B9F9NrS57t9P9MtabjTymgEhHrHg7CA']])
def test_swap_toc_sol_to_token_with_platform_fee(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Swap SOL -> token via OKX SwapToc with SyncNative/CloseAccount and platform fee."""
    signature = deserialize_tx_signature('5QdUFMdhUxf2uEiRffM7QasMJ4HckDovTz7rc1aoaevQtHD4WfKbrFnAjoAwv9kdkUgU8MFMYjiBph4kWu1izeuH')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1795790439000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal('0.0001639'),
        location_label=(user_address := solana_accounts[0]),
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=(tip_amount := FVal('0.0002')),
        location_label=user_address,
        notes=f'Send {tip_amount} SOL to HCg8X7XZXWibg9rS4oBXsYdp7cwnewX4B9ZyxwRD3oqR',
        address=SolanaAddress('HCg8X7XZXWibg9rS4oBXsYdp7cwnewX4B9ZyxwRD3oqR'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=4,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_SOL,
        amount=(spend_amount := FVal('0.4975')),
        location_label=user_address,
        notes=f'Swap {spend_amount} SOL in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=5,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:4gekdrLHoMtP2Qo9QHxM4Z8BDB9TibHKFEMkbMbMMTAb'),
        amount=(receive_amount := FVal('503143.660239')),
        location_label=user_address,
        notes=f'Receive {receive_amount} H100 as the result of a swap in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=6,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=(fee_amount := FVal('0.0025')),
        location_label=user_address,
        notes=f'Spend {fee_amount} SOL as OKX swap fee',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['EBs1Ri4v5VVSsnXG1YrXiaubNwMMiBUL9phfw8q5awDQ']])
def test_swap_tob_token_to_sol(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Swap token -> SOL via OKX SwapTob with temporary WSOL ATA closed to user."""
    signature = deserialize_tx_signature('4ftSxtdVc75QRjroorPR8YHygDM7chdF9hkow7LN2AzdkRjiixGsUXYr3cBoBwXPNRCEgrQvf8mDhvfVP1KgqPN2')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1795790470000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal('0.000008462'),
        location_label=(user_address := solana_accounts[0]),
        counterparty=CPT_GAS,
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:ysPp2Bt2j2UQu2tZwtSJz7JxyrmQ8GJcNJE5NyDoS5a'),
        amount=(spend_amount := FVal('0.055771')),
        location_label=user_address,
        notes=f'Swap {spend_amount} MUSK4 in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_SOL,
        amount=(receive_amount := FVal('0.000235574')),
        location_label=user_address,
        notes=f'Receive {receive_amount} SOL as the result of a swap in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['DpfNj5tD8Y2jB32ru2t4p43aXcHcBrf97i9HazLuWXwu']])
def test_swap_tob_with_receiver_token_to_sol(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Swap token -> SOL via OKX SwapTobWithReceiver with router closing temp WSOL ATA."""
    signature = deserialize_tx_signature('2W2VsEDBum2QuaoFdFGutcyvCogo5ZEVTzeoyFx2i6fqitr8o418asTQ5fUkyqkN1hGASCovEzWWuRcLV8fV2Zr6')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1795790438000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal('0.000436148'),
        location_label=(user_address := solana_accounts[0]),
        counterparty=CPT_GAS,
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:CASHx9KJUStyftLFWGvEVf59SGeG9sh5FfcnZMVPCASH'),
        amount=(spend_amount := FVal('109.489594')),
        location_label=user_address,
        notes=f'Swap {spend_amount} CASH in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_SOL,
        amount=(receive_amount := FVal('1.513949624')),
        location_label=user_address,
        notes=f'Receive {receive_amount} SOL as the result of a swap in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=receive_amount,
        location_label=user_address,
        notes=f'Send {receive_amount} SOL to 68aTHZqf6DSzKeVXNfqmTBzXdPXE4UoJrTWfi8gxQAcG',
        address=SolanaAddress('68aTHZqf6DSzKeVXNfqmTBzXdPXE4UoJrTWfi8gxQAcG'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['DN2Yc3AzzBQ6jLqDM33bVUSnbgDsPEys96PjxC16qfnA']])
def test_swap_with_fees2_token_to_sol_destination_fee(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Swap token -> SOL via OKX SwapWithFees2 with destination-mint SOL fee."""
    signature = deserialize_tx_signature('A53XCGBgBJjVSQPZksHVDqnbJekSopbzYvD8b7NwKvQ7AGzUcEQZxYhMMXwT9AqhKzpfpzWW1PBAhtgRwTB2pXM')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1795792817000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal('0.000123926'),
        location_label=(user_address := solana_accounts[0]),
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=(tip_amount := FVal('0.0002')),
        location_label=user_address,
        notes=f'Send {tip_amount} SOL to HCg8X7XZXWibg9rS4oBXsYdp7cwnewX4B9ZyxwRD3oqR',
        address=SolanaAddress('HCg8X7XZXWibg9rS4oBXsYdp7cwnewX4B9ZyxwRD3oqR'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:9TKbd3VFaMSXsEAicD9JVQWpWwAoLi4fSgWmZL2cpump'),
        amount=(spend_amount := FVal('23207.514322')),
        location_label=user_address,
        notes=f'Swap {spend_amount} Snowball in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=4,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_SOL,
        amount=(receive_amount := FVal('0.197379733')),
        location_label=user_address,
        notes=f'Receive {receive_amount} SOL as the result of a swap in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=5,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=(fee_amount := FVal('0.000986898')),
        location_label=user_address,
        notes=f'Spend {fee_amount} SOL as OKX swap fee',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['5aS8CKfB5XUhFH2e59ukh63Ykt6hv4TTDS5dvAuUgPjs']])
def test_swap_enhanced2_token_to_sol_router_closed_wsol(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Swap token -> SOL via OKX Enhanced2 with charge fee and router-closed WSOL rent refund."""
    signature = deserialize_tx_signature('2pyEDCPqrhRoqmDQphxaHbZuUhAFSTMLFumqnT6JiX2j369NTqdpGUKyNU6Ga2diU4p3jFN4R7xcAqTjvHTsQ1Vs')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1795792362000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal('0.000005015'),
        location_label=(user_address := solana_accounts[0]),
        counterparty=CPT_GAS,
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:ukHH6c7mMyiWCf1b9pnWe25TSpkDDt3H5pQZgZ74J82'),
        amount=(spend_amount := FVal('3')),
        location_label=user_address,
        notes=f'Swap {spend_amount} BOME in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_SOL,
        amount=(receive_amount := FVal('0.000019824')),
        location_label=user_address,
        notes=f'Receive {receive_amount} SOL as the result of a swap in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['Gj6BFXmfV8WLYUKDwj3PaZzRSCuzqfr5NiKNRSs46rGG']])
def test_swap_enhanced2_token_to_token(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Swap token -> token via OKX Enhanced2 (with source & destination fee slots)."""
    signature = deserialize_tx_signature('2kGoCWyXUCm6gvNARHJ4Z5jp72e6yVbsLduCVrucuM9J3RZWLqtPDUCQDHjs8JmQoNHVsRgZUgTWLSxZMnxmQQDP')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1795792810000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal('0.000030503'),
        location_label=(user_address := solana_accounts[0]),
        counterparty=CPT_GAS,
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=(spend_amount := FVal('1')),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    ), SolanaSwapEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('solana/token:MNDEFzGvMt87ueuHvVU9VcTqsAP5b3fTGPsHuuPA5ey'),
        amount=(receive_amount := FVal('51.584773104')),
        location_label=user_address,
        notes=f'Receive {receive_amount} MNDE as the result of a swap in OKX',
        counterparty=CPT_OKX,
        address=SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn'),
    )]


def _make_cpi_payload(
        length: int,
        direction: int = 1,
        amounts: dict[int, int] | None = None,
        source_mint: SolanaAddress | None = None,
        destination_mint: SolanaAddress | None = None,
) -> bytes:
    payload = bytearray(length)
    if source_mint is not None and length >= 40:
        payload[8:40] = bytes(deserialize_solana_pubkey(source_mint))
    if destination_mint is not None and length >= 72:
        payload[40:72] = bytes(deserialize_solana_pubkey(destination_mint))
    if length > 160:
        payload[160] = direction
    if amounts is not None:
        for offset, amount in amounts.items():
            payload[offset:offset + 8] = amount.to_bytes(8, byteorder='little')
    return bytes(payload)


def test_parse_cpi_event_fees(caplog: pytest.LogCaptureFixture) -> None:
    """Verify OKX CPI fee extraction across fee layouts and truncated payload warnings."""
    source_mint = SolanaAddress('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
    destination_mint = SolanaAddress('So11111111111111111111111111111111111111112')
    signature = deserialize_tx_signature(
        '7weJDgQqqkjTLxEAPRs2c247KTkjMMsXAspWwhLostyZmx74ZhSGHCkmg2jDagDH2gJxRB2BZsn3QHD8CFr2At3',
    )

    assert _parse_cpi_event_fees(
        event_discriminator=SWAP_CPI_EVENT2_DISCRIMINATOR,
        payload=_make_cpi_payload(160),
        source_mint=source_mint,
        destination_mint=destination_mint,
        tx_signature=signature,
    ) == []

    # SwapWithFees2 / SwapWithFees: direction=1 uses source_mint for slots 1 & 2
    for disc in (SWAP_WITH_FEES_CPI_EVENT2_DISCRIMINATOR, SWAP_WITH_FEES_CPI_EVENT_DISCRIMINATOR):
        payload = _make_cpi_payload(
            length=288,
            direction=1,
            amounts={165: 100, 207: 0, 248: 250},
        )
        assert _parse_cpi_event_fees(
            event_discriminator=disc,
            payload=payload,
            source_mint=source_mint,
            destination_mint=destination_mint,
            tx_signature=signature,
        ) == [(source_mint, 100), (destination_mint, 250)]

    # Enhanced2: direction=0 -> destination_mint for all slots including charge_amount at 290:298
    enhanced_payload = _make_cpi_payload(
        length=330,
        direction=0,
        amounts={165: 161, 207: 0, 248: 2, 290: 1},
    )
    assert _parse_cpi_event_fees(
        event_discriminator=SWAP_WITH_FEES_CPI_EVENT_ENHANCED2_DISCRIMINATOR,
        payload=enhanced_payload,
        source_mint=source_mint,
        destination_mint=destination_mint,
        tx_signature=signature,
    ) == [
        (destination_mint, 161),
        (destination_mint, 2),
        (destination_mint, 1),
    ]

    # ToB v2 with trim_amount at 296:304 (destination_mint) and ToC v2
    tob_payload = _make_cpi_payload(
        length=336,
        direction=1,
        amounts={169: 11, 213: 22, 255: 0, 296: 33},
    )
    assert _parse_cpi_event_fees(
        event_discriminator=SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR,
        payload=tob_payload,
        source_mint=source_mint,
        destination_mint=destination_mint,
        tx_signature=signature,
    ) == [
        (source_mint, 11),
        (source_mint, 22),
        (destination_mint, 33),
    ]
    toc_payload = _make_cpi_payload(
        length=295,
        direction=0,
        amounts={169: 5, 213: 0, 255: 9},
    )
    assert _parse_cpi_event_fees(
        event_discriminator=SWAP_TOC_V2_CPI_EVENT2_DISCRIMINATOR,
        payload=toc_payload,
        source_mint=source_mint,
        destination_mint=destination_mint,
        tx_signature=signature,
    ) == [(destination_mint, 5), (destination_mint, 9)]

    # Truncated payloads log warnings and return whatever valid slots exist
    caplog.clear()
    assert _parse_cpi_event_fees(
        event_discriminator=SWAP_WITH_FEES_CPI_EVENT2_DISCRIMINATOR,
        payload=_make_cpi_payload(287),
        source_mint=source_mint,
        destination_mint=destination_mint,
        tx_signature=signature,
    ) == []
    assert _parse_cpi_event_fees(
        event_discriminator=SWAP_WITH_FEES_CPI_EVENT_ENHANCED2_DISCRIMINATOR,
        payload=_make_cpi_payload(288, direction=1, amounts={165: 10}),
        source_mint=source_mint,
        destination_mint=destination_mint,
        tx_signature=signature,
    ) == [(source_mint, 10)]
    assert _parse_cpi_event_fees(
        event_discriminator=SWAP_TOC_V2_CPI_EVENT2_DISCRIMINATOR,
        payload=_make_cpi_payload(294),
        source_mint=source_mint,
        destination_mint=destination_mint,
        tx_signature=signature,
    ) == []
    assert _parse_cpi_event_fees(
        event_discriminator=SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR,
        payload=_make_cpi_payload(295, direction=1, amounts={169: 7}),
        source_mint=source_mint,
        destination_mint=destination_mint,
        tx_signature=signature,
    ) == [(source_mint, 7)]
    assert len(caplog.records) == 4
    assert all(record.levelname == 'WARNING' for record in caplog.records)


@pytest.mark.parametrize('solana_accounts', [['399WCXP1i2V2VM5DvCz1U5jN8jE4U8cuor9W7h8ri3Wu']])
def test_build_remaining_fees_handles_not_spl_conformant_and_caches_tokens(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
        caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify _build_remaining_fees catches NotSPLConformant, caches mints, and skips WSOL RPC."""
    base_tools = SolanaDecoderTools(
        database=solana_inquirer.database,
        node_inquirer=solana_inquirer,
    )
    decoder = OkxDecoder(
        node_inquirer=solana_inquirer,
        base_tools=base_tools,
        msg_aggregator=MessagesAggregator(),
    )
    bad_mint = SolanaAddress('4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R')
    usdc_mint = SolanaAddress('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
    wsol_mint = SolanaAddress('So11111111111111111111111111111111111111112')
    usdc_token = Asset(f'solana/token:{usdc_mint}').resolve_to_solana_token()
    signature = deserialize_tx_signature(
        '7weJDgQqqkjTLxEAPRs2c247KTkjMMsXAspWwhLostyZmx74ZhSGHCkmg2jDagDH2gJxRB2BZsn3QHD8CFr2At3',
    )

    with patch.object(
        base_tools,
        'get_or_create_solana_token',
        side_effect=NotSPLConformant('missing mint'),
    ) as mock_get_token:
        fees = decoder._build_remaining_fees(
            event_discriminator=SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR,
            payload=_make_cpi_payload(336, direction=1, amounts={169: 10, 213: 20, 296: 500}),
            source_mint=bad_mint,
            destination_mint=wsol_mint,
            tx_signature=signature,
        )

    # bad_mint fails once and is not retried for slot 2; WSOL slot 3 does not hit get_or_create
    assert mock_get_token.call_count == 1
    assert fees == [({A_WSOL, A_SOL}, FVal('0.0000005'))]
    assert 'Failed to load OKX swap fee SPL token' in caplog.text

    with patch.object(
        base_tools,
        'get_or_create_solana_token',
        return_value=usdc_token,
    ) as mock_get_token:
        cached_fees = decoder._build_remaining_fees(
            event_discriminator=SWAP_TOB_V2_CPI_EVENT2_DISCRIMINATOR,
            payload=_make_cpi_payload(336, direction=1, amounts={169: 1_000_000, 213: 2_000_000}),
            source_mint=usdc_mint,
            destination_mint=wsol_mint,
            tx_signature=signature,
        )

    assert mock_get_token.call_count == 1
    assert cached_fees == [
        ({usdc_token}, FVal('1')),
        ({usdc_token}, FVal('2')),
    ]


@pytest.mark.parametrize('solana_accounts', [['DpfNj5tD8Y2jB32ru2t4p43aXcHcBrf97i9HazLuWXwu']])
def test_decode_swap_preserves_unmatched_rent_and_post_route_funding(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Verify 2.3 edge cases: unmatched rent SPEND, missing SOL receive, and post-route funding."""
    user_address = solana_accounts[0]
    wsol_ata = SolanaAddress('79nk75aGZAWWKSYGvhyMvHxoa3yrb6hoVQ7VpZRGTK1E')
    source_ata = SolanaAddress('BDZoZhLH2AFSb32xN9WvCd8bDWJxivzd5QEGPip3puCp')
    intermediary = SolanaAddress('ARu4n5mFdZogZAravu7CcizaojWnS6oqka37gdLT5SZn')
    usdc_mint = SolanaAddress('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
    wsol_mint = SolanaAddress('So11111111111111111111111111111111111111112')
    usdc_asset = Asset(f'solana/token:{usdc_mint}')
    signature = deserialize_tx_signature(
        '2W2VsEDBum2QuaoFdFGutcyvCogo5ZEVTzeoyFx2i6fqitr8o418asTQ5fUkyqkN1hGASCovEzWWuRcLV8fV2Zr6',
    )
    ts_sec = Timestamp(1795790438)
    ts_ms = ts_sec_to_ms(ts_sec)
    payload = _make_cpi_payload(
        length=160,
        amounts={152: 1_000_000},
        source_mint=usdc_mint,
        destination_mint=wsol_mint,
    )
    cpi_data = ANCHOR_EVENT_DISCRIMINATOR + SWAP_CPI_EVENT2_DISCRIMINATOR + payload

    # Case 1: Router-closed WSOL ATA where SOL receive does not match expected_sol + rent
    base_tools = SolanaDecoderTools(
        database=solana_inquirer.database,
        node_inquirer=solana_inquirer,
    )
    decoder = OkxDecoder(
        node_inquirer=solana_inquirer,
        base_tools=base_tools,
        msg_aggregator=MessagesAggregator(),
    )
    rent_ix = SolanaInstruction(
        execution_index=1,
        parent_execution_index=None,
        program_id=SYSTEM_PROGRAM,
        data=b'',
        accounts=[user_address, wsol_ata],
    )
    route_ix = SolanaInstruction(
        execution_index=2,
        parent_execution_index=None,
        program_id=OKX_DEX_ROUTER_V2_PROGRAM,
        data=b'',
        accounts=[user_address, source_ata, wsol_ata],
    )
    spend_ix = SolanaInstruction(
        execution_index=3,
        parent_execution_index=2,
        program_id=SPL_TOKEN_PROGRAM,
        data=b'',
        accounts=[source_ata, intermediary],
    )
    wsol_receive_ix = SolanaInstruction(
        execution_index=4,
        parent_execution_index=2,
        program_id=SPL_TOKEN_PROGRAM,
        data=b'',
        accounts=[intermediary, wsol_ata],
    )
    close_ix = SolanaInstruction(
        execution_index=5,
        parent_execution_index=2,
        program_id=SPL_TOKEN_PROGRAM,
        data=SPL_TOKEN_CLOSE_ACCOUNT_DISCRIMINATOR,
        accounts=[wsol_ata, intermediary, user_address],
    )
    sol_receive_ix = SolanaInstruction(
        execution_index=6,
        parent_execution_index=2,
        program_id=SYSTEM_PROGRAM,
        data=b'',
        accounts=[intermediary, user_address],
    )
    cpi_ix = SolanaInstruction(
        execution_index=7,
        parent_execution_index=2,
        program_id=OKX_DEX_ROUTER_V2_PROGRAM,
        data=cpi_data,
        accounts=[],
    )
    tx = SolanaTransaction(
        fee=5000,
        slot=1,
        success=True,
        signature=signature,
        block_time=ts_sec,
        account_keys=[user_address],
        instructions=[
            rent_ix,
            route_ix,
            spend_ix,
            wsol_receive_ix,
            close_ix,
            sol_receive_ix,
            cpi_ix,
        ],
    )
    rent_event = base_tools.make_event_from_instruction(
        instruction=rent_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=FVal('0.00203928'),
        location_label=user_address,
        address=wsol_ata,
    )
    spend_event = base_tools.make_event_from_instruction(
        instruction=spend_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=usdc_asset,
        amount=FVal('10'),
        location_label=user_address,
        address=intermediary,
    )
    wsol_receive_event = base_tools.make_event_from_instruction(
        instruction=wsol_receive_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_WSOL,
        amount=FVal('0.001'),
        location_label=user_address,
        address=intermediary,
    )
    sol_receive_event = base_tools.make_event_from_instruction(
        instruction=sol_receive_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=FVal('0.005'),
        location_label=user_address,
        address=intermediary,
    )
    events = [rent_event, spend_event, wsol_receive_event, sol_receive_event]
    decoder.decode_swap(SolanaDecoderContext(
        instruction=cpi_ix,
        transaction=tx,
        decoded_events=events,
        ata_data={wsol_ata: (user_address, wsol_mint)},
    ))
    assert events == [
        rent_event,
        spend_event,
        sol_receive_event,
    ]
    assert sol_receive_event.amount == FVal('0.005')
    assert sol_receive_event.event_type == HistoryEventType.TRADE

    # Case 2: Router-closed WSOL ATA without native SOL receive keeps & converts WSOL receive
    base_tools_2 = SolanaDecoderTools(
        database=solana_inquirer.database,
        node_inquirer=solana_inquirer,
    )
    decoder_2 = OkxDecoder(
        node_inquirer=solana_inquirer,
        base_tools=base_tools_2,
        msg_aggregator=MessagesAggregator(),
    )
    tx_no_sol_recv = SolanaTransaction(
        fee=5000,
        slot=1,
        success=True,
        signature=signature,
        block_time=ts_sec,
        account_keys=[user_address],
        instructions=[rent_ix, route_ix, spend_ix, wsol_receive_ix, close_ix, cpi_ix],
    )
    rent_event_2 = base_tools_2.make_event_from_instruction(
        instruction=rent_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=FVal('0.00203928'),
        location_label=user_address,
        address=wsol_ata,
    )
    spend_event_2 = base_tools_2.make_event_from_instruction(
        instruction=spend_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=usdc_asset,
        amount=FVal('10'),
        location_label=user_address,
        address=intermediary,
    )
    wsol_receive_event_2 = base_tools_2.make_event_from_instruction(
        instruction=wsol_receive_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_WSOL,
        amount=FVal('0.001'),
        location_label=user_address,
        address=intermediary,
    )
    events_2 = [rent_event_2, spend_event_2, wsol_receive_event_2]
    decoder_2.decode_swap(SolanaDecoderContext(
        instruction=cpi_ix,
        transaction=tx_no_sol_recv,
        decoded_events=events_2,
        ata_data={wsol_ata: (user_address, wsol_mint)},
    ))
    assert events_2 == [rent_event_2, spend_event_2, wsol_receive_event_2]
    assert wsol_receive_event_2.asset == A_SOL
    assert wsol_receive_event_2.event_type == HistoryEventType.TRADE
    assert wsol_receive_event_2.timestamp == ts_ms

    # Case 3: Post-route SOL funding transfer to same WSOL ATA is not dropped
    base_tools_3 = SolanaDecoderTools(
        database=solana_inquirer.database,
        node_inquirer=solana_inquirer,
    )
    decoder_3 = OkxDecoder(
        node_inquirer=solana_inquirer,
        base_tools=base_tools_3,
        msg_aggregator=MessagesAggregator(),
    )
    sync_ix = SolanaInstruction(
        execution_index=1,
        parent_execution_index=None,
        program_id=SPL_TOKEN_PROGRAM,
        data=SPL_TOKEN_SYNC_NATIVE_DISCRIMINATOR,
        accounts=[wsol_ata],
    )
    pre_fund_ix = SolanaInstruction(
        execution_index=0,
        parent_execution_index=None,
        program_id=SYSTEM_PROGRAM,
        data=b'',
        accounts=[user_address, wsol_ata],
    )
    post_fund_ix = SolanaInstruction(
        execution_index=9,
        parent_execution_index=None,
        program_id=SYSTEM_PROGRAM,
        data=b'',
        accounts=[user_address, wsol_ata],
    )
    wsol_spend_ix = SolanaInstruction(
        execution_index=3,
        parent_execution_index=2,
        program_id=SPL_TOKEN_PROGRAM,
        data=b'',
        accounts=[wsol_ata, intermediary],
    )
    usdc_receive_ix = SolanaInstruction(
        execution_index=4,
        parent_execution_index=2,
        program_id=SPL_TOKEN_PROGRAM,
        data=b'',
        accounts=[intermediary, source_ata],
    )
    sol_to_usdc_payload = _make_cpi_payload(
        length=160,
        amounts={152: 10_000_000},
        source_mint=wsol_mint,
        destination_mint=usdc_mint,
    )
    sol_to_usdc_cpi_ix = SolanaInstruction(
        execution_index=7,
        parent_execution_index=2,
        program_id=OKX_DEX_ROUTER_V2_PROGRAM,
        data=ANCHOR_EVENT_DISCRIMINATOR + SWAP_CPI_EVENT2_DISCRIMINATOR + sol_to_usdc_payload,
        accounts=[],
    )
    tx_post_fund = SolanaTransaction(
        fee=5000,
        slot=1,
        success=True,
        signature=signature,
        block_time=ts_sec,
        account_keys=[user_address],
        instructions=[
            pre_fund_ix,
            sync_ix,
            route_ix,
            wsol_spend_ix,
            usdc_receive_ix,
            sol_to_usdc_cpi_ix,
            post_fund_ix,
        ],
    )
    pre_fund_event = base_tools_3.make_event_from_instruction(
        instruction=pre_fund_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=FVal('0.5'),
        location_label=user_address,
        address=wsol_ata,
    )
    wsol_spend_event = base_tools_3.make_event_from_instruction(
        instruction=wsol_spend_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_WSOL,
        amount=FVal('0.5'),
        location_label=user_address,
        address=intermediary,
    )
    usdc_receive_event = base_tools_3.make_event_from_instruction(
        instruction=usdc_receive_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=usdc_asset,
        amount=FVal('10'),
        location_label=user_address,
        address=intermediary,
    )
    post_fund_event = base_tools_3.make_event_from_instruction(
        instruction=post_fund_ix,
        tx_ref=signature,
        timestamp=ts_sec,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=FVal('0.25'),
        location_label=user_address,
        address=wsol_ata,
    )
    events_3 = [pre_fund_event, wsol_spend_event, usdc_receive_event, post_fund_event]
    decoder_3.decode_swap(SolanaDecoderContext(
        instruction=sol_to_usdc_cpi_ix,
        transaction=tx_post_fund,
        decoded_events=events_3,
        ata_data={wsol_ata: (user_address, wsol_mint)},
    ))
    assert events_3 == [post_fund_event, wsol_spend_event, usdc_receive_event]
