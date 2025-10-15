import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.convex.constants import (
    BOOSTER,
    CONVEX_ABRAS_HEX,
    CONVEX_CPT_DETAILS,
    CONVEX_VIRTUAL_REWARDS,
    CPT_CONVEX,
    CVX_LOCK_WITHDRAWN,
    CVX_LOCKER,
    CVX_LOCKER_V2,
    CVX_REWARDS,
    CVXCRV_REWARDS,
    REWARD_TOPICS,
    WITHDRAWAL_TOPICS,
)
from rotkehlchen.chain.ethereum.modules.convex.convex_cache import (
    query_convex_data,
    read_convex_data_from_cache,
)
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER, STAKED
from rotkehlchen.chain.evm.decoding.interfaces import (
    EvmDecoderInterface,
    ReloadableCacheDecoderMixin,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    DecoderContext,
    EnricherContext,
    EvmDecodingOutput,
    TransferEnrichmentOutput,
)
from rotkehlchen.constants.assets import A_CRV, A_CVX
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.history.events.structures.base import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

REWARD_ADDED = b'\xde\x88\xa9"\xe0\xd3\xb8\x8b$\xe9b>\xfe\xb4d\x91\x9ck\xf9\xf6hW\xa6^+\xfc\xf2\xce\x87\xa9C='  # noqa: E501


class ConvexDecoder(EvmDecoderInterface, ReloadableCacheDecoderMixin):
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        ReloadableCacheDecoderMixin.__init__(
            self,
            evm_inquirer=ethereum_inquirer,
            cache_type_to_check_for_freshness=CacheType.CONVEX_POOL_ADDRESS,
            query_data_method=query_convex_data,
            read_data_from_cache_method=read_convex_data_from_cache,
        )
        self.cvx = A_CVX.resolve_to_evm_token()

    @property
    def pools(self) -> dict[ChecksumEvmAddress, str]:
        assert isinstance(self.cache_data[0], dict), 'ConvexDecoder cache_data[0] is not a dict'
        return self.cache_data[0]

    def _cache_mapping_methods(self) -> tuple[Callable[[DecoderContext], EvmDecodingOutput]]:
        return (self._decode_pool_events,)

    def _decode_pool_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == REWARD_ADDED:
            return self._decode_compound_crv(context=context)

        return self._decode_gauge_events(context=context)

    def _decode_compound_crv(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode compounding of CRV in convex pools"""
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_CRV
            ):
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_CONVEX
                event.notes = f'Claim {event.amount} {event.asset.resolve_to_crypto_asset().symbol} after compounding Convex pool'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_gauge_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """
        Decode events in convex gauges:
        - deposits/withdrawals
        - claim rewards
        """
        amount_raw = int.from_bytes(context.tx_log.data[0:32])
        interacted_address = bytes_to_address(context.tx_log.topics[1])
        found_event_modifying_balances, found_return_wrapped = False, False
        # in the case of withdrawing CVX from an expired lock the withdrawn event
        # is emitted before the transfer events and when iterating over the decoded events
        # we haven't processed the transfer yet so it can't be decoded. To cover that case
        # we use a post processing event only for that topic
        matched_counterparty = CPT_CONVEX if context.tx_log.topics[0] == CVX_LOCK_WITHDRAWN else None  # noqa: E501

        for event in context.decoded_events:
            try:
                crypto_asset = event.asset.resolve_to_crypto_asset()
            except (UnknownAsset, WrongAssetType):
                self.notify_user(event=event, counterparty=CPT_CONVEX)
                continue

            amount = asset_normalized_value(amount_raw, crypto_asset)
            if (
                event.location_label == context.transaction.from_address == interacted_address is False or  # noqa: E501
                (event.address != ZERO_ADDRESS and event.amount != amount)
            ):
                continue
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                found_event_modifying_balances = True
                if event.address == ZERO_ADDRESS:
                    found_return_wrapped = True
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.counterparty = CPT_CONVEX
                    if context.tx_log.address in self.pools:
                        event.notes = f'Return {event.amount} {crypto_asset.symbol} to convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
                    else:
                        event.notes = f'Return {event.amount} {crypto_asset.symbol} to convex'
                else:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.counterparty = CPT_CONVEX
                    if context.tx_log.address in self.pools:
                        event.notes = f'Deposit {event.amount} {crypto_asset.symbol} into convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
                    else:
                        event.notes = f'Deposit {event.amount} {crypto_asset.symbol} into convex'

                    # in this case store information about the gauge in the extra details to use
                    # it during balances queries
                    for log_event in context.all_logs:
                        if log_event.topics[0] == STAKED:
                            deposit_amount_raw = int.from_bytes(context.tx_log.data[0:32])
                            staking_address = bytes_to_address(log_event.topics[1])
                            if deposit_amount_raw == amount_raw and staking_address == event.location_label:  # noqa: E501
                                event.extra_data = {'gauge_address': log_event.address}
                                break

            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ):
                if context.tx_log.topics[0] in WITHDRAWAL_TOPICS:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED if found_return_wrapped else HistoryEventSubType.REMOVE_ASSET  # noqa: E501
                    event.counterparty = CPT_CONVEX
                    found_event_modifying_balances = True
                    if context.tx_log.address in self.pools:
                        event.notes = f'Withdraw {event.amount} {crypto_asset.symbol} from convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
                    else:
                        event.notes = f'Withdraw {event.amount} {crypto_asset.symbol} from convex'
                elif context.tx_log.topics[0] in REWARD_TOPICS:
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.counterparty = CPT_CONVEX
                    found_event_modifying_balances = True
                    if context.tx_log.address in self.pools:
                        event.notes = f'Claim {event.amount} {crypto_asset.symbol} reward from convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
                    else:
                        event.notes = f'Claim {event.amount} {crypto_asset.symbol} reward from convex'  # noqa: E501
        return EvmDecodingOutput(
            refresh_balances=found_event_modifying_balances,
            matched_counterparty=matched_counterparty,
        )

    def _check_lock_withdrawal_funds(
            self,
            transaction: 'EvmTransaction',  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """
        Process unlocked CVX withdrawals.

        The withdrawal event needs to be handled after all the events get decoded since it is
        emitted before the transfer events get processed. We gather all the withdraw amounts
        that don't relock from the log event data and then match them against
        the receive events of CVX.
        """
        withdrawals_log_entries = filter(lambda x: x.topics[0] == CVX_LOCK_WITHDRAWN, all_logs)
        amounts_withdrawn = [
            asset_normalized_value(int.from_bytes(tx_log.data[0:32]), self.cvx)
            for tx_log in withdrawals_log_entries
            if bool(int.from_bytes(tx_log.data[32:64])) is False  # false means not relocked
        ]

        for event in decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == A_CVX and
                event.amount in amounts_withdrawn
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_CONVEX
                event.notes = f'Unlock {event.amount} {self.cvx.symbol} from convex'

                amounts_withdrawn.remove(event.amount)
                if len(amounts_withdrawn) == 0:
                    break  # stop as soon as we have processed all the unlock events
        else:
            log.error(f'Did not process all the expected CVX unlock withdrawals for {transaction.tx_hash.hex()}')  # noqa: E501

        return decoded_events

    def _maybe_enrich_convex_transfers(self, context: EnricherContext) -> TransferEnrichmentOutput:
        """
        Used for rewards paid with abracadabras. Problem is that the transfer event in this
        case happens at the end of the transaction and there is no reward event after it to
        emit event processing.

        May raise:
        - UnknownAsset
        - WrongAssetType
        """
        if (
            context.tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
            context.tx_log.topics[1] in CONVEX_ABRAS_HEX and
            context.event.location_label == context.transaction.from_address and
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE
        ):
            crypto_asset = context.event.asset.resolve_to_crypto_asset()
            context.event.event_subtype = HistoryEventSubType.REWARD
            if context.tx_log.address in self.pools:
                context.event.notes = f'Claim {context.event.amount} {crypto_asset.symbol} reward from convex {self.pools[context.tx_log.address]} pool'  # noqa: E501
            else:
                context.event.notes = f'Claim {context.event.amount} {crypto_asset.symbol} reward from convex'  # noqa: E501
            context.event.counterparty = CPT_CONVEX
            return TransferEnrichmentOutput(matched_counterparty=CPT_CONVEX)
        return FAILED_ENRICHMENT_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        decoder_mappings = {
            BOOSTER: (self._decode_pool_events,),
            CVX_LOCKER: (self._decode_pool_events,),
            CVX_LOCKER_V2: (self._decode_pool_events,),
            CVX_REWARDS: (self._decode_pool_events,),
            CVXCRV_REWARDS: (self._decode_pool_events,),
        }
        virtual_rewards = dict.fromkeys(CONVEX_VIRTUAL_REWARDS, (self._decode_pool_events,))
        decoder_mappings.update(virtual_rewards)
        return decoder_mappings

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CONVEX_CPT_DETAILS,)

    def enricher_rules(self) -> list[Callable]:
        return [self._maybe_enrich_convex_transfers]

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {CPT_CONVEX: [(0, self._check_lock_withdrawal_funds)]}
