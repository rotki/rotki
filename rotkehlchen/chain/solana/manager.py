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
from spl.token._layouts import ACCOUNT_LAYOUT
from spl.token.constants import TOKEN_2022_PROGRAM_ID, TOKEN_PROGRAM_ID

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
    get_extension_data,
    get_metadata_account,
    is_token_nft,
    lamports_to_sol,
    unpack_mint,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress, SupportedBlockchain, TokenKind
from rotkehlchen.utils.misc import bytes_to_solana_address

from .constants import METADATA_LAYOUT_2022, METADATA_LAYOUT_LEGACY, METADATA_PROGRAM_IDS

if TYPE_CHECKING:
    from solders.solders import GetTokenAccountsByOwnerResp

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.greenlets.manager import GreenletManager

R = TypeVar('R')
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


INITIAL_BACKOFF: Final = 4
BACKOFF_MULTIPLIER: Final = 2
MAX_RETRIES: Final = 3


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
