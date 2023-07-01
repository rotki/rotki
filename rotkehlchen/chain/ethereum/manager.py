import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.transactions import EthereumTransactions
from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.errors.misc import InputError
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .decoding.decoder import EthereumTransactionDecoder
from .tokens import EthereumTokens

if TYPE_CHECKING:
    from .node_inquirer import EthereumInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthereumManager(EvmManager):
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

    def assure_curve_cache_is_queried_and_decoder_updated(self) -> None:
        """
        Make sure that information that needs to be queried is queried and if not query it.

        1. Deletes all previous cache values
        2. Queries information about curve pools' addresses, lp tokens and used coins
        3. Saves queried information in the cache in globaldb

        Also updates the curve decoder
        """
        if self.node_inquirer.assure_curve_protocol_cache_is_queried() is False:
            return

        try:
            curve_decoder = self.transactions_decoder.decoders['Curve']
        except KeyError as e:
            raise InputError(
                'Expected to find Curve decoder but it was not loaded. '
                'Please open an issue on github.com/rotki/rotki/issues if you saw this.',
            ) from e
        new_mappings = curve_decoder.reload_data()  # type: ignore  # we know type here
        if new_mappings:
            self.transactions_decoder.rules.address_mappings.update(new_mappings)
