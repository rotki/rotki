import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Final, TypeVar

import gevent
from httpx import HTTPStatusError, ReadTimeout
from solana.exceptions import SolanaRpcException
from solana.rpc.api import Client
from solders.pubkey import Pubkey

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
    get_extension_data,
    get_metadata_account,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress, SupportedBlockchain

from .constants import METADATA_LAYOUT_2022, METADATA_LAYOUT_LEGACY, METADATA_PROGRAM_IDS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.greenlets.manager import GreenletManager

R = TypeVar('R')
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

INITIAL_BACKOFF: Final = 4
BACKOFF_MULTIPLIER: Final = 2
MAX_RETRIES: Final = 3


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

    def get_token_mint_info(self, token_address: SolanaAddress) -> MintInfo | None:
        """Query the mint info for the given token address.
        Returns the mint info or None if there was an error.
        """
        try:
            return deserialize_mint(
                mint_data=self.get_raw_account_info(pubkey=Pubkey.from_string(token_address)),
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
