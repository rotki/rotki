import logging
from typing import TYPE_CHECKING, Union

from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmInternalTransaction, ExternalService, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismEtherscan(Etherscan):

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            database=database,
            msg_aggregator=msg_aggregator,
            chain=SupportedBlockchain.OPTIMISM,
            base_url='optimistic.etherscan.io',
            service=ExternalService.OPTIMISM_ETHERSCAN,
        )

    def _additional_transaction_processing(
            self,
            tx: Union[OptimismTransaction, EvmInternalTransaction],  # type: ignore[override]
    ) -> Union[OptimismTransaction, EvmInternalTransaction]:
        if not isinstance(tx, EvmInternalTransaction):
            # TODO: write this tx_receipt to DB so it doesn't need to be queried again
            # https://github.com/rotki/rotki/pull/6359#discussion_r1252850465
            tx_receipt = self.get_transaction_receipt(tx.tx_hash)
            if tx_receipt is not None:
                l1_fee = int(tx_receipt['l1Fee'], 16)
            else:
                l1_fee = 0
                log.error(f'Could not query receipt for optimism transaction {tx.tx_hash.hex()}. Using 0 l1 fee')  # noqa: E501

            tx = OptimismTransaction(
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
