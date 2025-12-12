import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Literal

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.constants import (
    BURN_TOPIC,
    DEFAULT_TOKEN_DECIMALS,
    MINT_TOPIC,
    WITHDRAW_TOPIC_V2,
    ZERO_ADDRESS,
)
from rotkehlchen.chain.evm.decoding.interfaces import (
    EvmDecoderInterface,
    ReloadablePoolsAndGaugesDecoderMixin,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.uniswap.v2.constants import (
    UNISWAP_V2_SWAP_SIGNATURE as SWAP_V1,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.velodrome.constants import (
    CLAIM_REWARDS_V2,
    GAUGE_DEPOSIT_V2,
    REMOVE_LIQUIDITY_EVENT_V2,
    SWAP_V2,
    VOTER_CLAIM_REWARDS,
    VOTER_VOTED,
    VOTING_ESCROW_CREATE_LOCK,
    VOTING_ESCROW_METADATA_UPDATE,
    VOTING_ESCROW_WITHDRAW,
)
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    query_velodrome_like_data,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.types import CacheType, ChecksumEvmAddress, GeneralCacheType, TokenKind
from rotkehlchen.utils.misc import bytes_to_address, timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class VelodromeLikeDecoder(EvmDecoderInterface, ReloadablePoolsAndGaugesDecoderMixin):
    """A decoder class for velodrome-like related events."""

    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer | BaseInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            counterparty: Literal['velodrome', 'aerodrome'],
            voting_escrow_address: ChecksumEvmAddress,
            voter_address: ChecksumEvmAddress,
            routers: set[ChecksumEvmAddress],
            token_symbol: Literal['AERO', 'VELO'],
            gauge_bribes_cache_type: GeneralCacheType,
            gauge_fees_cache_type: GeneralCacheType,
            pool_cache_type: CacheType,
            read_fn: Callable[[], tuple[set[ChecksumEvmAddress], set[ChecksumEvmAddress]]],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        ReloadablePoolsAndGaugesDecoderMixin.__init__(
            self,
            evm_inquirer=evm_inquirer,
            cache_type_to_check_for_freshness=pool_cache_type,
            query_data_method=query_velodrome_like_data,
            read_data_from_cache_method=read_fn,
        )
        self.counterparty = counterparty
        self.protocol_addresses = routers  # protocol_addresses are updated with pools in post_cache_update_callback  # noqa: E501
        self.voting_escrow_address = voting_escrow_address
        self.gauge_bribes_cache_type = gauge_bribes_cache_type
        self.gauge_fees_cache_type = gauge_fees_cache_type
        self.voter_address = voter_address
        self.token_symbol = token_symbol

    @property
    def pools(self) -> set[ChecksumEvmAddress]:
        assert isinstance(self.cache_data[0], set), f'{self.counterparty} Decoder cache_data[0] is not a set'  # noqa: E501
        return self.cache_data[0]

    def post_cache_update_callback(self) -> None:
        self.protocol_addresses.update(self.pools)

    def _decode_add_liquidity_events(
            self,
            tx_log: 'EvmTxReceiptLog',
            decoded_events: list['EvmEvent'],
    ) -> EvmDecodingOutput:
        """
        Decodes events that add liquidity to a (velo/aero)drome v1 or v2 pool.

        It can raise
        - UnknownAsset if the asset identifier is not known
        - WrongAssetType if the asset is not of the correct type
        """
        for event in decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Deposit {event.amount} {crypto_asset.symbol} in {self.counterparty} pool {event.address}'  # noqa: E501
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == ZERO_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} after depositing in {self.counterparty} pool {tx_log.address}'  # noqa: E501
                GlobalDBHandler.set_tokens_protocol_if_missing(
                    tokens=[event.asset.resolve_to_evm_token()],
                    new_protocol=self.counterparty,
                )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_remove_liquidity_events(
            self,
            tx_log: 'EvmTxReceiptLog',
            decoded_events: list['EvmEvent'],
    ) -> EvmDecodingOutput:
        """Decodes events that remove liquidity from a (velo/aero)drome v1 or v2 pool"""
        for event in decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Return {event.amount} {crypto_asset.symbol}'
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address in self.pools
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.counterparty = self.counterparty
                event.notes = f'Remove {event.amount} {crypto_asset.symbol} from {self.counterparty} pool {tx_log.address}'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_swap(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes events that swap eth or tokens in a (velo/aero)drome v1 or v2 pool"""
        spend_event, receive_event = None, None
        for event in context.decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                    ((event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE) or  # noqa: E501
                    (event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND))  # noqa: E501
                    and event.address in self.protocol_addresses
            ):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
                event.counterparty = self.counterparty
                event.notes = f'Swap {event.amount} {crypto_asset.symbol} in {self.counterparty}'
                spend_event = event
            elif ((
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE
            ) or ((
                event.event_type == HistoryEventType.TRADE and
                event.event_subtype == HistoryEventSubType.RECEIVE
            ) and event.address in self.protocol_addresses)):
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
                event.counterparty = self.counterparty
                event.notes = f'Receive {event.amount} {crypto_asset.symbol} as the result of a swap in {self.counterparty}'  # noqa: E501
                receive_event = event

        if spend_event is None or receive_event is None:
            log.error(
                f'A swap in {self.counterparty} pool must have both a spend and a receive event '
                'but one or both of them are missing for transaction hash: '
                f'{context.transaction.tx_hash.hex()}. '
                f'Spend event: {spend_event}, receive event: {receive_event}.',
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[spend_event, receive_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

    def _decode_pool_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes transactions that interact with a (velo/aero)drome v1 or v2 pool"""
        if context.tx_log.topics[0] in (REMOVE_LIQUIDITY_EVENT_V2, BURN_TOPIC):
            return self._decode_remove_liquidity_events(
                tx_log=context.tx_log,
                decoded_events=context.decoded_events,
            )
        if context.tx_log.topics[0] == MINT_TOPIC:
            return self._decode_add_liquidity_events(
                tx_log=context.tx_log,
                decoded_events=context.decoded_events,
            )
        if context.tx_log.topics[0] in (SWAP_V2, SWAP_V1):
            return self._decode_swap(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_gauge_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """
        Decodes transactions that interact with a (velo/aero)drome v2 gauge.
        Velodrome v1 had no gauges.
        """
        if context.tx_log.topics[0] not in (GAUGE_DEPOSIT_V2, WITHDRAW_TOPIC_V2, CLAIM_REWARDS_V2):
            return DEFAULT_EVM_DECODING_OUTPUT

        user_or_contract_address = bytes_to_address(context.tx_log.topics[1])
        gauge_address = context.tx_log.address
        raw_amount = int.from_bytes(context.tx_log.data)
        found_event_modifying_balances = False
        for event in context.decoded_events:
            crypto_asset = event.asset.resolve_to_crypto_asset()
            if (
                event.location_label == user_or_contract_address and
                event.address == gauge_address and
                event.amount == asset_normalized_value(amount=raw_amount, asset=crypto_asset)
            ):
                event.counterparty = self.counterparty
                found_event_modifying_balances = True
                if context.tx_log.topics[0] == GAUGE_DEPOSIT_V2:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    event.notes = f'Deposit {event.amount} {crypto_asset.symbol} into {gauge_address} {self.counterparty} gauge'  # noqa: E501
                    GlobalDBHandler.set_tokens_protocol_if_missing(
                        tokens=[event.asset.resolve_to_evm_token()],
                        new_protocol=self.counterparty,
                    )
                elif context.tx_log.topics[0] == WITHDRAW_TOPIC_V2:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    event.notes = f'Withdraw {event.amount} {crypto_asset.symbol} from {gauge_address} {self.counterparty} gauge'  # noqa: E501
                else:  # CLAIM_REWARDS
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.REWARD
                    event.notes = f'Receive {event.amount} {crypto_asset.symbol} rewards from {gauge_address} {self.counterparty} gauge'  # noqa: E501

        return EvmDecodingOutput(refresh_balances=found_event_modifying_balances)

    def _decode_voting_escrow_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == VOTING_ESCROW_WITHDRAW:
            return self._decode_withdraw_event(context)
        elif context.tx_log.topics[0] == VOTING_ESCROW_CREATE_LOCK:
            return self._decode_create_lock_event(context)
        elif context.tx_log.topics[0] == VOTING_ESCROW_METADATA_UPDATE:
            return self._decode_metadata_update_event(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_withdraw_event(self, context: DecoderContext) -> EvmDecodingOutput:
        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        token_id = int.from_bytes(context.tx_log.topics[2])
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == bytes_to_address(context.tx_log.topics[1]) and
                    event.address == ZERO_ADDRESS and
                    event.amount == ONE
            ):
                event.event_type = HistoryEventType.BURN
                event.event_subtype = HistoryEventSubType.NFT
                event.counterparty = self.counterparty
                event.notes = f'Burn veNFT-{token_id} to unlock {amount} {self.token_symbol} from vote escrow'  # noqa: E501

            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.amount == amount and
                    event.address == self.voting_escrow_address
            ):
                event.counterparty = self.counterparty
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Receive {amount} {self.token_symbol} from vote escrow after burning veNFT-{token_id}'  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_create_lock_event(self, context: DecoderContext) -> EvmDecodingOutput:
        in_event, out_event = None, None
        token_id = int.from_bytes(context.tx_log.topics[2])
        amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == ZERO_ADDRESS and
                    event.amount == ONE
            ):
                event.event_type = HistoryEventType.MINT
                event.event_subtype = HistoryEventSubType.NFT
                event.notes = f'Receive veNFT-{token_id} for locking {amount} {self.token_symbol} in vote escrow'  # noqa: E501
                event.counterparty = self.counterparty
                in_event = event

            elif (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == self.voting_escrow_address and
                    event.amount == amount
            ):
                event.notes = f'Lock {amount} {self.token_symbol} in vote escrow until {timestamp_to_date((lock_time := deserialize_timestamp(int.from_bytes(context.tx_log.data[32:64]))), formatstr="%d/%m/%Y")}'  # noqa: E501
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.extra_data = {
                    'token_id': token_id,
                    'lock_time': lock_time,
                }
                event.event_type = HistoryEventType.DEPOSIT
                event.counterparty = self.counterparty
                out_event = event

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events,
        )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_metadata_update_event(self, context: DecoderContext) -> EvmDecodingOutput:
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.DEPOSIT and
                    event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET and
                    event.counterparty == self.counterparty
            ):  # increase amount locked
                token_id = event.extra_data['token_id']  # type: ignore[index]  # it is always available
                event.notes = f'Increase locked amount in veNFT-{token_id} by {event.amount} {self.token_symbol}'  # noqa: E501
                # The lock time on amount increases is zero, so remove it from the extra data.
                # But keep the token_id for balance detection if the original deposit was from a
                # different address or wasn't decoded for some reason.
                event.extra_data.pop('lock_time', None)  # type: ignore[union-attr]  # extra_data is not None
                return DEFAULT_EVM_DECODING_OUTPUT

        for tx_log in context.all_logs:  # Handle increase unlock time case
            if tx_log.topics[0] != VOTING_ESCROW_CREATE_LOCK:
                continue

            # depositType=3 (i.e. increase unlock time)
            if int.from_bytes(tx_log.topics[3]) != 3:
                continue

            return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                extra_data={
                    'token_id': (token_id := int.from_bytes(tx_log.topics[2])),
                    'lock_time': (new_unlock_time := deserialize_timestamp(int.from_bytes(tx_log.data[32:64]))),  # noqa: E501
                },
                amount=ZERO,
                counterparty=self.counterparty,
                address=self.voting_escrow_address,
                location_label=bytes_to_address(tx_log.topics[1]),
                notes=f'Increase unlock time to {timestamp_to_date(new_unlock_time, "%d/%m/%Y")} for {self.token_symbol} veNFT-{token_id}',  # noqa: E501
                asset=get_or_create_evm_token(
                    userdb=self.base.database,
                    evm_address=self.voting_escrow_address,
                    chain_id=self.node_inquirer.chain_id,
                    token_kind=TokenKind.ERC721,
                    collectible_id=str(token_id),
                ),
            )])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_claim_rewards_events(
            self,
            suffix: str,
            context: DecoderContext,
    ) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != VOTER_CLAIM_REWARDS:
            return DEFAULT_EVM_DECODING_OUTPUT

        for event in context.decoded_events:
            if (
                event.asset != (reward_token := self.base.get_or_create_evm_asset(bytes_to_address(context.tx_log.topics[2]))) and  # noqa: E501
                event.amount != asset_normalized_value(
                    amount=int.from_bytes(context.tx_log.data[:32]),
                    asset=reward_token,
                )
            ):
                continue

            event.counterparty = self.counterparty
            event.event_type = HistoryEventType.RECEIVE
            event.event_subtype = HistoryEventSubType.REWARD
            event.notes = f'Claim {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from {self.counterparty} as a {suffix}'  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_vote_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != VOTER_VOTED:
            return DEFAULT_EVM_DECODING_OUTPUT

        weight = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            tx_log=context.tx_log,
            transaction=context.transaction,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=get_or_create_evm_token(
                userdb=self.base.database,
                evm_address=self.voting_escrow_address,
                chain_id=self.node_inquirer.chain_id,
                token_kind=TokenKind.ERC721,
                collectible_id=str(int.from_bytes(context.tx_log.topics[3])),
            ),
            amount=ZERO,
            counterparty=self.counterparty,
            address=self.voter_address,
            location_label=bytes_to_address(context.tx_log.topics[1]),
            notes=f'Cast {weight} votes for pool {bytes_to_address(context.tx_log.topics[2])}',
        )])

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        parent_mappings = super().reload_data()
        decoder_mappings = self.addresses_to_decoders()
        if parent_mappings is None:
            return decoder_mappings

        return dict(parent_mappings) | decoder_mappings

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        decoders = {
            self.voting_escrow_address: (self._decode_voting_escrow_events,),
            self.voter_address: (self._decode_vote_events,),
        }
        with GlobalDBHandler().conn.read_ctx() as cursor:
            for addy in globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[self.gauge_fees_cache_type],
            ):
                decoders[string_to_evm_address(addy)] = (lambda context: self._decode_claim_rewards_events(context=context, suffix='fee'),)  # noqa: E501

            for addy in globaldb_get_general_cache_values(
                cursor=cursor,
                key_parts=[self.gauge_bribes_cache_type],
            ):
                decoders[string_to_evm_address(addy)] = (lambda context: self._decode_claim_rewards_events(context=context, suffix='bribe'),)  # noqa: E501

            return decoders
