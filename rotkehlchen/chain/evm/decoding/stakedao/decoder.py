import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    asset_raw_value,
    should_update_protocol_cache,
    token_normalized_value,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.stakedao.utils import (
    query_stakedao_gauges,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.globaldb.cache import globaldb_get_general_cache_values
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import CacheType, ChainID, ChecksumEvmAddress, Timestamp
from rotkehlchen.utils.misc import bytes_to_address, timestamp_to_date

from .constants import (
    CLAIMED_WITH_BOUNTY,
    CLAIMED_WITH_BRIBE,
    CPT_STAKEDAO,
    STAKEDAO_DEPOSIT,
    STAKEDAO_GAUGE_ABI,
    STAKEDAO_VAULT_ABI,
    STAKEDAO_WITHDRAW,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class StakedaoCommonDecoder(DecoderInterface, ReloadableDecoderMixin):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            claim_bribe_addresses: list['ChecksumEvmAddress'],
            claim_bounty_addresses: list['ChecksumEvmAddress'],
    ):
        super().__init__(evm_inquirer, base_tools, msg_aggregator)
        self.claim_bribe_addresses = claim_bribe_addresses
        self.claim_bounty_addresses = claim_bounty_addresses
        self.gauges: list[ChecksumEvmAddress] = []

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        """Check that cache is up to date and refresh cache from db.
        Returns a fresh addresses to decoders mapping.
        """
        if should_update_protocol_cache(
            cache_key=CacheType.STAKEDAO_GAUGES,
            args=(str(self.evm_inquirer.chain_id.value),),
        ) is True:
            query_stakedao_gauges()
        if len(self.gauges) != 0:
            return None  # we didn't update the globaldb cache, and we have the data already

        with GlobalDBHandler().conn.read_ctx() as cursor:
            self.gauges = globaldb_get_general_cache_values(  # type: ignore[assignment]  # addresses are always checksummed
                cursor=cursor,
                key_parts=(CacheType.STAKEDAO_GAUGES, str(self.evm_inquirer.chain_id.value)),
            )

        return self.addresses_to_decoders()

    def _decode_claim(
            self,
            context: DecoderContext,
            reward_token_address: ChecksumEvmAddress,
            amount: int,
            period: Timestamp,
    ) -> DecodingOutput:
        """Base functionality for claiming different types of stakedao votemarket bribes"""
        claimed_token = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=reward_token_address,
            chain_id=ChainID.ETHEREUM,
            evm_inquirer=self.evm_inquirer,
        )
        normalized_amount = token_normalized_value(amount, claimed_token)
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == claimed_token and event.amount == normalized_amount:  # noqa: E501
                event.event_subtype = HistoryEventSubType.REWARD
                event.counterparty = CPT_STAKEDAO
                event.notes = f'Claim {normalized_amount} {claimed_token.symbol} from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}'  # noqa: E501
                event.product = EvmProduct.BRIBE
                break
        else:  # not found
            log.error(f'Stakedao bribe transfer was not found for {context.transaction.tx_hash.hex()}')  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def _decode_claim_with_bounty(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED_WITH_BOUNTY:
            return DEFAULT_DECODING_OUTPUT

        # we are not checking user address in the logs as user is not always
        # the recipient according to the contract
        reward_token_address = bytes_to_address(context.tx_log.data[0:32])
        amount = int.from_bytes(context.tx_log.data[32:64])
        period = Timestamp(int.from_bytes(context.tx_log.data[96:128]))
        return self._decode_claim(context=context, reward_token_address=reward_token_address, amount=amount, period=period)  # noqa: E501

    def _decode_claim_with_bribe(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != CLAIMED_WITH_BRIBE:
            return DEFAULT_DECODING_OUTPUT

        # we are not checking user address in the logs as user is not always
        # the recipient according to the contract
        reward_token_address = bytes_to_address(context.tx_log.topics[2])
        amount = int.from_bytes(context.tx_log.data[0:32])
        period = Timestamp(int.from_bytes(context.tx_log.data[32:64]))
        return self._decode_claim(context=context, reward_token_address=reward_token_address, amount=amount, period=period)  # noqa: E501

    def _decode_deposit(self, context: DecoderContext) -> DecodingOutput:
        deposited_raw_amount = int.from_bytes(context.tx_log.data[:32])
        received_amount = asset_normalized_value(
            amount=deposited_raw_amount,
            asset=(received_asset := self.base.get_or_create_evm_token(context.tx_log.address)),
        )
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    asset_raw_value(
                        amount=event.amount,
                        asset=(deposited_asset := event.asset.resolve_to_crypto_asset()),
                    ) == deposited_raw_amount
            ):
                event.counterparty = CPT_STAKEDAO
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {event.amount} {deposited_asset.symbol} in StakeDAO'
                break
        else:
            log.error(f'Could not find stakedao deposit event for transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        return DecodingOutput(action_items=[ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            to_event_type=HistoryEventType.RECEIVE,
            to_event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            amount=received_amount,
            asset=received_asset,
            to_notes=f'Receive {received_amount} {received_asset.symbol} after depositing in StakeDAO',  # noqa: E501
            to_counterparty=CPT_STAKEDAO,
        )])

    def _decode_withdraw(self, context: DecoderContext) -> DecodingOutput:
        # find the vault behind the gauge, then get the underlying token of that vault
        received_token = self.base.get_or_create_evm_token(deserialize_evm_address(self.evm_inquirer.call_contract(  # noqa: E501
            contract_address=(vault_address := deserialize_evm_address(self.evm_inquirer.call_contract(  # noqa: E501
                contract_address=context.tx_log.address,
                abi=STAKEDAO_GAUGE_ABI,
                method_name='vault',
            ))),
            abi=STAKEDAO_VAULT_ABI,
            method_name='token',
        )))
        received_amount = asset_normalized_value(
            amount=(removed_raw_amount := int.from_bytes(context.tx_log.data[:32])),
            asset=received_token,
        )
        claim_events = []
        for event in context.decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
                claim_events.append(event)
                event.counterparty = CPT_STAKEDAO
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.REWARD
                event.notes = f'Claim {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} from StakeDAO'  # noqa: E501

        # search logs for the gauge token burn — this happens when the vault contract,
        # not the user, burns the gauge token as part of the withdrawal process.
        # We use this to confirm the amount unwrapped and trace the original wrapped token.
        for tx_log in context.all_logs:
            if not (
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    tx_log.address == context.tx_log.address and
                    bytes_to_address(tx_log.topics[1]) == vault_address and
                    bytes_to_address(tx_log.topics[2]) == ZERO_ADDRESS and
                    int.from_bytes(tx_log.data[:32]) == removed_raw_amount
            ):
                continue

            return_event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=tx_log,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                asset=(returned_asset := self.base.get_or_create_evm_token(tx_log.address)),
                amount=(returned_amount := asset_normalized_value(
                    amount=removed_raw_amount,
                    asset=returned_asset,
                )),
                counterparty=CPT_STAKEDAO,
                address=tx_log.address,
                location_label=bytes_to_address(context.tx_log.topics[1]),
                notes=f'Return {returned_amount} {returned_asset.symbol} to StakeDAO',
            )
            break
        else:
            log.error(f'Could not find stakedao gauge token return event for transaction {context.transaction}')  # noqa: E501
            return DEFAULT_DECODING_OUTPUT

        context.decoded_events.append(return_event)
        maybe_reshuffle_events(
            ordered_events=[return_event] + claim_events,
            events_list=context.decoded_events,
        )
        return DecodingOutput(action_items=[ActionItem(
            action='transform',
            asset=received_token,
            amount=received_amount,
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            to_counterparty=CPT_STAKEDAO,
            to_notes=f'Withdraw {received_amount} {received_token.symbol} from StakeDAO',
            to_address=context.transaction.to_address,
        )])

    def _decode_deposit_withdrawal_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == STAKEDAO_DEPOSIT:
            return self._decode_deposit(context)
        elif context.tx_log.topics[0] == STAKEDAO_WITHDRAW:
            return self._decode_withdraw(context)
        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_STAKEDAO: [EvmProduct.BRIBE],
        }

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return (
            dict.fromkeys(self.gauges, (self._decode_deposit_withdrawal_events, )) |
            dict.fromkeys(self.claim_bribe_addresses, (self._decode_claim_with_bribe, )) |
            dict.fromkeys(self.claim_bounty_addresses, (self._decode_claim_with_bounty, ))
        )

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_STAKEDAO,
            label='Stakedao',
            image='stakedao.png',
        ),)
