import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.active_management.manager import ActiveManager
from rotkehlchen.chain.evm.decoding.curve.curve_cache import (
    query_curve_data,
)
from rotkehlchen.chain.evm.types import RemoteDataQueryStatus
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress

if TYPE_CHECKING:
    from .accounting.aggregator import EVMAccountingAggregator
    from .decoding.decoder import EVMTransactionDecoder
    from .node_inquirer import EvmNodeInquirer
    from .tokens import EvmTokens
    from .transactions import EvmTransactions

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EvmManager:
    """EvmManager defines a basic implementation for EVM chains."""

    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            transactions: 'EvmTransactions',
            tokens: 'EvmTokens',
            transactions_decoder: 'EVMTransactionDecoder',
            accounting_aggregator: 'EVMAccountingAggregator',
    ) -> None:
        super().__init__()
        self.node_inquirer = node_inquirer
        self.transactions = transactions
        self.tokens = tokens
        self.transactions_decoder = transactions_decoder
        self.accounting_aggregator = accounting_aggregator
        self.active_management = ActiveManager(node_inquirer=node_inquirer)

    def get_historical_balance(
            self,
            address: ChecksumEvmAddress,
            block_number: int,
    ) -> FVal | None:
        """Attempts to get a historical eth balance from the local own node only.
        If there is no node or the node can't query historical balance (not archive) then
        returns None"""
        return self.node_inquirer.get_historical_balance(address, block_number)


class CurveManagerMixin:
    """Mixin for EVM chain managers that need to query Curve data"""

    def assure_curve_cache_is_queried_and_decoder_updated(
            self,
            node_inquirer: 'EvmNodeInquirer',
            transactions_decoder: 'EVMTransactionDecoder',
    ) -> None:
        """
        Make sure that information that needs to be queried is queried and if not query it.

        1. Deletes all previous cache values
        2. Queries information about curve pools' addresses, lp tokens and used coins
        3. Saves queried information in the cache in globaldb

        Also updates the curve decoder
        """
        if node_inquirer.ensure_cache_data_is_updated(
            cache_type=CacheType.CURVE_LP_TOKENS,
            query_method=query_curve_data,
            chain_id=node_inquirer.chain_id,
            cache_key_parts=(str(node_inquirer.chain_id.serialize_for_db()),),
        ) != RemoteDataQueryStatus.NEW_DATA:
            return

        try:
            curve_decoder = transactions_decoder.decoders['Curve']
        except KeyError as e:
            raise InputError(
                'Expected to find Curve decoder but it was not loaded. '
                'Please open an issue on github.com/rotki/rotki/issues if you saw this.',
            ) from e
        new_mappings = curve_decoder.reload_data()  # type: ignore  # we know type here
        if new_mappings:
            transactions_decoder.rules.address_mappings.update(new_mappings)
