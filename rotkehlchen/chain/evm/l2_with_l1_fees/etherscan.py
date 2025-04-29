import logging
from abc import ABC
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.l2_with_l1_fees.types import (
    L2WithL1FeesTransaction,
    SupportedL2WithL1FeesType,
)
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmInternalTransaction

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class L2WithL1FeesEtherscan(Etherscan, ABC):
    """
    An intermediary etherscan class to be inherited by L2 chains
    that have an extra L1 Fee structure.
    """

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            chain: SupportedL2WithL1FeesType,
    ) -> None:
        super().__init__(
            database=database,
            msg_aggregator=msg_aggregator,
            chain=chain,
        )

    def _additional_transaction_processing(
            self,
            tx: L2WithL1FeesTransaction | EvmInternalTransaction,  # type: ignore[override]
    ) -> L2WithL1FeesTransaction | EvmInternalTransaction:
        if not isinstance(tx, EvmInternalTransaction):
            # TODO: write this tx_receipt to DB so it doesn't need to be queried again
            # https://github.com/rotki/rotki/pull/6359#discussion_r1252850465
            tx_receipt = self.get_transaction_receipt(tx.tx_hash)
            l1_fee = 0
            if tx_receipt is not None:
                if 'l1Fee' in tx_receipt:
                    # system tx like deposits don't have the l1fee attribute
                    # https://github.com/ethereum-optimism/optimism/blob/84ead32601fb825a060cde5a6635be2e8aea1a95/specs/deposits.md  # noqa: E501
                    l1_fee = int(tx_receipt['l1Fee'], 16)
            else:
                log.error(f'Could not query receipt for {self.chain.name.lower()} transaction {tx.tx_hash.hex()}. Using 0 l1 fee')  # noqa: E501

            tx = L2WithL1FeesTransaction(
                tx_hash=tx.tx_hash,
                chain_id=tx.chain_id,
                timestamp=tx.timestamp,
                block_number=tx.block_number,
                from_address=tx.from_address,
                to_address=tx.to_address,
                value=tx.value,
                gas=tx.gas,
                gas_price=tx.gas_price,
                gas_used=tx.gas_used,
                input_data=tx.input_data,
                nonce=tx.nonce,
                l1_fee=l1_fee,
            )
        return tx
