import logging
from collections.abc import Callable, Sequence
from functools import partial
from typing import TYPE_CHECKING, Final, TypeVar

import gevent
from httpx import HTTPStatusError, ReadTimeout
from solana.exceptions import SolanaRpcException
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.solders import (
    LOOKUP_TABLE_META_SIZE,
    Account,
    EncodedConfirmedTransactionWithStatusMeta,
    GetSignaturesForAddressResp,
    MessageAddressTableLookup,
    Signature,
    UiAddressTableLookup,
)

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.chain.mixins.rpc_nodes import SolanaRPCMixin
from rotkehlchen.chain.solana.utils import (
    ExtensionType,
    MetadataInfo,
    MintInfo,
    decode_metadata_pointer,
    decode_token_metadata,
    deserialize_mint,
    deserialize_solana_instruction_from_rpc,
    get_extension_data,
    get_metadata_account,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_solana_pubkey,
    deserialize_timestamp,
)
from rotkehlchen.types import SolanaAddress, SupportedBlockchain
from rotkehlchen.utils.misc import bytes_to_solana_address, get_chunks

from .constants import METADATA_LAYOUT_2022, METADATA_LAYOUT_LEGACY, METADATA_PROGRAM_IDS
from .types import SolanaTransaction, pubkey_to_solana_address

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.greenlets.manager import GreenletManager

R = TypeVar('R')
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

INITIAL_BACKOFF: Final = 4
BACKOFF_MULTIPLIER: Final = 2
MAX_RETRIES: Final = 3
SIGNATURES_PAGE_SIZE: Final = 1000
MAX_ACCOUNTS_PER_REQUEST: Final = 100


class SolanaInquirer(SolanaRPCMixin):

    def __init__(
            self,
            greenlet_manager: 'GreenletManager',
            database: 'DBHandler',
    ):
        SolanaRPCMixin.__init__(self)
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.blockchain = SupportedBlockchain.SOLANA
        self.rpc_timeout = DEFAULT_RPC_TIMEOUT

    def query(
            self,
            method: Callable[[Client], R],
            call_order: Sequence[WeightedNode] | None = None,
    ) -> R:
        """Request a method from solana using the provided or default call order.
        May raise RemoteError if unable to get a response from any node.
        """
        if call_order is None:
            call_order = self.default_call_order()

        for weighted_node in call_order:
            node_info = weighted_node.node_info
            if (rpc_node := self.rpc_mapping.get(node_info, None)) is None:
                if node_info.name in self.failed_to_connect_nodes:
                    continue

                success, _ = self.attempt_connect(node=node_info)
                if success is False:
                    self.failed_to_connect_nodes.add(node_info.name)
                    continue

                if (rpc_node := self.rpc_mapping.get(node_info, None)) is None:
                    log.error(f'Unexpected missing node {node_info} at Solana')
                    continue

            backoff, attempts = INITIAL_BACKOFF, 0
            while True:
                try:
                    return method(rpc_node.rpc_client)
                except SolanaRpcException as e:
                    if attempts > MAX_RETRIES:
                        log.error(f'Maximum retries reached for solana node {node_info.name}. Giving up.')  # noqa: E501
                        break

                    attempts += 1
                    ratelimit_response = None
                    if (
                        (
                            isinstance(e.__cause__, HTTPStatusError) and
                            (ratelimit_response := e.__cause__.response).status_code == 429  # pylint: disable=no-member  # cause is a HTTPStatusError here.
                        ) or
                        isinstance(e.__cause__, ReadTimeout)  # Some RPCs (publicnode.com) do a read timeout instead of a proper 429 response  # noqa: E501
                    ):
                        if ratelimit_response is not None and (retry_after := ratelimit_response.headers.get('retry-after')) is not None:  # noqa: E501
                            backoff = int(retry_after) + 1

                        log.warning(f'Got rate limited from solana node {node_info.name}. Backing off {backoff} seconds...')  # noqa: E501
                        gevent.sleep(backoff)
                        backoff *= BACKOFF_MULTIPLIER
                        continue

                    log.error(f'Failed to call solana node {node_info.name} due to {e}')
                    break

        log.error(f'Tried all solana nodes in {call_order} for {method} but did not get any response')  # noqa: E501
        raise RemoteError(f'Failed to get {method}')

    def get_raw_account_info(self, pubkey: Pubkey) -> bytes:
        """Query the raw account info for the given pubkey.
        May raise RemoteError if there is a problem with querying the external service.
        """
        if (response := self.query(
            method=lambda client: client.get_account_info(pubkey),
        ).value) is None:
            raise RemoteError(f'Got empty response for raw solana account info for {pubkey!s}')

        return response.data

    def get_raw_accounts_info(self, pubkeys: list[Pubkey]) -> dict[SolanaAddress, Account]:
        """Query the raw accounts info for the given pubkeys.
        May raise RemoteError if there is a problem with querying the external service.
        """
        aggregated_response: dict[SolanaAddress, Account] = {}
        for chunk in get_chunks(pubkeys, MAX_ACCOUNTS_PER_REQUEST):
            if (response := self.query(
                method=partial(lambda client, keys: client.get_multiple_accounts(keys), keys=list(chunk)),  # noqa: E501
            ).value) is None:
                raise RemoteError(f'Got empty response for raw solana accounts info for {chunk!s}')

            if len(response) != len(chunk):
                # shouldn't happen, rpc is expected to return one entry per input key
                # preserving order and including None for non-existent accounts
                # reference: https://solana.com/docs/rpc/http/getmultipleaccounts
                raise RemoteError(
                    f'Unexpected length mismatch from getMultipleAccounts, expected {len(chunk)} '
                    f'items but got {len(response)}',
                )

            aggregated_response.update({pubkey_to_solana_address(addr): info for addr, info in zip(chunk, response, strict=False) if info is not None})  # noqa: E501

        return aggregated_response

    def get_token_mint_info(self, token_address: SolanaAddress) -> MintInfo | None:
        """Query the mint info for the given token address.
        Returns the mint info or None if there was an error.
        """
        try:
            return deserialize_mint(
                mint_data=self.get_raw_account_info(pubkey=deserialize_solana_pubkey(token_address)),
            )
        except (RemoteError, DeserializationError) as e:
            log.error(f'Failed to get mint info for solana token {token_address} due to {e!s}')
            return None

    def get_token_metadata(
            self,
            token_address: SolanaAddress,
            mint_info: MintInfo,
    ) -> MetadataInfo | None:
        """Retrieve the metadata for the given token address either from the token extensions or
        by querying metadata PDAs.
        Returns the metadata or None if there was an error.
        """
        if (
            (metadata := self._get_metadata_from_extensions(
                token_address=token_address,
                mint_info=mint_info,
            )) is None and
            (metadata := self._get_metadata_from_pdas(token_address)) is None
        ):
            log.error(f'Failed to get metadata for solana token {token_address}')
            return None

        return metadata

    def _query_metadata_account(self, metadata_account: Pubkey) -> MetadataInfo:
        """Query the parsed legacy metadata for the given metadata account.
        Returns a tuple with the name and symbol of the token.
        May raise:
        - RemoteError if there is a problem with querying the external service.
        - DeserializationError if the metadata returned from onchain is invalid.
        """
        return decode_token_metadata(
            data=self.get_raw_account_info(pubkey=metadata_account),
            layout=METADATA_LAYOUT_LEGACY,
        )

    def _get_metadata_from_extensions(
            self,
            token_address: SolanaAddress,
            mint_info: MintInfo,
    ) -> MetadataInfo | None:
        """Attempt to get the metadata from token extensions in the mint info.
        If the extensions include a MetadataPointer there are two possibilities:
        - points to its own mint address - gets metadata from the TokenMetadata extension
        - points to a separate metadata account - queries metadata from that account

        Returns the metadata if found, otherwise returns None.
        """
        if mint_info.tlv_data is None or (raw_metadata_pointer := get_extension_data(
                extension_type=ExtensionType.METADATA_POINTER,
                tlv_data=mint_info.tlv_data,
        )) is None:
            return None  # This token doesn't have metadata extensions.

        if (metadata_address := decode_metadata_pointer(raw_metadata_pointer)) is None:
            log.error(f'Failed to decode metadata pointer extension for solana token {token_address}')  # noqa: E501
            return None

        if metadata_address == token_address:  # Token uses the TokenMetadata extension
            if (raw_data := get_extension_data(extension_type=ExtensionType.TOKEN_METADATA, tlv_data=mint_info.tlv_data)) is None:  # noqa: E501
                log.error(
                    f'Failed to get metadata for solana token {token_address}. Its TokenMetadata '
                    f'extension is missing despite the MetadataPointer indicating its own mint address.',  # noqa: E501
                )
                return None

            try:
                metadata = decode_token_metadata(data=raw_data, layout=METADATA_LAYOUT_2022)
            except DeserializationError as e:
                log.error(f'Failed to decode token metadata extension for solana token {token_address} due to {e!s}')  # noqa: E501
                return None

        else:  # Token uses a separate metadata account (uncommon)
            try:
                metadata = self._query_metadata_account(Pubkey.from_string(metadata_address))
            except (RemoteError, DeserializationError) as e:
                log.error(
                    f'Unable to query metadata for solana token {token_address} '
                    f'from metadata account {metadata_address} due to {e!s}',
                )
                return None

        return metadata

    def _get_metadata_from_pdas(self, token_address: SolanaAddress) -> MetadataInfo | None:
        """Query token metadata from PDAs (Program Derived Addresses) using known metadata
        programs, such as Metaplex.
        """
        for metadata_program in METADATA_PROGRAM_IDS:
            metadata_account = get_metadata_account(token_address, metadata_program)
            try:
                metadata = self._query_metadata_account(metadata_account)
                break
            except (RemoteError, DeserializationError):
                log.debug(
                    f'Failed to get metadata for solana token {token_address} '
                    f'from program {metadata_program}. Trying next program...',
                )
                continue
        else:
            log.error(f'Failed to query metadata for solana token {token_address} from any known metadata program.')  # noqa: E501
            return None

        return metadata

    def query_tx_signatures_for_address(
            self,
            address: SolanaAddress,
            until: Signature | None = None,
    ) -> list[Signature]:
        """Query all the transaction signatures for the given address.
        May raise RemoteError if there is a problem with querying the external service.
        """
        signatures, before = [], None
        while True:
            response: GetSignaturesForAddressResp = self.query(
                method=lambda client, _before=before, _until=until: client.get_signatures_for_address(  # type: ignore[misc]  # noqa: E501
                    account=Pubkey.from_string(address),
                    limit=SIGNATURES_PAGE_SIZE,
                    before=_before,
                    until=_until,
                ),
            )
            signatures.extend([tx_sig.signature for tx_sig in response.value])
            if len(response.value) < SIGNATURES_PAGE_SIZE:
                break  # all signatures have been queried

            before = response.value[-1].signature

        return signatures

    def get_transaction_for_signature(self, signature: Signature) -> tuple[SolanaTransaction, dict[SolanaAddress, tuple[SolanaAddress, SolanaAddress]]]:  # noqa: E501
        """Query the transaction with the given signature.
        Returns a tuple containing the transaction and
        a mapping of token accounts to (owner, mint).
        May raise:
        - RemoteError if there is a problem with querying the external service.
        - DeserializationError if there is a problem deserializing the transaction data.
        """
        if (response := self.query(method=lambda client: client.get_transaction(
            tx_sig=signature,
            max_supported_transaction_version=0,  # include the new v0 txs
        )).value) is None:
            raise RemoteError(f'Empty response from the RPC for solana tx {signature!s}')

        return self.deserialize_solana_tx_from_rpc(raw_tx=response)

    def _query_address_lookup_table(
            self,
            alt: MessageAddressTableLookup | UiAddressTableLookup,
    ) -> tuple[list[SolanaAddress], list[SolanaAddress]]:
        """Query the addresses for the given address table lookup.
        Returns a tuple containing the writable and readonly address lists or None if the account
        data is invalid.
        May raise:
        - RemoteError if there is a problem with querying the external service.
        - DeserializationError if there is a problem deserializing the table data.
        """
        if (
            (account_info := self.get_raw_account_info(pubkey=alt.account_key)) is None or
            len(account_info) <= LOOKUP_TABLE_META_SIZE  # ensure the table data is at least as large as the lookup table meta data size  # noqa: E501
        ):
            raise DeserializationError(f'Invalid solana address lookup table account data for {alt.account_key}')  # noqa: E501

        table_data = account_info[LOOKUP_TABLE_META_SIZE:]
        accounts = [
            bytes_to_solana_address(table_data[idx:idx + 32])
            for idx in range(0, len(table_data), 32)
        ]
        return (
            [accounts[idx] for idx in alt.writable_indexes],
            [accounts[idx] for idx in alt.readonly_indexes],
        )

    def deserialize_solana_tx_from_rpc(
            self,
            raw_tx: EncodedConfirmedTransactionWithStatusMeta,
    ) -> tuple[SolanaTransaction, dict[SolanaAddress, tuple[SolanaAddress, SolanaAddress]]]:
        """Deserialize a solana transaction from the RPC response.
        Returns a tuple containing the transaction and
        a mapping of token accounts to (owner, mint).

        Note that the solders library uses some complex union types, apparently to support querying
        using different parsing options, so we use some type ignores here since we only use the
        default (`json`) parsing option when querying tx data.
        May raise:
        - DeserializationError if there is a problem deserializing.
        - RemoteError if there is a problem with querying the Address Lookup Tables (ALTs).
        """
        message = raw_tx.transaction.transaction.message  # type: ignore[union-attr]
        if raw_tx.transaction.meta is None:
            raise DeserializationError('The tx data does not contain transaction meta')

        try:
            account_keys = [pubkey_to_solana_address(pubkey) for pubkey in message.account_keys]  # type: ignore[arg-type]  # it is a pubkey
            if (  # maybe resolve addresses from Address Lookup Tables (ALTs)
                (alts := message.address_table_lookups) is not None and  # type: ignore[union-attr]
                len(alts) > 0
            ):
                writable_accounts, readonly_accounts = [], []
                for alt in alts:
                    alt_writable, alt_readonly = self._query_address_lookup_table(alt)
                    writable_accounts.extend(alt_writable)
                    readonly_accounts.extend(alt_readonly)

                # Account key order with ALTs is: all keys from the tx itself, then all writeable
                # accounts from all ALTs, and then all readonly accounts from all ALTs.
                # https://docs.anza.xyz/proposals/versioned-transactions#new-transaction-format
                account_keys.extend(writable_accounts + readonly_accounts)

            inner_instructions_dict = {}
            if raw_tx.transaction.meta.inner_instructions is not None:
                for inner_instructions in raw_tx.transaction.meta.inner_instructions:
                    inner_instructions_dict[inner_instructions.index] = [
                        deserialize_solana_instruction_from_rpc(
                            execution_index=idx,
                            parent_execution_index=inner_instructions.index,
                            raw_instruction=raw_instruction,  # type: ignore[arg-type]
                            account_keys=account_keys,
                        ) for idx, raw_instruction in enumerate(inner_instructions.instructions)
                    ]

            instructions = []
            for idx, raw_instruction in enumerate(message.instructions):
                instructions.append(deserialize_solana_instruction_from_rpc(
                    execution_index=idx,
                    parent_execution_index=None,
                    raw_instruction=raw_instruction,
                    account_keys=account_keys,
                ))
                if (inner_instruction := inner_instructions_dict.get(idx)) is not None:
                    instructions.extend(inner_instruction)

            token_accounts_mapping: dict[SolanaAddress, tuple[SolanaAddress, SolanaAddress]] = {}
            for token_balances in (
                    raw_tx.transaction.meta.pre_token_balances,
                    raw_tx.transaction.meta.post_token_balances,
            ):
                if token_balances is None:
                    continue

                for token_balance in token_balances:
                    if token_balance.owner is None or token_balance.mint is None:
                        log.warning(
                            f'Solana transaction {raw_tx.transaction.transaction.signatures[0]} has '  # noqa: E501
                            f'token account {account_keys[token_balance.account_index]} without an owner. Skipping.',  # noqa: E501
                        )
                        continue

                    token_accounts_mapping[account_keys[token_balance.account_index]] = (
                        pubkey_to_solana_address(token_balance.owner),
                        pubkey_to_solana_address(token_balance.mint),
                    )

            return (SolanaTransaction(
                fee=raw_tx.transaction.meta.fee,
                slot=raw_tx.slot,
                success=raw_tx.transaction.meta.err is None,
                signature=raw_tx.transaction.transaction.signatures[0],
                block_time=deserialize_timestamp(raw_tx.block_time),
                account_keys=account_keys,
                instructions=instructions,
            ), token_accounts_mapping)
        except (IndexError, ValueError, TypeError, DeserializationError) as e:
            raise DeserializationError(f'Failed to deserialize solana tx due to {e!s}') from e
