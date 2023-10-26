from typing import TYPE_CHECKING, Callable

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import PICKLE_JAR_PROTOCOL
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_PICKLE

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


class PickleFinanceDecoder(DecoderInterface):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        jars = GlobalDBHandler().get_evm_tokens(
            chain_id=ethereum_inquirer.chain_id,
            protocol=PICKLE_JAR_PROTOCOL,
        )
        self.pickle_contracts = {jar.evm_address for jar in jars}

    def _maybe_enrich_pickle_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        Enrich tranfer transactions to address for jar deposits and withdrawals
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        crypto_asset = context.event.asset.resolve_to_crypto_asset()
        if not (
            hex_or_bytes_to_address(context.tx_log.topics[2]) in self.pickle_contracts or
            hex_or_bytes_to_address(context.tx_log.topics[1]) in self.pickle_contracts or
            context.tx_log.address in self.pickle_contracts
        ):
            return FAILED_ENRICHMENT_OUTPUT

        if (  # Deposit give asset
            context.event.event_type == HistoryEventType.SPEND and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.event.location_label == context.transaction.from_address and
            hex_or_bytes_to_address(context.tx_log.topics[2]) in self.pickle_contracts
        ):
            if EvmToken(ethaddress_to_identifier(context.tx_log.address)) != context.event.asset:
                return FAILED_ENRICHMENT_OUTPUT
            amount_raw = hex_or_bytes_to_int(context.tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=context.event.asset.resolve_to_crypto_asset(),
            )
            if context.event.balance.amount == amount:
                context.event.event_type = HistoryEventType.DEPOSIT
                context.event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                context.event.counterparty = CPT_PICKLE
                context.event.notes = f'Deposit {context.event.balance.amount} {crypto_asset.symbol} in pickle contract'  # noqa: E501
                return TransferEnrichmentOutput(matched_counterparty=CPT_PICKLE)
        elif (  # Deposit receive wrapped
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.tx_log.address in self.pickle_contracts
        ):
            amount_raw = hex_or_bytes_to_int(context.tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=context.event.asset.resolve_to_crypto_asset(),
            )
            if context.event.balance.amount == amount:
                context.event.event_type = HistoryEventType.RECEIVE
                context.event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                context.event.counterparty = CPT_PICKLE
                context.event.notes = f'Receive {context.event.balance.amount} {crypto_asset.symbol} after depositing in pickle contract'  # noqa: E501
                return TransferEnrichmentOutput(matched_counterparty=CPT_PICKLE)
        elif (  # Withdraw send wrapped
            context.event.event_type == HistoryEventType.SPEND and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.event.location_label == context.transaction.from_address and
            hex_or_bytes_to_address(context.tx_log.topics[2]) == ZERO_ADDRESS and
            hex_or_bytes_to_address(context.tx_log.topics[1]) in context.transaction.from_address
        ):
            if context.event.asset != EvmToken(ethaddress_to_identifier(context.tx_log.address)):
                return FAILED_ENRICHMENT_OUTPUT
            amount_raw = hex_or_bytes_to_int(context.tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=context.event.asset.resolve_to_crypto_asset(),
            )
            if context.event.balance.amount == amount:
                context.event.event_type = HistoryEventType.SPEND
                context.event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                context.event.counterparty = CPT_PICKLE
                context.event.notes = f'Return {context.event.balance.amount} {crypto_asset.symbol} to the pickle contract'  # noqa: E501
                return TransferEnrichmentOutput(matched_counterparty=CPT_PICKLE)
        elif (  # Withdraw receive asset
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.event.location_label == context.transaction.from_address and
            hex_or_bytes_to_address(context.tx_log.topics[2]) == context.transaction.from_address and  # noqa: E501
            hex_or_bytes_to_address(context.tx_log.topics[1]) in self.pickle_contracts
        ):
            if context.event.asset != EvmToken(ethaddress_to_identifier(context.tx_log.address)):
                return FAILED_ENRICHMENT_OUTPUT
            amount_raw = hex_or_bytes_to_int(context.tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=context.event.asset.resolve_to_crypto_asset(),
            )
            if context.event.balance.amount == amount:
                context.event.event_type = HistoryEventType.WITHDRAWAL
                context.event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                context.event.counterparty = CPT_PICKLE
                context.event.notes = f'Unstake {context.event.balance.amount} {crypto_asset.symbol} from the pickle contract'  # noqa: E501
                return TransferEnrichmentOutput(matched_counterparty=CPT_PICKLE)

        return FAILED_ENRICHMENT_OUTPUT

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_pickle_transfers,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_PICKLE,
            label='Pickle Finance',
            image='pickle.svg',
        ),)
