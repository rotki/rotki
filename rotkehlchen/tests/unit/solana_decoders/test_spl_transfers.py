from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.constants import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.constants import A_SOL
from rotkehlchen.tests.utils.solana import get_decoded_events_of_solana_tx
from rotkehlchen.types import SolanaAddress, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['54r6W445JsjDf5UGzmVtcczsPpgg3B3J16USuNcu1EY']])
def test_spl_token_transfer(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    events = get_decoded_events_of_solana_tx(
        solana_inquirer=solana_inquirer,
        signature=(signature := deserialize_tx_signature('28f8jFzCX3D1dJ5sZSABgVmrziAQu3hPeERjRoKMJwvQGrahxDfSRARpgX4rBeGcYvGSMu77QPoEqYdyYTzx9TY7')),  # noqa: E501
    )
    assert events == [SolanaEvent(
        signature=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1735930769000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000015'),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        signature=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),
        amount=FVal(spend_amount := '29.69787'),
        location_label=user,
        notes=f'Send {spend_amount} USDC to GabwTHe1P9wLKCqqBNBnAPgD71K8j8Dp4Uk4L6EyFUnK',
        address=SolanaAddress('GabwTHe1P9wLKCqqBNBnAPgD71K8j8Dp4Uk4L6EyFUnK'),
    )]
    with solana_inquirer.database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT * FROM key_value_cache').fetchall() == [
            ('solana_token_account_BKHLvZxmSGUJRMX9WPPLFTQvRTktctpL6At2yWnxbLtV', 'GabwTHe1P9wLKCqqBNBnAPgD71K8j8Dp4Uk4L6EyFUnK,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),  # noqa: E501
            ('solana_token_account_EHF3dReNcLKmop3j2EhZuABtq7hnEzyS6VFBqsTsz5Mt', '54r6W445JsjDf5UGzmVtcczsPpgg3B3J16USuNcu1EY,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'),  # noqa: E501
        ]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['5Sp1e78jLb9b4B8FMFEGobzQCc9kW23tydFNaeGsNJSt']])
def test_token2022_transfer(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    events = get_decoded_events_of_solana_tx(
        solana_inquirer=solana_inquirer,
        signature=(signature := deserialize_tx_signature('3oR9ryME5VTS2qWZ25AhAwKWYLsYMLigCcFKRh6DiyFGtC7m7e17mBihB84XzL1EptM6mCjjyRp6uovHfHgcZrMA')),  # noqa: E501
    )
    assert events == [SolanaEvent(
        signature=signature,
        sequence_index=0,
        timestamp=TimestampMS(1759754588000),
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('solana/token:7atgF8KQo4wJrD5ATGX7t1V2zVvykPJbFfNeVf1icFv1'),
        amount=FVal(receive_amount := '3840000'),
        location_label=solana_accounts[0],
        notes=f'Receive {receive_amount} CWIF from 6HbSn7QQraiNXW5p4M7Sp48qdcxvCSsqwuJvrNNTMayF',
        address=SolanaAddress('6HbSn7QQraiNXW5p4M7Sp48qdcxvCSsqwuJvrNNTMayF'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['9rJ4QzDLYm5VARnuWcMFMzB4Nr1hKprGQWb8LTfsU6Q2']])
def test_nft_transfer(
        solana_inquirer: 'SolanaInquirer',
        solana_accounts: list[SolanaAddress],
) -> None:
    events = get_decoded_events_of_solana_tx(
        solana_inquirer=solana_inquirer,
        signature=(signature := deserialize_tx_signature('5ChR6nE7SssBX6FrMJCXMb3Z93uQFWtET15RLhxCg1GCWbgaQMAXPH4C6SqrannjvsCeeR7Kq9qNPas3Ehsh76Pm')),  # noqa: E501
    )
    assert events == [SolanaEvent(
        signature=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1759756642000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000080001'),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        signature=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('solana/nft:HFQ4rcivJ4PnY5EWDFJigoDACNEEUfFP2eexTKCJ4VzF'),
        amount=(spend_amount := ONE),
        location_label=user,
        notes=f'Send {spend_amount} ReGuLaTeD to 54r6W445JsjDf5UGzmVtcczsPpgg3B3J16USuNcu1EY',
        address=SolanaAddress('54r6W445JsjDf5UGzmVtcczsPpgg3B3J16USuNcu1EY'),
    )]
