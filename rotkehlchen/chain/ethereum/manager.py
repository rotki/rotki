import logging
from typing import TYPE_CHECKING, Optional

from rotkehlchen.chain.ethereum.modules.curve.pools_cache import (
    clear_curve_pools_cache,
    update_curve_metapools_cache,
    update_curve_registry_pools_cache,
)
from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.errors.misc import InputError
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, GeneralCacheType
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

from .decoding.decoder import EthereumTransactionDecoder
from .tokens import EthereumTokens
from .utils import should_update_protocol_cache

if TYPE_CHECKING:

    from rotkehlchen.chain.ethereum.decoding.decoder import EVMTransactionDecoder

    from .node_inquirer import EthereumInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


CURVE_POOLS_MAPPING_TYPE = dict[
    ChecksumEvmAddress,  # lp token address
    tuple[
        ChecksumEvmAddress,  # pool address
        list[ChecksumEvmAddress],  # list of coins addresses
        Optional[list[ChecksumEvmAddress]],  # optional list of underlying coins addresses
    ],
]


class EthereumManager(EvmManager, LockableQueryMixIn):
    """EthereumManager inherits from EvmManager and defines Ethereum-specific methods
    such as curve cache manipulation."""
    def __init__(
            self,
            node_inquirer: 'EthereumInquirer',
    ) -> None:
        transactions = EthereumTransactions(
            ethereum_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=EthereumTokens(
                database=node_inquirer.database,
                ethereum_inquirer=node_inquirer,
            ),
            transactions_decoder=EthereumTransactionDecoder(
                database=node_inquirer.database,
                ethereum_inquirer=node_inquirer,
                transactions=transactions,
            ),
        )
        self.node_inquirer: 'EthereumInquirer'  # just to make the type specific

    def _update_curve_decoder(self, tx_decoder: 'EVMTransactionDecoder') -> None:
        try:
            curve_decoder = tx_decoder.decoders['Curve']
        except KeyError as e:
            raise InputError(
                'Expected to find Curve decoder but it was not loaded. '
                'Please open an issue on github.com/rotki/rotki/issues if you saw this.',
            ) from e
        new_mappings = curve_decoder.reload()
        tx_decoder.rules.address_mappings.update(new_mappings)

    @protect_with_lock()
    def curve_protocol_cache_is_queried(
            self,
            tx_decoder: Optional['EVMTransactionDecoder'],
    ) -> bool:
        """
        Make sure that information that needs to be queried is queried and if not query it.
        Returns true if the cache was modified or false otherwise.
        If the tx_decoder provided is None no information for the decoders is reloaded
        Updates curve pools cache.
        1. Deletes all previous cache values
        2. Queries information about curve pools' addresses, lp tokens and used coins
        3. Saves queried information in the cache in globaldb
        """
        if should_update_protocol_cache(GeneralCacheType.CURVE_LP_TOKENS) is False:
            if tx_decoder is not None:
                self._update_curve_decoder(tx_decoder)
            return False

        curve_address_provider = self.node_inquirer.contracts.contract('CURVE_ADDRESS_PROVIDER')
        # Using shared cursor to not end up having partially populated cache
        with GlobalDBHandler().conn.write_ctx() as write_cursor:
            # Delete current cache. Need to do this in case curve removes some pools
            clear_curve_pools_cache(write_cursor=write_cursor)
            # write new values to the cache
            update_curve_registry_pools_cache(
                write_cursor=write_cursor,
                ethereum=self.node_inquirer,
                curve_address_provider=curve_address_provider,
            )
            update_curve_metapools_cache(
                write_cursor=write_cursor,
                ethereum=self.node_inquirer,
                curve_address_provider=curve_address_provider,
            )

        if tx_decoder is not None:
            self._update_curve_decoder(tx_decoder)

        return True
