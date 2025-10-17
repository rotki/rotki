import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from solders.solders import Signature

from rotkehlchen.assets.utils import TokenEncounterInfo, get_or_create_solana_token
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.decoding.decoder import TransactionDecoder
from rotkehlchen.chain.decoding.utils import decode_safely
from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value,
)
from rotkehlchen.chain.evm.decoding.constants import OUTGOING_EVENT_TYPES
from rotkehlchen.chain.solana.types import (
    SolanaInstruction,
    SolanaTransaction,
)
from rotkehlchen.chain.solana.utils import deserialize_token_account, lamports_to_sol
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.filtering import (
    SolanaEventFilterQuery,
    SolanaTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.errors.misc import ModuleLoadingError, NotSPLConformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.solana_swap import SolanaSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_solana_pubkey
from rotkehlchen.types import Location, SolanaAddress, SupportedBlockchain
from rotkehlchen.utils.misc import bytes_to_solana_address

from .constants import (
    NATIVE_TRANSFER_DISCRIMINATOR,
    SPL_TOKEN_INITIALIZE_ACCOUNT_DISCRIMINATOR,
    SPL_TOKEN_PROGRAM,
    SPL_TOKEN_TRANSFER_CHECKED_DISCRIMINATORS,
    SPL_TOKEN_TRANSFER_DISCRIMINATOR,
    SYSTEM_PROGRAM,
    TOKEN_2022_PROGRAM,
)
from .interfaces import SolanaDecoderInterface
from .structures import (
    SolanaDecoderContext,
    SolanaDecodingOutput,
)
from .tools import SolanaDecoderTools

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
    from rotkehlchen.chain.solana.transactions import SolanaTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class SolanaDecodingRules:
    address_mappings: dict[SolanaAddress, tuple[Any, ...]]
    all_counterparties: set['CounterpartyDetails']

    def __add__(self, other: 'SolanaDecodingRules') -> 'SolanaDecodingRules':
        if not isinstance(other, SolanaDecodingRules):
            raise TypeError(
                f'Can only add SolanaDecodingRules to SolanaDecodingRules. Got {type(other)}',
            )

        return SolanaDecodingRules(
            address_mappings=self.address_mappings | other.address_mappings,
            all_counterparties=self.all_counterparties | other.all_counterparties,
        )


class SolanaTransactionDecoder(TransactionDecoder[SolanaTransaction, SolanaDecodingRules, SolanaDecoderInterface, Signature, SolanaEvent, SolanaTransaction, SolanaDecoderTools, DBSolanaTx, SolanaEventFilterQuery, SolanaTransactionsNotDecodedFilterQuery]):  # noqa: E501

    def __init__(
            self,
            database: 'DBHandler',
            node_inquirer: 'SolanaInquirer',
            transactions: 'SolanaTransactions',
            base_tools: 'SolanaDecoderTools',
            premium: 'Premium | None' = None,
    ):
        self.node_inquirer = node_inquirer
        self.transactions = transactions
        self.dbevents = DBHistoryEvents(database)
        super().__init__(
            database=database,
            dbtx=DBSolanaTx(database),
            tx_mappings_table='solana_tx_mappings',
            chain_name=SupportedBlockchain.SOLANA.name.lower(),
            value_asset=A_SOL.resolve_to_asset_with_oracles(),
            rules=SolanaDecodingRules(address_mappings={}, all_counterparties=set()),
            premium=premium,
            base_tools=base_tools,
            misc_counterparties=[],
            possible_decoding_exceptions=(),
        )

    def _add_builtin_decoders(self, rules: SolanaDecodingRules) -> None:
        """No-op for solana. All decoders are loaded dynamically."""

    def _add_single_decoder(
            self,
            class_name: str,
            decoder_class: type[SolanaDecoderInterface],
            rules: SolanaDecodingRules,
    ) -> None:
        """Initialize a single decoder, add it to the set of decoders to use
        and append its rules to the passed rules
        """
        if class_name in self.decoders:
            raise ModuleLoadingError(f'{self.chain_name} decoder with name {class_name} already loaded')  # noqa: E501

        self.decoders[class_name] = (decoder := decoder_class(
            node_inquirer=self.node_inquirer,
            base_tools=self.base,
            msg_aggregator=self.msg_aggregator,
        ))
        new_address_to_decoders = decoder.addresses_to_decoders()

        if __debug__:  # sanity checks for now only in debug as decoders are constant
            self.assert_keys_are_unique(
                new_struct=new_address_to_decoders,
                main_struct=rules.address_mappings,
                class_name=class_name,
                type_name='address_mappings',
            )

        rules.address_mappings.update(new_address_to_decoders)
        rules.all_counterparties.update(decoder.counterparties())

    @staticmethod
    def _load_default_decoding_rules() -> SolanaDecodingRules:
        return SolanaDecodingRules(address_mappings={}, all_counterparties=set())

    def _get_tx_not_decoded_filter_query(
            self,
            limit: int | None,
    ) -> SolanaTransactionsNotDecodedFilterQuery:
        return SolanaTransactionsNotDecodedFilterQuery.make(limit=limit)

    def _load_transaction_context(
            self,
            cursor: 'DBCursor',
            tx_hash: Signature,
    ) -> SolanaTransaction:
        return self.transactions.get_or_create_transaction(signature=tx_hash)

    def _decode_transaction_from_context(
            self,
            context: SolanaTransaction,
            ignore_cache: bool,
            delete_customized: bool,
    ) -> tuple[list[SolanaEvent], bool, set[str] | None]:
        if (events := self._maybe_load_or_purge_events_from_db(
            transaction=context,
            tx_ref=context.signature,
            location=Location.SOLANA,
            ignore_cache=ignore_cache,
            delete_customized=delete_customized,
        )) is not None:
            return events, False, None

        # else we should decode now
        return self._decode_transaction(transaction=context)

    def _make_event_filter_query(self, tx_ref: Signature) -> SolanaEventFilterQuery:
        return SolanaEventFilterQuery.make(signatures=[tx_ref])

    def _calculate_fees(self, tx: SolanaTransaction) -> FVal:
        return lamports_to_sol(tx.fee)

    def _maybe_decode_fee_event(self, transaction: SolanaTransaction) -> SolanaEvent | None:
        """Decode the fee event for the given transaction.
        Returns the fee event or None if the fee is zero or the fee payer is not tracked.
        """
        if transaction.fee == ZERO or not self.base.is_tracked(fee_payer := transaction.account_keys[0]):  # noqa: E501
            return None

        return self.base.make_event_next_index(
            tx_ref=transaction.signature,
            timestamp=transaction.block_time,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_SOL,
            amount=(amount := lamports_to_sol(transaction.fee)),
            location_label=fee_payer,
            notes=f'Spend {amount} SOL as transaction fee',
            counterparty=CPT_GAS,
        )

    @staticmethod
    def _identify_token_transfer(
            instruction: SolanaInstruction,
            transaction_signature: Signature,
    ) -> tuple[SolanaAddress, SolanaAddress] | None:
        """Identify token transfer instruction and extract their token account addresses."""
        if not (
            instruction.program_id in (SPL_TOKEN_PROGRAM, TOKEN_2022_PROGRAM) and
            instruction.data[:1] in (SPL_TOKEN_TRANSFER_DISCRIMINATOR, *SPL_TOKEN_TRANSFER_CHECKED_DISCRIMINATORS) and  # noqa: E501
            len(instruction.data) > 0
        ):
            return None

        minimum_accounts, to_token_account_idx = 3, 1
        if instruction.data[:1] in SPL_TOKEN_TRANSFER_CHECKED_DISCRIMINATORS:
            minimum_accounts, to_token_account_idx = 4, 2

        if len(instruction.accounts) < minimum_accounts:
            log.error(
                f'Skipping SPL token transfer in {transaction_signature}, '
                f'expected at least {minimum_accounts} accounts but found {len(instruction.accounts)}',  # noqa: E501
            )
            return None

        return instruction.accounts[0], instruction.accounts[to_token_account_idx]

    def _fetch_token_accounts_owners(
            self,
            token_accounts: list[SolanaAddress],
    ) -> dict[SolanaAddress, tuple[SolanaAddress, SolanaAddress]]:
        """Fetch token account owners and mint addresses from cache or RPC calls as fallback.

        In Solana, tokens are held in Associated Token Accounts (ATAs) rather than directly
        by user wallets. Each token account contains metadata about:
        - The owner (the wallet address that controls this token account)
        - The mint (the token contract address)

        This function takes pairs of token accounts (typically from/to in transfers) and
        retrieves the (owner, mint) information for each unique token account. It first
        tries to get this data from the local cache to avoid RPC calls, and
        only queries the Solana RPC for accounts not found in cache.

        May raise:
        - RemoteError
        - DeserializationError
        """
        result = {}
        accounts_needing_rpc = set()
        with self.database.conn.read_ctx() as cursor:
            for token_account in token_accounts:
                if (cached_owner_mint := self.database.get_dynamic_cache(
                    cursor=cursor,
                    name=DBCacheDynamic.SOLANA_TOKEN_ACCOUNT,
                    address=token_account,
                )) is not None:
                    result[token_account] = cached_owner_mint
                else:
                    accounts_needing_rpc.add(deserialize_solana_pubkey(token_account))

        if len(accounts_needing_rpc) > 0:  # fallback to RPC calls for uncached accounts
            token_cache_data = []
            for account_addr, account_info in self.node_inquirer.get_raw_accounts_info(list(accounts_needing_rpc)).items():  # noqa: E501
                token_account_info = deserialize_token_account(account_info.data)
                result[(token_account := account_addr)] = (owner_mint_info := (
                    token_account_info.owner,
                    token_account_info.mint,
                ))
                token_cache_data.append((
                    DBCacheDynamic.SOLANA_TOKEN_ACCOUNT.get_db_key(address=token_account),
                    ','.join(owner_mint_info),
                ))

            with self.database.conn.write_ctx() as write_cursor:
                write_cursor.executemany(
                    'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
                    token_cache_data,
                )

        return result

    def _maybe_decode_token_transfer(
            self,
            transaction: SolanaTransaction,
            instruction: SolanaInstruction,
            token_accounts: tuple[SolanaAddress, SolanaAddress],
            token_accounts_with_owners: dict[SolanaAddress, tuple[SolanaAddress, SolanaAddress]],
    ) -> SolanaEvent | None:
        """Decode transfer-like spl token instructions (spl-token and token-2022).
        It supports:
            - Transfer
            - TransferChecked
            - TransferCheckedWithFee

        Both token programs share identical instruction layout, so we can safely extract
        fields from known offsets. The instruction program and type are verified in
        _identify_token_transfer() before this function is called, ensuring the data
        structure matches the documented layout.

        Reference:
         * https://github.com/solana-program/token/blob/main/interface/src/instruction.rs
         * https://github.com/solana-program/token-2022/blob/main/interface/src/instruction.rs
        """
        if (raw_amount := int.from_bytes(instruction.data[1:9], 'little')) == ZERO:
            return None

        try:
            owners: list[SolanaAddress] = []
            for token_address in token_accounts:
                if (account_data := token_accounts_with_owners.get(token_address)) is None:
                    log.error(f'Failed to find owner data for SPL token account {token_address} in transaction {transaction.signature}')  # noqa: E501
                    return None

                owners.append(account_data[0])

            # mint_address is guaranteed to exist since we checked
            # all token_accounts exist in token_accounts_with_owners above
            mint_address = token_accounts_with_owners[token_accounts[0]][1]
        except (DeserializationError, RemoteError) as e:
            log.error(
                f'Failed to fetch SPL token account owners for ({token_accounts}) in '
                f'transaction {transaction.signature} due to {e}',
            )
            return None

        try:
            spl_token = get_or_create_solana_token(
                userdb=self.database,
                address=mint_address,
                solana_inquirer=self.node_inquirer,
                encounter=TokenEncounterInfo(tx_ref=transaction.signature),
            )
        except NotSPLConformant as e:
            log.error(
                f'Failed to load SPL token {mint_address} in transaction '
                f'{transaction.signature} due to {e}',
            )
            return None

        return self._compose_transfer_event(
            transaction=transaction,
            amount=token_normalized_value(
                token_amount=raw_amount,
                token=spl_token,
            ),
            asset=spl_token,
            from_address=owners[0],
            to_address=owners[1],
        )

    def _maybe_decode_native_transfer(
            self,
            transaction: SolanaTransaction,
            instruction: SolanaInstruction,
    ) -> SolanaEvent | None:
        """Decode native SOL transfers."""
        if instruction.program_id != SYSTEM_PROGRAM or instruction.data[:4] != NATIVE_TRANSFER_DISCRIMINATOR:  # noqa: E501
            return None

        if (account_len := len(instruction.accounts)) < 2:
            log.error(
                f'Encountered a native transfer instruction in {transaction} '
                f'with {account_len} accounts. Expected 2. Skipping.',
            )
            return None

        if (raw_amount := int.from_bytes(instruction.data[4:12], byteorder='little')) == ZERO:
            return None

        return self._compose_transfer_event(
            transaction=transaction,
            amount=lamports_to_sol(raw_amount),
            asset=A_SOL,
            from_address=instruction.accounts[0],
            to_address=instruction.accounts[1],
        )

    def _maybe_get_token_account_initialization(
            self,
            transaction: SolanaTransaction,
            instruction: SolanaInstruction,
    ) -> tuple[SolanaAddress, SolanaAddress, SolanaAddress] | None:
        """Decode an SPL associated token account (ATA) initialization instruction.
        Returns a tuple containing the ATA address, the owner address, and the mint address.
        """
        if (
            instruction.program_id != SPL_TOKEN_PROGRAM or
            instruction.data[:1] != SPL_TOKEN_INITIALIZE_ACCOUNT_DISCRIMINATOR
        ):
            return None

        if (account_len := len(instruction.accounts)) < 2:
            log.error(
                f'Encountered an SPL token account initialization instruction in {transaction} '
                f'with {account_len} accounts. Expected 2. Skipping.',
            )
            return None

        return (
            instruction.accounts[0],  # ATA address
            bytes_to_solana_address(instruction.data[1:33]),  # account owner address
            instruction.accounts[1],  # token mint address
        )

    def _compose_transfer_event(
            self,
            amount: FVal,
            asset: 'Asset',
            from_address: 'SolanaAddress',
            to_address: 'SolanaAddress',
            transaction: SolanaTransaction,
    ) -> SolanaEvent | None:
        if (direction_result := self.base.decode_direction(
                from_address=from_address,
                to_address=to_address,
        )) is None:
            return None

        event_type, event_subtype, location_label, address, counterparty, verb = direction_result
        counterparty_or_address = counterparty or address
        preposition = 'to' if event_type in OUTGOING_EVENT_TYPES else 'from'
        return self.base.make_event_next_index(
            tx_ref=transaction.signature,
            timestamp=transaction.block_time,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=f'{verb} {amount} {asset.resolve_to_asset_with_symbol().symbol} {preposition} {counterparty_or_address}',  # noqa: E501
            counterparty=counterparty,
            address=address,
        )

    def _decode_basic_events(
            self,
            transaction: SolanaTransaction,
    ) -> tuple[list[SolanaEvent], list[SolanaInstruction]]:
        """Decode the basic events (fee, transfers, etc.) for the given transaction.
        Returns a tuple containing the list of decoded events and the list of instructions that
        have not been decoded yet.
        """
        events: list[SolanaEvent] = []
        if (fee_event := self._maybe_decode_fee_event(transaction=transaction)) is not None:
            events.append(fee_event)

        token_accounts_with_owners: dict[SolanaAddress, tuple[SolanaAddress, SolanaAddress]] = {}
        transfers_and_token_accounts = []
        token_account_list: list[SolanaAddress] = []
        # Decode basic transfer instructions so that the more complex decoding that runs later
        # can simply modify the already decoded transfer events.
        undecoded_instructions = []
        for instruction in transaction.instructions:
            if (native_transfer_event := self._maybe_decode_native_transfer(
                transaction=transaction,
                instruction=instruction,
            )) is not None:
                events.append(native_transfer_event)
            elif (token_accounts := self._identify_token_transfer(
                instruction=instruction,
                transaction_signature=transaction.signature,
            )) is not None:
                token_account_list.extend(token_accounts)
                transfers_and_token_accounts.append((instruction, token_accounts))
            if (account_initialization_result := self._maybe_get_token_account_initialization(
                transaction=transaction,
                instruction=instruction,
            )) is not None:
                ata_address, owner_address, mint_address = account_initialization_result
                token_accounts_with_owners[ata_address] = (owner_address, mint_address)
            else:
                undecoded_instructions.append(instruction)

        try:
            token_accounts_with_owners.update(self._fetch_token_accounts_owners(
                token_accounts=[x for x in token_account_list if x not in token_accounts_with_owners],  # noqa: E501
            ))
        except (DeserializationError, RemoteError) as e:
            log.error(f'Failed to fetch token account owners for transaction {transaction.signature} due to {e}')  # noqa: E501
            # Add all token transfer instructions to undecoded since we can't process them
            undecoded_instructions.extend(instruction for instruction, _ in transfers_and_token_accounts)  # noqa: E501
            return events, undecoded_instructions

        for instruction, token_accounts in transfers_and_token_accounts:
            if (transfer_event := self._maybe_decode_token_transfer(
                transaction=transaction,
                instruction=instruction,
                token_accounts=token_accounts,
                token_accounts_with_owners=token_accounts_with_owners,
            )) is not None:
                events.append(transfer_event)

            undecoded_instructions.append(instruction)

        return events, undecoded_instructions

    def _decode_transaction(
            self,
            transaction: SolanaTransaction,
    ) -> tuple[list[SolanaEvent], bool, set[str] | None]:
        """Decodes a solana transaction and saves the result in the DB.
        Returns
        - the list of decoded events
        - a flag which is True if balances refresh is needed
        - A list of decoders to reload or None if no need
        """
        log.debug(f'Starting decoding of solana transaction {transaction.signature!s}')

        with self.database.conn.write_ctx() as write_cursor:
            tx_id = transaction.get_or_query_db_id(write_cursor)

        if len(transaction.account_keys) == 0 or len(transaction.instructions) == 0:
            log.warning(
                f'Solana transaction {transaction.signature!s} '
                f'has empty instructions or accounts. Ignoring this transaction.',
            )
            self._write_new_tx_events_to_the_db(
                events=[],  # marks the tx as decoded and adds to the ignored action ids since there are no events.  # noqa: E501
                action_id=str(transaction.signature),
                db_id=tx_id,
            )
            return [], False, None

        self.base.reset_sequence_counter(tx_data=transaction)
        events, undecoded_instructions = self._decode_basic_events(transaction=transaction)
        refresh_balances, reload_decoders, process_swaps = False, set(), False
        for instruction in undecoded_instructions:
            if (mapping_result := self.rules.address_mappings.get(instruction.program_id)) is None:
                continue

            context = SolanaDecoderContext(
                transaction=transaction,
                instruction=instruction,
                decoded_events=events,
            )
            method, *args = mapping_result
            decoding_output: SolanaDecodingOutput
            decoding_output, err = decode_safely(  # can't used named arguments with *args
                self.possible_decoding_exceptions,
                self.msg_aggregator,
                SupportedBlockchain.SOLANA,
                method,
                str(context.transaction.signature),
                *(context, *args),
            )
            if err:
                continue

            if decoding_output.refresh_balances:
                refresh_balances = True
            if decoding_output.reload_decoders is not None:
                reload_decoders.update(decoding_output.reload_decoders)
            if decoding_output.events is not None:
                events.extend(decoding_output.events)
            if decoding_output.process_swaps:
                process_swaps = True

        # the events list may not be properly ordered after decoding
        events = sorted(events, key=lambda x: x.sequence_index, reverse=False)
        if process_swaps:
            events = self._process_swaps(transaction=transaction, decoded_events=events)

        self._write_new_tx_events_to_the_db(
            events=events,
            action_id=str(transaction.signature),
            db_id=tx_id,
        )
        return events, refresh_balances, (reload_decoders if len(reload_decoders) > 0 else None)

    def _create_swap_event(
            self,
            trade_event: SolanaEvent,
            spend_event: SolanaEvent,
            sequence_index: int,
            event_type: HistoryEventType,
    ) -> SolanaEvent:
        """Creates a SolanaSwapEvent from trade event data."""
        return SolanaSwapEvent(
            tx_ref=trade_event.tx_ref,
            sequence_index=sequence_index,
            timestamp=trade_event.timestamp,
            event_type=event_type,  # type: ignore[arg-type]  # will be TRADE or MULTI_TRADE
            event_subtype=trade_event.event_subtype,  # type: ignore[arg-type]  # will be SPEND, RECEIVE, or FEE
            asset=trade_event.asset,
            amount=trade_event.amount,
            notes=trade_event.notes,
            extra_data=trade_event.extra_data,
            location_label=trade_event.location_label if trade_event.location_label is not None else spend_event.location_label,  # noqa: E501
            counterparty=spend_event.counterparty,
            address=spend_event.address,
        )
