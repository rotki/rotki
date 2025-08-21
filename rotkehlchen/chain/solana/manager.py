import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, TypeVar

from httpx import HTTPError
from solana.rpc.api import Client
from solana.rpc.core import RPCException
from solders.pubkey import Pubkey

from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.chain.mixins.rpc_nodes import SolanaRPCMixin
from rotkehlchen.chain.solana.utils import lamports_to_sol
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.greenlets.manager import GreenletManager

R = TypeVar('R')
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
            call_order: Sequence[WeightedNode],
    ) -> R:
        """Use the provided call order to request method from solana"""
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

            try:
                return method(rpc_node.rpc_client)
            except (HTTPError, RPCException) as e:
                log.error(f'Failed to call {node_info.name} due to {e}')

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
            call_order=self.default_call_order(),
        )

        result = {}
        for account, entry in zip(accounts, response.value, strict=False):
            if entry is None or entry.lamports == 0:
                log.debug(f'Found no account entry in balances for {account}. Skipping')
                result[account] = ZERO
            else:
                result[account] = lamports_to_sol(entry.lamports)

        return result
