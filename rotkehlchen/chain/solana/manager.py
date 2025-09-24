import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Final, TypeVar

import gevent
from construct import ConstructError
from httpx import HTTPStatusError, ReadTimeout
from solana.exceptions import SolanaRpcException
from solana.rpc.api import Client
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
from solders.solders import (
    LOOKUP_TABLE_META_SIZE,
    EncodedConfirmedTransactionWithStatusMeta,
    MessageAddressTableLookup,
    Signature,
    UiAddressTableLookup,
)
from spl.token._layouts import ACCOUNT_LAYOUT
from spl.token.constants import TOKEN_2022_PROGRAM_ID, TOKEN_PROGRAM_ID

from rotkehlchen.api.websockets.typedefs import (
    TransactionStatusStep,
    TransactionStatusSubType,
    WSMessageType,
)
from rotkehlchen.assets.asset import Asset, SolanaToken
from rotkehlchen.assets.utils import get_solana_token
from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.chain.mixins.rpc_nodes import SolanaRPCMixin
from rotkehlchen.chain.solana.utils import (
    ExtensionType,
    MetadataInfo,
    MintInfo,
    decode_metadata_pointer,
    decode_token_metadata,
    deserialize_solana_instruction_from_rpc,
    get_extension_data,
    get_metadata_account,
    is_token_nft,
    lamports_to_sol,
    unpack_mint,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.helius import Helius
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import SolanaAddress, SupportedBlockchain, Timestamp, TokenKind
from rotkehlchen.utils.misc import bytes_to_solana_address, ts_now

from .constants import METADATA_LAYOUT_2022, METADATA_LAYOUT_LEGACY, METADATA_PROGRAM_IDS
from .types import SolanaTransaction

if TYPE_CHECKING:
    from solders.solders import GetSignaturesForAddressResp, GetTokenAccountsByOwnerResp

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.greenlets.manager import GreenletManager

R = TypeVar('R')
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


INITIAL_BACKOFF: Final = 4
BACKOFF_MULTIPLIER: Final = 2
MAX_RETRIES: Final = 3
SIGNATURES_PAGE_SIZE: Final = 1000


class SolanaManager(SolanaRPCMixin):

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
        self.helius = Helius(database=self.database)

    def _query(
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

            backoff = INITIAL_BACKOFF
            attempts = 0
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

    def get_multi_balance(self, accounts: Sequence[SolanaAddress]) -> dict[SolanaAddress, FVal]:
        """Returns a dict with keys being accounts and balances in the chain native token.

        May raise:
        - RemoteError if an external service is queried and there is a problem with its query.
        """
        response = self._query(
            method=lambda client: client.get_multiple_accounts(
                pubkeys=[Pubkey.from_string(addr) for addr in accounts],
            ),
        )

        result = {}
        for account, entry in zip(accounts, response.value, strict=False):
            if entry is None or entry.lamports == 0:
                log.debug(f'Found no account entry in balances for solana account {account}. Skipping')  # noqa: E501
                result[account] = ZERO
            else:
                result[account] = lamports_to_sol(entry.lamports)

        return result

    def get_token_balances(self, account: SolanaAddress) -> dict[Asset, FVal]:
        """Query the token balances of the given account.
        May raise RemoteError if there is a problem with querying the external service.
        """
        balances: defaultdict[Asset, FVal] = defaultdict(lambda: ZERO)
        for token_program_id in (TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID):
            log.debug(f'Querying solana token balances for {account} with program id {token_program_id}')  # noqa: E501
            response: GetTokenAccountsByOwnerResp = self._query(
                method=lambda client, pid=token_program_id: client.get_token_accounts_by_owner(  # type: ignore
                    owner=Pubkey.from_string(account),
                    opts=TokenAccountOpts(program_id=pid),
                ),
            )
            for account_info in response.value:
                try:
                    decoded = ACCOUNT_LAYOUT.parse(account_info.account.data)
                except ConstructError as e:
                    log.error(f'Failed to parse solana token account data for {account} due to {e}')  # noqa: E501
                    continue

                try:
                    token_address = bytes_to_solana_address(decoded.mint)
                except DeserializationError as e:
                    log.error(f'Failed to deserialize a solana token address for {account} due to {e}')  # noqa: E501
                    continue

                if decoded.amount == ZERO:
                    log.debug(f'Found solana token {token_address} with zero balance for {account}. Skipping.')  # noqa: E501
                    continue

                if (
                    (token := get_solana_token(token_address)) is None and
                    (token := self._create_token(token_address)) is None
                ):
                    log.error(f'Failed to create solana token with address {token_address}')
                    continue

                # Add to existing balances since there may be multiple ATAs
                # (Associated Token Account) for the same token.
                balances[token] += (amount := token_normalized_value(
                    token=token,
                    token_amount=decoded.amount,
                ))
                log.debug(f'Found {token} token balance for solana account {account} with balance {amount}')  # noqa: E501

        return balances

    def _create_token(self, token_address: SolanaAddress) -> SolanaToken | None:
        """Creates a solana token from the given token address.
        Queries the mint info for the token which contains supply, decimals, and extensions.
        Then queries the metadata (name, symbol, etc.) from either the extensions or
        the known metadata programs.
        May raise RemoteError if there is a problem with querying the external service.
        """
        log.debug(f'Creating solana token with address {token_address}')
        if (
            (raw_mint := self._get_raw_account_info(pubkey=Pubkey.from_string(token_address))) is None or  # noqa: E501
            (mint_info := unpack_mint(raw_mint)) is None
        ):
            log.error(f'Failed to get mint info for solana token {token_address}')
            return None

        if (
            (metadata := self._get_metadata_from_extensions(
                token_address=token_address,
                mint_info=mint_info,
            )) is None and
            (metadata := self._get_metadata_from_pdas(token_address)) is None
        ):
            log.error(f'Failed to get metadata for solana token {token_address}')
            return None

        # TODO: Maybe use metadata.uri to query the token image as well?
        # Note that is_token_nft already may query the offchain metadata, so don't query it twice
        # https://github.com/orgs/rotki/projects/11/views/3?pane=issue&itemId=127649813
        GlobalDBHandler().add_asset(token := SolanaToken.initialize(
            address=token_address,
            token_kind=TokenKind.SPL_NFT if is_token_nft(
                token_address=token_address,
                mint_info=mint_info,
                metadata=metadata,
            ) else TokenKind.SPL_TOKEN,
            name=metadata.name,
            symbol=metadata.symbol,
            decimals=mint_info.decimals,
        ))
        return token

    def _get_raw_account_info(self, pubkey: Pubkey) -> bytes | None:
        """Query the raw account info for the given pubkey.
        May raise RemoteError if there is a problem with querying the external service.
        """
        if (response := self._query(
            method=lambda client: client.get_account_info(pubkey),
        ).value) is None:
            log.error(f'Failed to get raw solana account info for {pubkey!s}')
            return None

        return response.data

    def _query_metadata_account(self, metadata_account: Pubkey) -> MetadataInfo | None:
        """Query the parsed legacy metadata for the given metadata account.
        Returns a tuple with the name and symbol of the token.
        May raise RemoteError if there is a problem with querying the external service.
        """
        if (
            (raw_data := self._get_raw_account_info(pubkey=metadata_account)) is None or
            (metadata := decode_token_metadata(data=raw_data, layout=METADATA_LAYOUT_LEGACY)) is None  # noqa: E501
        ):
            log.error(f'Failed to get solana token legacy metadata from {metadata_account}')
            return None

        return metadata

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
            if (
                (raw_data := get_extension_data(extension_type=ExtensionType.TOKEN_METADATA, tlv_data=mint_info.tlv_data)) is None or  # noqa: E501
                (metadata := decode_token_metadata(data=raw_data, layout=METADATA_LAYOUT_2022)) is None  # noqa: E501
            ):
                log.error(f'Failed to decode token metadata extension for solana token {token_address}')  # noqa: E501
                return None

        else:  # Token uses a separate metadata account (uncommon)
            metadata = self._query_metadata_account(Pubkey.from_string(metadata_address))

        return metadata

    def _get_metadata_from_pdas(self, token_address: SolanaAddress) -> MetadataInfo | None:
        """Query token metadata from PDAs (Program Derived Addresses) using known metadata
        programs, such as Metaplex.
        """
        for metadata_program in METADATA_PROGRAM_IDS:
            log.debug(f'Querying metadata for solana token {token_address} using program {metadata_program}')  # noqa: E501
            metadata_account = get_metadata_account(token_address, metadata_program)
            if (metadata := self._query_metadata_account(metadata_account)) is not None:
                break
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
            response: GetSignaturesForAddressResp = self._query(
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

    def query_transactions(self, addresses: list[SolanaAddress]) -> None:
        """Query the transactions for the given addresses and save them to the DB.
        Only queries new transactions if there are already transactions in the DB.
        """
        for address in addresses:
            self.query_transactions_for_address(address=address)

    def query_transactions_for_address(self, address: SolanaAddress) -> None:
        """Query the transactions for the given address and save them to the DB.
        Only queries new transactions if there are already transactions in the DB.
        """
        last_existing_sig, start_ts, end_ts = None, Timestamp(0), ts_now()
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT st.signature, max(st.block_time) FROM solana_transactions st '
                'JOIN solanatx_address_mappings sam ON st.identifier == sam.tx_id '
                'WHERE sam.address = ?',
                (address,),
            )
            if (max_result := cursor.fetchone()) is not None and None not in max_result:
                last_existing_sig = Signature.from_bytes(max_result[0])
                start_ts = Timestamp(max_result[1])

        self.database.msg_aggregator.add_message(
            message_type=WSMessageType.TRANSACTION_STATUS,
            data={
                'address': address,
                'chain': SupportedBlockchain.SOLANA.value,
                'subtype': str(TransactionStatusSubType.SOLANA),
                'period': [start_ts, end_ts],
                'status': str(TransactionStatusStep.QUERYING_TRANSACTIONS_STARTED),
            },
        )

        # Get the list of signatures from the RPCs
        signatures = self.query_tx_signatures_for_address(
            address=address,
            until=last_existing_sig,
        )

        # Query the full tx data for each signature from either Helius or the RPCs
        if (transactions := self.helius.get_transactions(
            signatures=[str(x) for x in signatures],
        )) is None:
            log.debug(
                'Unable to query solana transactions from Helius. '
                f'Falling back to querying from the rpc for address {address}.',
            )
            transactions = [
                tx for signature in signatures
                if (tx := self.query_rpc_for_single_tx(signature)) is not None
            ]

        # Save txs to the DB
        with self.database.conn.write_ctx() as write_cursor:
            DBSolanaTx(database=self.database).add_solana_transactions(
                write_cursor=write_cursor,
                solana_transactions=transactions,
                relevant_address=address,
            )

        self.database.msg_aggregator.add_message(
            message_type=WSMessageType.TRANSACTION_STATUS,
            data={
                'address': address,
                'chain': SupportedBlockchain.SOLANA.value,
                'subtype': str(TransactionStatusSubType.SOLANA),
                'period': [start_ts, end_ts],
                'status': str(TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED),
            },
        )

    def query_rpc_for_single_tx(self, signature: Signature) -> SolanaTransaction | None:
        """Query the transaction with the given signature.
        May raise RemoteError if there is a problem with querying the external service.
        """
        if (response := self._query(method=lambda client: client.get_transaction(
            tx_sig=signature,
            max_supported_transaction_version=0,  # include the new v0 txs
        )).value) is None:
            log.error(f'Failed to get solana transaction {signature} from rpc')
            return None

        try:
            return self.deserialize_solana_tx_from_rpc(raw_tx=response)
        except DeserializationError as e:
            log.error(e)
            return None

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
            (account_info := self._get_raw_account_info(pubkey=alt.account_key)) is None or
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
    ) -> SolanaTransaction:
        """Deserialize a solana transaction from the RPC response.
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
            account_keys = [SolanaAddress(str(pubkey)) for pubkey in message.account_keys]
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

            return SolanaTransaction(
                fee=raw_tx.transaction.meta.fee,
                slot=raw_tx.slot,
                success=raw_tx.transaction.meta.err is None,
                signature=raw_tx.transaction.transaction.signatures[0],
                block_time=deserialize_timestamp(raw_tx.block_time),
                account_keys=account_keys,
                instructions=instructions,
            )
        except (IndexError, ValueError, DeserializationError) as e:
            raise DeserializationError(f'Failed to deserialize solana tx due to {e!s}') from e
