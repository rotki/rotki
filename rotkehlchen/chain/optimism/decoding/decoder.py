import logging
from typing import TYPE_CHECKING, Optional
from rotkehlchen.chain.evm.decoding.base import BaseDecoderToolsWithDSProxy

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.evm.structures import EvmTxReceipt
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, OUTGOING_EVENT_TYPES
from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.optimismtx import DBOptimismTx
from rotkehlchen.db.filtering import OptimismTransactionsFilterQuery
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash
from rotkehlchen.utils.misc import from_wei

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.evm.decoding.structures import EnricherContext
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.optimism.transactions import OptimismTransactions
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismTransactionDecoder(EVMTransactionDecoder):

    def __init__(
            self,
            database: 'DBHandler',
            optimism_inquirer: 'OptimismInquirer',
            transactions: 'OptimismTransactions',
    ):
        super().__init__(
            database=database,
            evm_inquirer=optimism_inquirer,
            transactions=transactions,
            value_asset=A_ETH.resolve_to_asset_with_oracles(),
            event_rules=[],
            misc_counterparties=[],
            base_tools=BaseDecoderToolsWithDSProxy(
                database=database,
                evm_inquirer=optimism_inquirer,
                is_non_conformant_erc721_fn=self._is_non_conformant_erc721,
                address_is_exchange_fn=self._address_is_exchange,
            ),
        )
        self.dbevmtx = DBOptimismTx(database)

    # -- methods that need to be implemented by child classes --

    def _enrich_protocol_tranfers(self, context: 'EnricherContext') -> TransferEnrichmentOutput:  # pylint: disable=unused-argument # noqa: E501
        return FAILED_ENRICHMENT_OUTPUT

    @staticmethod
    def _is_non_conformant_erc721(address: ChecksumEvmAddress) -> bool:  # pylint: disable=unused-argument # noqa: E501
        return False

    @staticmethod
    def _address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:  # pylint: disable=unused-argument # noqa: E501
        return None

    def _maybe_decode_simple_transactions(
            self,
            tx: OptimismTransaction,
            tx_receipt: EvmTxReceipt,
    ) -> list['EvmEvent']:
        """Decodes normal ETH transfers, internal transactions and gas cost payments"""
        events: list['EvmEvent'] = []
        # check for gas spent
        direction_result = self.base.decode_direction(tx.from_address, tx.to_address)
        if direction_result is not None:
            event_type, location_label, _, _, _ = direction_result
            if event_type in OUTGOING_EVENT_TYPES:
                log.debug(f"searchme type: {type(tx)}, tx: {tx}")
                eth_burned_as_gas = from_wei(FVal(tx.gas_used * tx.gas_price + tx.l1_fee))
                events.append(self.base.make_event_next_index(
                    tx_hash=tx.tx_hash,
                    timestamp=tx.timestamp,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=self.value_asset,
                    balance=Balance(amount=eth_burned_as_gas),
                    location_label=location_label,
                    notes=f'Burned {eth_burned_as_gas} {self.value_asset.symbol} for gas',
                    counterparty=CPT_GAS,
                ))

        # Decode internal transactions after gas so gas is always 0 indexed
        self._maybe_decode_internal_transactions(
            tx=tx,
            tx_receipt=tx_receipt,
            events=events,
        )

        if tx_receipt.status is False or direction_result is None:
            # Not any other action to do for failed transactions or transaction where
            # any tracked address is not involved
            return events

        # now decode the actual transaction eth transfer itself
        amount = ZERO if tx.value == 0 else from_wei(FVal(tx.value))
        if tx.to_address is None:
            if not self.base.is_tracked(tx.from_address):
                return events

            events.append(self.base.make_event_next_index(  # contract deployment
                tx_hash=tx.tx_hash,
                timestamp=tx.timestamp,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.DEPLOY,
                asset=self.value_asset,
                balance=Balance(amount=amount),
                location_label=tx.from_address,
                notes='Contract deployment',
                address=None,  # TODO: Find out contract address
            ))
            return events

        if amount == ZERO:
            return events

        if (eth_event := self._get_eth_transfer_event(tx)) is not None:
            events.append(eth_event)
        return events
    

    def decode_transaction_hashes(
            self,
            ignore_cache: bool,
            tx_hashes: Optional[list[EVMTxHash]],
    ) -> list['EvmEvent']:
        """Make sure that receipts are pulled + events decoded for the given transaction hashes.

        The transaction hashes must exist in the DB at the time of the call

        May raise:
        - DeserializationError if there is a problem with conacting a remote to get receipts
        - RemoteError if there is a problem with contacting a remote to get receipts
        - InputError if the transaction hash is not found in the DB
        """
        events: list['EvmEvent'] = []
        refresh_balances = False
        with self.database.conn.read_ctx() as cursor:
            self.reload_data(cursor)
            # If no transaction hashes are passed, decode all transactions.
            if tx_hashes is None:
                tx_hashes = []
                cursor.execute(
                    'SELECT tx_hash FROM evm_transactions WHERE chain_id=?', #does this need to be changed for optimism_transactions?
                    (self.evm_inquirer.chain_id.serialize_for_db(),),
                )
                for entry in cursor:
                    tx_hashes.append(EVMTxHash(entry[0]))

        for tx_hash in tx_hashes:
            try:
                receipt = self.transactions.get_or_query_transaction_receipt(tx_hash)
            except RemoteError as e:
                raise InputError(f'{self.evm_inquirer.chain_name} hash {tx_hash.hex()} does not correspond to a transaction') from e  # noqa: E501

            # TODO: Change this if transaction filter query can accept multiple hashes
            with self.database.conn.read_ctx() as cursor:
                txs = self.dbevmtx.get_optimism_transactions(
                    cursor=cursor,
                    filter_=OptimismTransactionsFilterQuery.make(tx_hash=tx_hash, chain_id=self.evm_inquirer.chain_id),  # noqa: E501
                    has_premium=True,  # ignore limiting here
                )
            new_events, new_refresh_balances = self._get_or_decode_transaction_events(
                transaction=txs[0],
                tx_receipt=receipt,
                ignore_cache=ignore_cache,
            )
            events.extend(new_events)
            if new_refresh_balances is True:
                refresh_balances = True

        self._post_process(refresh_balances=refresh_balances)
        return events