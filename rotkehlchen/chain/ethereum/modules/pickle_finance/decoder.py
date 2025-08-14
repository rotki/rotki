import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import MerkleClaimDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    FAILED_ENRICHMENT_OUTPUT,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CORN_TOKEN_ID, CORNICHON_CLAIM, CPT_PICKLE

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class PickleFinanceDecoder(MerkleClaimDecoderInterface):

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
        self.pickle_contracts = set(GlobalDBHandler.get_addresses_by_protocol(
            chain_id=ethereum_inquirer.chain_id,
            protocol=CPT_PICKLE,
        ))

    def _maybe_enrich_pickle_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        Enrich transfer transactions to address for jar deposits and withdrawals
        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        crypto_asset = context.event.asset.resolve_to_crypto_asset()
        if not (
            bytes_to_address(context.tx_log.topics[2]) in self.pickle_contracts or
            bytes_to_address(context.tx_log.topics[1]) in self.pickle_contracts or
            context.tx_log.address in self.pickle_contracts
        ):
            return FAILED_ENRICHMENT_OUTPUT

        if (  # Deposit give asset
            context.event.event_type == HistoryEventType.SPEND and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.event.location_label == context.transaction.from_address and
            bytes_to_address(context.tx_log.topics[2]) in self.pickle_contracts
        ):
            if EvmToken(ethaddress_to_identifier(context.tx_log.address)) != context.event.asset:
                return FAILED_ENRICHMENT_OUTPUT
            amount_raw = int.from_bytes(context.tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=context.event.asset.resolve_to_crypto_asset(),
            )
            if context.event.amount == amount:
                context.event.event_type = HistoryEventType.DEPOSIT
                context.event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                context.event.counterparty = CPT_PICKLE
                context.event.notes = f'Deposit {context.event.amount} {crypto_asset.symbol} in pickle contract'  # noqa: E501
                return TransferEnrichmentOutput(matched_counterparty=CPT_PICKLE)
        elif (  # Deposit receive wrapped
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.tx_log.address in self.pickle_contracts
        ):
            amount_raw = int.from_bytes(context.tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=context.event.asset.resolve_to_crypto_asset(),
            )
            if context.event.amount == amount:
                context.event.event_type = HistoryEventType.RECEIVE
                context.event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                context.event.counterparty = CPT_PICKLE
                context.event.notes = f'Receive {context.event.amount} {crypto_asset.symbol} after depositing in pickle contract'  # noqa: E501
                context.event.address = context.tx_log.address
                return TransferEnrichmentOutput(matched_counterparty=CPT_PICKLE)
        elif (  # Withdraw send wrapped
            context.event.event_type == HistoryEventType.SPEND and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.event.location_label == context.transaction.from_address and
            bytes_to_address(context.tx_log.topics[2]) == ZERO_ADDRESS and
            bytes_to_address(context.tx_log.topics[1]) in context.transaction.from_address
        ):
            if context.event.asset != EvmToken(ethaddress_to_identifier(context.tx_log.address)):
                return FAILED_ENRICHMENT_OUTPUT
            amount_raw = int.from_bytes(context.tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=context.event.asset.resolve_to_crypto_asset(),
            )
            if context.event.amount == amount:
                context.event.event_type = HistoryEventType.SPEND
                context.event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                context.event.counterparty = CPT_PICKLE
                context.event.notes = f'Return {context.event.amount} {crypto_asset.symbol} to the pickle contract'  # noqa: E501
                context.event.address = context.tx_log.address
                return TransferEnrichmentOutput(matched_counterparty=CPT_PICKLE)
        elif (  # Withdraw receive asset
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.event.location_label == context.transaction.from_address and
            bytes_to_address(context.tx_log.topics[2]) == context.transaction.from_address and
            bytes_to_address(context.tx_log.topics[1]) in self.pickle_contracts
        ):
            if context.event.asset != EvmToken(ethaddress_to_identifier(context.tx_log.address)):
                return FAILED_ENRICHMENT_OUTPUT
            amount_raw = int.from_bytes(context.tx_log.data)
            amount = asset_normalized_value(
                amount=amount_raw,
                asset=context.event.asset.resolve_to_crypto_asset(),
            )
            if context.event.amount == amount:
                context.event.event_type = HistoryEventType.WITHDRAWAL
                context.event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                context.event.counterparty = CPT_PICKLE
                context.event.notes = f'Unstake {context.event.amount} {crypto_asset.symbol} from the pickle contract'  # noqa: E501
                return TransferEnrichmentOutput(matched_counterparty=CPT_PICKLE)

        return FAILED_ENRICHMENT_OUTPUT

    # -- DecoderInterface methods

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_pickle_transfers,
        ]

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            CORNICHON_CLAIM: (
                self._decode_merkle_claim,
                CPT_PICKLE,  # counterparty
                CORN_TOKEN_ID,  # token id
                18,  # token decimals
                'CORN from the pickle finance hack compensation airdrop',  # notes suffix
                'cornichon',
            ),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_PICKLE,
            label='Pickle Finance',
            image='pickle.svg',
        ),)
