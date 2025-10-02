from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from solders.solders import Signature

from rotkehlchen.chain.decoding.decoder import TransactionDecoder
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.tools import SolanaDecoderTools
from rotkehlchen.chain.solana.types import SolanaTransaction
from rotkehlchen.chain.solana.utils import lamports_to_sol
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.db.filtering import SolanaTransactionsNotDecodedFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.types import SolanaAddress, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
    from rotkehlchen.chain.solana.transactions import SolanaTransactions
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.premium.premium import Premium


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class SolanaDecodingRules:
    address_mappings: dict[SolanaAddress, tuple[Any, ...]]

    def __add__(self, other: 'SolanaDecodingRules') -> 'SolanaDecodingRules':
        if not isinstance(other, SolanaDecodingRules):
            raise TypeError(
                f'Can only add SolanaDecodingRules to SolanaDecodingRules. Got {type(other)}',
            )

        return SolanaDecodingRules(
            address_mappings=self.address_mappings | other.address_mappings,
        )


class SolanaTransactionDecoder(TransactionDecoder[SolanaTransaction, SolanaDecodingRules, SolanaDecoderInterface, Signature, SolanaEvent, SolanaTransaction, SolanaDecoderTools, DBSolanaTx, SolanaTransactionsNotDecodedFilterQuery]):  # noqa: E501

    def __init__(
            self,
            database: 'DBHandler',
            node_inquirer: 'SolanaInquirer',
            transactions: 'SolanaTransactions',
            base_tools: 'SolanaDecoderTools',
            premium: 'Premium | None' = None,
    ):
        self.node_inquirer = node_inquirer
        self.transactions = transactions
        self.dbevents = DBHistoryEvents(database)
        super().__init__(
            database=database,
            dbtx=DBSolanaTx(database),
            tx_not_decoded_filter_query_class=SolanaTransactionsNotDecodedFilterQuery,
            chain_name=SupportedBlockchain.SOLANA.name.lower(),
            value_asset=A_SOL.resolve_to_asset_with_oracles(),
            rules=SolanaDecodingRules(address_mappings={}),
            premium=premium,
            base_tools=base_tools,
            misc_counterparties=[],
            possible_decoding_exceptions=(),
        )

    def _add_builtin_decoders(self, rules: SolanaDecodingRules) -> None:
        # TODO: add native/token transfer decoders here
        ...

    def _add_single_decoder(
            self,
            class_name: str,
            decoder_class: type[SolanaDecoderInterface],
            rules: SolanaDecodingRules,
    ) -> None:
        # TODO: initialize a single decoder here
        ...

    @staticmethod
    def _load_default_decoding_rules() -> SolanaDecodingRules:
        return SolanaDecodingRules(address_mappings={})

    def _load_transaction_context(
            self,
            cursor: 'DBCursor',
            tx_hash: Signature,
    ) -> SolanaTransaction:
        return self.transactions.get_or_create_transaction(signature=tx_hash)

    def _decode_transaction_from_context(
            self,
            context: SolanaTransaction,
            ignore_cache: bool,
            delete_customized: bool,
    ) -> tuple[list[SolanaEvent], bool, set[str] | None]:
        # TODO: load existing events from the db or do decoding here
        return [], False, None

    def _calculate_fees(self, tx: SolanaTransaction) -> FVal:
        return lamports_to_sol(tx.fee)
