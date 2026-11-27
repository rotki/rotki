from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.solana.modules.okx.constants import CPT_OKX
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.solana_swap import SolanaSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.constants import A_SOL
from rotkehlchen.tests.utils.solana import get_decoded_events_of_solana_tx
from rotkehlchen.types import SolanaAddress, TimestampMS

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
