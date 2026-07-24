from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.solana.modules.stake.constants import CPT_SOLANA_STAKE
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
from rotkehlchen.tests.utils.solana import get_decoded_events_of_solana_tx
from rotkehlchen.types import SolanaAddress, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['HuUpZe8dH1ttFoEtwpGjatcaoQrJ7PpeSUpBZH1Hh2G3']])
def test_stake_creation_and_delegation(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """A transaction creating a stake account via createAccountWithSeed, initializing
    it and delegating it to a validator in one go."""
    signature = deserialize_tx_signature('2BhH7DcQJMPBZfLQDjLCSqhygzzwXiviGmLaLaojNUm3StihhLZaD1A7TXdfm6V8vR76VVsXvXmqTdVy2KPwYJau')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784920595000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000017733'),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_SOL,
        amount=FVal(staked_amount := '1.98528288'),
        location_label=user,
        notes=f'Stake {staked_amount} SOL to validator EXhYxF25PJEHb3v5G1HY8Jn8Jm7bRjJtaxEghGrUuhQw',  # noqa: E501
        counterparty=CPT_SOLANA_STAKE,
        address=SolanaAddress('HhJKd8G1gbvhPEiC4Aa3ZH9p4E9yze3ziYYq5A2ZLKjA'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['9TT3YkWkLxU1DxJSsUHvmtbWtFJd9E7jkvxz1nBRq172']])
def test_stake_deactivation(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    signature = deserialize_tx_signature('5jgnWXmTHWwpvFnCkciye7XhTCdRqDduUNUoSSRWoMh5bGxniFstMUAV2err7k6D3Dw59ocFijb8G1xNBv11nHsf')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784920737000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000005'),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=ZERO,
        location_label=user,
        notes=f'Deactivate stake account {SolanaAddress("7kf6dqRzRTAACPd7dDDrYVFMHSGgZzJY2tZVS3ZfuKMw")}',  # noqa: E501
        counterparty=CPT_SOLANA_STAKE,
        address=SolanaAddress('7kf6dqRzRTAACPd7dDDrYVFMHSGgZzJY2tZVS3ZfuKMw'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['CQ3gvU4vKvFGevho9TkG1FEdTCHQKiLC1AcWLwPv4ek4']])
def test_stake_authorize(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """A stake account sale through a marketplace: both the staker and the withdrawer
    authorities are handed to the buyer and the seller receives the payment."""
    signature = deserialize_tx_signature('5R9M9ZviLoQ378G38zUi4dn6xQSSP51vvLEw2vzZjki1y6FzueuKNiDc5xaFxDh82dSzWw85eaQRVT93XzCqeQyw')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    stake_account, new_authority = SolanaAddress('9rJXVkHewWzuBh7wPErqhuwy3H5YN9znNVgWJDoEGhnD'), SolanaAddress('5PxxoU93A4KLr23rXvYrYMFZDAw5DY8XZiyX6NsW7Hkk')  # noqa: E501
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784922230000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.00081'),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=FVal(received_amount := '0.022336188'),
        location_label=user,
        notes=f'Receive {received_amount} SOL from {new_authority}',
        address=new_authority,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=ZERO,
        location_label=user,
        notes=f'Set the staker of stake account {stake_account} to {new_authority}',
        counterparty=CPT_SOLANA_STAKE,
        address=stake_account,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=3,
        timestamp=timestamp,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=ZERO,
        location_label=user,
        notes=f'Set the withdrawer of stake account {stake_account} to {new_authority}',
        counterparty=CPT_SOLANA_STAKE,
        address=stake_account,
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['BG1MAyPvJsPP3BoSwkbDzTah2zW7NGu1VpteKi9Utqxo']])
def test_stake_split(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Splitting part of a stake account into a new one, whose rent-exempt reserve is
    funded via createAccountWithSeed in the same transaction."""
    signature = deserialize_tx_signature('5s3aSkoBkoc9xQW83vepG2zMhz2YA75NLyqdYWqDHWnZrBNYawnifZGr4Ui3jS6zWj3z7FGfpcWQLa5kAFTTrFC8')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    source_account, destination_account = SolanaAddress('E6Qz4Fkxukhxm6ubGdLihCnUUhmYLa12WQj2NaykFgt1'), SolanaAddress('4dyK7o1KewvaH7b6inweQxMvULCExAgXm9SmMqWreFzb')  # noqa: E501
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784921316000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000013445'),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_SOL,
        amount=FVal(rent_amount := '0.00228288'),
        location_label=user,
        notes=f'Deposit {rent_amount} SOL into stake account {destination_account}',
        counterparty=CPT_SOLANA_STAKE,
        address=destination_account,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=2,
        timestamp=timestamp,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=FVal(split_amount := '30'),
        location_label=user,
        notes=f'Split {split_amount} SOL from stake account {source_account} into stake account {destination_account}',  # noqa: E501
        counterparty=CPT_SOLANA_STAKE,
        address=destination_account,
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['36kaqVpcbSSJ55rP48uGQWtQs3eNaa6SbX8qbhPxHGJf']])
def test_stake_merge(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    signature = deserialize_tx_signature('k78n39QMtVDUFHDFGgyZRvHqxArVVhqP7ZhD4RjrYyjaCvNyXPwnWNg6ofYXMpzgXDAVAw7ghnktjduSLhqqw8V')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784921283000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.000005'),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_SOL,
        amount=ZERO,
        location_label=user,
        notes='Merge stake account 5adkBxExn2nPL7PVD1snpvjvaY7BwvtFtpxL6QmCvdUi into stake account 2R9YrpeXNXyne2gPrC3tKwJosScsuausNTmZ16LYfaFD',  # noqa: E501
        counterparty=CPT_SOLANA_STAKE,
        address=SolanaAddress('2R9YrpeXNXyne2gPrC3tKwJosScsuausNTmZ16LYfaFD'),
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('solana_accounts', [['npN8zCyQGPaAFNk95zJs2SAQ8GSjGcfhRDo6eiN57a9']])
def test_stake_withdrawal(
        solana_inquirer: SolanaInquirer,
        solana_accounts: list[SolanaAddress],
) -> None:
    """Withdraw from a deactivated stake account back to the withdraw authority,
    in a transaction that uses a durable nonce before the withdraw instruction."""
    signature = deserialize_tx_signature('4j2wEyeo2gFrV4xUBVM5YukW1ZW2976osDofBJfUUTLbHKEkiTo7WtCdmLQa33Eo45xCs4M3XcZeSSMST2NtPrhM')  # noqa: E501
    events = get_decoded_events_of_solana_tx(solana_inquirer=solana_inquirer, signature=signature)
    assert events == [SolanaEvent(
        tx_ref=signature,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1784920793000)),
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_SOL,
        amount=FVal(fee_amount := '0.00001'),
        location_label=(user := solana_accounts[0]),
        notes=f'Spend {fee_amount} SOL as transaction fee',
        counterparty=CPT_GAS,
    ), SolanaEvent(
        tx_ref=signature,
        sequence_index=1,
        timestamp=timestamp,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_SOL,
        amount=FVal(unstaked_amount := '92.204933944'),
        location_label=user,
        notes=f'Unstake {unstaked_amount} SOL from stake account fqR3jkizg36JsGgfcSB6ZiRQWGMYdNW3bPZ4UtG44VC',  # noqa: E501
        counterparty=CPT_SOLANA_STAKE,
        address=SolanaAddress('fqR3jkizg36JsGgfcSB6ZiRQWGMYdNW3bPZ4UtG44VC'),
    )]
