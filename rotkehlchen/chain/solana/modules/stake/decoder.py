import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.solana.decoding.constants import (
    NATIVE_TRANSFER_DISCRIMINATOR,
    SYSTEM_PROGRAM,
)
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import (
    DEFAULT_SOLANA_DECODING_OUTPUT,
    SolanaDecodingOutput,
)
from rotkehlchen.chain.solana.modules.stake.constants import (
    CPT_SOLANA_STAKE,
    STAKE_PROGRAM,
    SYSTEM_CREATE_ACCOUNT_DISCRIMINATOR,
    SYSTEM_CREATE_ACCOUNT_WITH_SEED_DISCRIMINATOR,
    StakeInstructionTag,
)
from rotkehlchen.chain.solana.utils import lamports_to_sol
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_solana_address

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.chain.solana.decoding.structures import SolanaDecoderContext
    from rotkehlchen.chain.solana.types import SolanaInstruction
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.solana_event import SolanaEvent
    from rotkehlchen.types import SolanaAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class StakeDecoder(SolanaDecoderInterface):
    """Decoder for the native Solana Stake program.

    Covers the full user-signed instruction set: funding + delegation, deactivation,
    withdrawal, splitting, merging, moving stake/lamports between accounts, authority
    changes and lockup updates. GetMinimumDelegation carries no user action, and
    DeactivateDelinquent/Redelegate are permissionless/retired instructions that do
    not appear in a tracked user's own transactions, so they produce no events.
    """

    def _check_min_accounts(
            self,
            context: SolanaDecoderContext,
            tag: StakeInstructionTag,
            minimum: int,
    ) -> bool:
        """Returns True if the instruction has at least the expected number of accounts,
        logging an error otherwise."""
        if len(accounts := context.instruction.accounts) < minimum:
            log.error(
                'Solana stake %s instruction in %s has %d accounts. Expected at least %d. Skipping',  # noqa: E501
                tag.name,
                context.transaction.signature,
                len(accounts),
                minimum,
            )
            return False

        return True

    @staticmethod
    def _get_funding_amount(
            instruction: SolanaInstruction,
            stake_account: SolanaAddress,
    ) -> tuple[FVal, SolanaAddress] | None:
        """Extract the funding amount and funder of the given stake account from a system
        program instruction, if it is a transfer/create targeting that account.
        Returns the amount in SOL and the funder address, or None if it doesn't match.
        """
        if (
            instruction.program_id != SYSTEM_PROGRAM or
            len(instruction.accounts) < 2 or
            instruction.accounts[1] != stake_account
        ):
            return None

        if (discriminator := instruction.data[:4]) in (
            SYSTEM_CREATE_ACCOUNT_DISCRIMINATOR,
            NATIVE_TRANSFER_DISCRIMINATOR,
        ):  # for both, a u64 lamports amount follows the discriminator
            raw_amount = int.from_bytes(instruction.data[4:12], byteorder='little')
        elif discriminator == SYSTEM_CREATE_ACCOUNT_WITH_SEED_DISCRIMINATOR:
            # layout: discriminator (4) + base pubkey (32) + seed string (8-byte length
            # prefix + bytes) + lamports (8) + space (8) + owner pubkey (32)
            seed_len = int.from_bytes(instruction.data[36:44], byteorder='little')
            raw_amount = int.from_bytes(
                instruction.data[44 + seed_len:52 + seed_len],
                byteorder='little',
            )
        else:
            return None

        return lamports_to_sol(raw_amount), instruction.accounts[0]

    def _maybe_decode_funding_deposit(
            self,
            context: SolanaDecoderContext,
            stake_account: SolanaAddress,
            notes_fn: Callable[[FVal], str],
    ) -> tuple[SolanaEvent, bool] | None:
        """Decode the system program instruction funding the given stake account in this
        transaction into a staking deposit event, transforming an already-decoded plain
        transfer if that is how the account was funded. Returns the event and whether it
        is newly created (a transformed transfer is already in the decoded events), or
        None when no funding by a tracked address is found.
        """
        for event in context.decoded_events:  # a plain transfer funding the stake account has already been decoded as a spend  # noqa: E501
            if (
                event.address == stake_account and
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_SOL
            ):
                event.event_type = HistoryEventType.STAKING
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_SOLANA_STAKE
                event.notes = notes_fn(event.amount)
                return event, False

        for instruction in context.transaction.instructions:
            if (funding_result := self._get_funding_amount(
                instruction=instruction,
                stake_account=stake_account,
            )) is not None:
                amount, funder = funding_result
                if not self.base.is_tracked(funder):
                    return None

                return self.base.make_event_from_instruction(
                    instruction=context.instruction,
                    tx_ref=context.transaction.signature,
                    timestamp=context.transaction.block_time,
                    event_type=HistoryEventType.STAKING,
                    event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                    asset=A_SOL,
                    amount=amount,
                    location_label=funder,
                    notes=notes_fn(amount),
                    counterparty=CPT_SOLANA_STAKE,
                    address=stake_account,
                ), True

        return None

    def _make_informational_event(
            self,
            context: SolanaDecoderContext,
            location_label: SolanaAddress,
            notes: str,
            address: SolanaAddress,
            amount: FVal | None = None,
    ) -> SolanaDecodingOutput:
        return SolanaDecodingOutput(events=[self.base.make_event_from_instruction(
            instruction=context.instruction,
            tx_ref=context.transaction.signature,
            timestamp=context.transaction.block_time,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_SOL,
            amount=amount if amount is not None else ZERO,
            location_label=location_label,
            notes=notes,
            counterparty=CPT_SOLANA_STAKE,
            address=address,
        )])

    def _decode_initialize(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode an Initialize/InitializeChecked instruction, creating a deposit event
        for the SOL funding the new stake account. When the account is also delegated in
        the same transaction the delegation decoding emits the deposit instead, with the
        validator in the notes."""
        stake_account = context.instruction.accounts[0]
        for instruction in context.transaction.instructions:
            if (
                instruction.program_id == STAKE_PROGRAM and
                int.from_bytes(instruction.data[:4], byteorder='little') == StakeInstructionTag.DELEGATE_STAKE and  # noqa: E501
                len(instruction.accounts) > 0 and
                instruction.accounts[0] == stake_account
            ):
                return DEFAULT_SOLANA_DECODING_OUTPUT

        if (deposit_result := self._maybe_decode_funding_deposit(
            context=context,
            stake_account=stake_account,
            notes_fn=lambda amount: f'Deposit {amount} SOL into stake account {stake_account}',
        )) is not None and deposit_result[1] is True:
            return SolanaDecodingOutput(events=[deposit_result[0]])

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def _decode_delegate(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode a DelegateStake instruction.

        The delegated amount is not part of the instruction, so it is taken from the
        system program instruction funding the stake account in the same transaction
        (create account with/without seed, or a plain transfer). A delegation of a
        stake account funded in an earlier transaction gets an informational event
        instead, since the staked amount is not knowable from this transaction alone.
        """
        if not self._check_min_accounts(context, StakeInstructionTag.DELEGATE_STAKE, 6):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        accounts = context.instruction.accounts
        stake_account, vote_account, stake_authority = accounts[0], accounts[1], accounts[5]
        if (deposit_result := self._maybe_decode_funding_deposit(
            context=context,
            stake_account=stake_account,
            notes_fn=lambda amount: f'Stake {amount} SOL to validator {vote_account}',
        )) is not None:
            deposit_event, is_new = deposit_result
            return SolanaDecodingOutput(events=[deposit_event]) if is_new else DEFAULT_SOLANA_DECODING_OUTPUT  # noqa: E501

        if not self.base.is_tracked(stake_authority):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        return self._make_informational_event(
            context=context,
            location_label=stake_authority,
            notes=f'Delegate stake account {stake_account} to validator {vote_account}',
            address=stake_account,
        )

    def _decode_authorize(
            self,
            context: SolanaDecoderContext,
            tag: StakeInstructionTag,
    ) -> SolanaDecodingOutput:
        """Decode the Authorize instruction family, changing the staker or withdrawer
        authority of a stake account. The new authority and the authority type come from
        the instruction data in the plain/seed variants and from the accounts in the
        checked variants."""
        accounts, data = context.instruction.accounts, context.instruction.data
        if tag == StakeInstructionTag.AUTHORIZE:
            if not self._check_min_accounts(context, tag, 3):
                return DEFAULT_SOLANA_DECODING_OUTPUT
            # data layout: discriminator (4) + new authority pubkey (32) + authority type (4)
            authority, new_authority = accounts[2], bytes_to_solana_address(data[4:36])
            authority_type = int.from_bytes(data[36:40], byteorder='little')
        elif tag == StakeInstructionTag.AUTHORIZE_WITH_SEED:
            if not self._check_min_accounts(context, tag, 2):
                return DEFAULT_SOLANA_DECODING_OUTPUT
            authority, new_authority = accounts[1], bytes_to_solana_address(data[4:36])
            authority_type = int.from_bytes(data[36:40], byteorder='little')
        else:  # AUTHORIZE_CHECKED or AUTHORIZE_CHECKED_WITH_SEED
            if not self._check_min_accounts(context, tag, 4):
                return DEFAULT_SOLANA_DECODING_OUTPUT
            authority = accounts[2] if tag == StakeInstructionTag.AUTHORIZE_CHECKED else accounts[1]  # noqa: E501
            new_authority = accounts[3]
            authority_type = int.from_bytes(data[4:8], byteorder='little')

        if authority_type not in (0, 1):
            log.error(
                'Solana stake %s instruction in %s has unknown authority type %d. Skipping',
                tag.name,
                context.transaction.signature,
                authority_type,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        stake_account = accounts[0]
        if self.base.is_tracked(authority):
            location_label = authority
        elif self.base.is_tracked(new_authority):
            location_label = new_authority
        else:
            return DEFAULT_SOLANA_DECODING_OUTPUT

        return self._make_informational_event(
            context=context,
            location_label=location_label,
            notes=f'Set the {"staker" if authority_type == 0 else "withdrawer"} of stake account {stake_account} to {new_authority}',  # noqa: E501
            address=stake_account,
        )

    def _decode_split(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode a Split instruction moving part of a stake account into a new one.
        The rent-exempt reserve funding the new account in the same transaction is
        decoded as a deposit, since that SOL also moves from the wallet into the
        stake account."""
        if not self._check_min_accounts(context, StakeInstructionTag.SPLIT, 3):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        accounts = context.instruction.accounts
        source_account, destination_account, authority = accounts[0], accounts[1], accounts[2]
        if not self.base.is_tracked(authority):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        events = []
        if (deposit_result := self._maybe_decode_funding_deposit(
            context=context,
            stake_account=destination_account,
            notes_fn=lambda amount: f'Deposit {amount} SOL into stake account {destination_account}',  # noqa: E501
        )) is not None and deposit_result[1] is True:
            events.append(deposit_result[0])

        amount = lamports_to_sol(int.from_bytes(context.instruction.data[4:12], byteorder='little'))  # noqa: E501
        split_output = self._make_informational_event(
            context=context,
            location_label=authority,
            notes=f'Split {amount} SOL from stake account {source_account} into stake account {destination_account}',  # noqa: E501
            address=destination_account,
            amount=amount,
        )
        return SolanaDecodingOutput(events=events + (split_output.events or []))

    def _decode_withdraw(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode a Withdraw instruction, returning SOL from a stake account."""
        if not self._check_min_accounts(context, StakeInstructionTag.WITHDRAW, 5):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        accounts = context.instruction.accounts
        stake_account, recipient = accounts[0], accounts[1]
        if not self.base.is_tracked(recipient):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        if (raw_amount := int.from_bytes(
            context.instruction.data[4:12],
            byteorder='little',
        )) == 0:
            return DEFAULT_SOLANA_DECODING_OUTPUT

        amount = lamports_to_sol(raw_amount)
        return SolanaDecodingOutput(events=[self.base.make_event_from_instruction(
            instruction=context.instruction,
            tx_ref=context.transaction.signature,
            timestamp=context.transaction.block_time,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_SOL,
            amount=amount,
            location_label=recipient,
            notes=f'Unstake {amount} SOL from stake account {stake_account}',
            counterparty=CPT_SOLANA_STAKE,
            address=stake_account,
        )])

    def _decode_deactivate(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode a Deactivate instruction. The stake becomes withdrawable after the
        cooldown, so this only marks the start of unstaking and moves no funds."""
        if not self._check_min_accounts(context, StakeInstructionTag.DEACTIVATE, 3):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        accounts = context.instruction.accounts
        stake_account, stake_authority = accounts[0], accounts[2]
        if not self.base.is_tracked(stake_authority):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        return self._make_informational_event(
            context=context,
            location_label=stake_authority,
            notes=f'Deactivate stake account {stake_account}',
            address=stake_account,
        )

    def _decode_set_lockup(
            self,
            context: SolanaDecoderContext,
            tag: StakeInstructionTag,
    ) -> SolanaDecodingOutput:
        if not self._check_min_accounts(context, tag, 2):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        accounts = context.instruction.accounts
        stake_account, authority = accounts[0], accounts[1]
        if not self.base.is_tracked(authority):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        return self._make_informational_event(
            context=context,
            location_label=authority,
            notes=f'Update the lockup of stake account {stake_account}',
            address=stake_account,
        )

    def _decode_merge(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        """Decode a Merge instruction combining two stake accounts. The merged amount is
        not part of the instruction data, so the event is purely informational."""
        if not self._check_min_accounts(context, StakeInstructionTag.MERGE, 5):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        accounts = context.instruction.accounts
        destination_account, source_account, authority = accounts[0], accounts[1], accounts[4]
        if not self.base.is_tracked(authority):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        return self._make_informational_event(
            context=context,
            location_label=authority,
            notes=f'Merge stake account {source_account} into stake account {destination_account}',
            address=destination_account,
        )

    def _decode_move(
            self,
            context: SolanaDecoderContext,
            tag: StakeInstructionTag,
    ) -> SolanaDecodingOutput:
        """Decode MoveStake/MoveLamports, shifting value between two stake accounts of
        the same authority."""
        if not self._check_min_accounts(context, tag, 3):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        accounts = context.instruction.accounts
        source_account, destination_account, authority = accounts[0], accounts[1], accounts[2]
        if not self.base.is_tracked(authority):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        amount = lamports_to_sol(int.from_bytes(context.instruction.data[4:12], byteorder='little'))  # noqa: E501
        subject = 'SOL of stake' if tag == StakeInstructionTag.MOVE_STAKE else 'SOL'
        return self._make_informational_event(
            context=context,
            location_label=authority,
            notes=f'Move {amount} {subject} from stake account {source_account} to stake account {destination_account}',  # noqa: E501
            address=destination_account,
            amount=amount,
        )

    def decode_stake_instruction(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        if len(context.instruction.data) < 4 or len(context.instruction.accounts) == 0:
            return DEFAULT_SOLANA_DECODING_OUTPUT

        try:
            tag = StakeInstructionTag(int.from_bytes(
                context.instruction.data[:4],
                byteorder='little',
            ))
        except ValueError:
            log.error(
                'Unknown solana stake program instruction tag in transaction %s. Skipping',
                context.transaction.signature,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        if tag in (StakeInstructionTag.INITIALIZE, StakeInstructionTag.INITIALIZE_CHECKED):
            return self._decode_initialize(context)
        if tag in (
            StakeInstructionTag.AUTHORIZE,
            StakeInstructionTag.AUTHORIZE_WITH_SEED,
            StakeInstructionTag.AUTHORIZE_CHECKED,
            StakeInstructionTag.AUTHORIZE_CHECKED_WITH_SEED,
        ):
            return self._decode_authorize(context, tag)
        if tag == StakeInstructionTag.DELEGATE_STAKE:
            return self._decode_delegate(context)
        if tag == StakeInstructionTag.SPLIT:
            return self._decode_split(context)
        if tag == StakeInstructionTag.WITHDRAW:
            return self._decode_withdraw(context)
        if tag == StakeInstructionTag.DEACTIVATE:
            return self._decode_deactivate(context)
        if tag in (StakeInstructionTag.SET_LOCKUP, StakeInstructionTag.SET_LOCKUP_CHECKED):
            return self._decode_set_lockup(context, tag)
        if tag == StakeInstructionTag.MERGE:
            return self._decode_merge(context)
        if tag in (StakeInstructionTag.MOVE_STAKE, StakeInstructionTag.MOVE_LAMPORTS):
            return self._decode_move(context, tag)

        # GET_MINIMUM_DELEGATION, DEACTIVATE_DELINQUENT and REDELEGATE carry no
        # user-visible action for tracked accounts.
        return DEFAULT_SOLANA_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[SolanaAddress, tuple[Any, ...]]:
        return {STAKE_PROGRAM: (self.decode_stake_instruction,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SOLANA_STAKE,
            label='Solana staking',
            image='solana.svg',
        ),)
