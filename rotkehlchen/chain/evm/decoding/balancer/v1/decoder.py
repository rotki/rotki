import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.ethereum.utils import asset_normalized_value, should_update_protocol_cache
from rotkehlchen.chain.evm.decoding.balancer.constants import BALANCER_LABEL, CPT_BALANCER_V1
from rotkehlchen.chain.evm.decoding.balancer.mixins import BalancerCommonAccountingMixin
from rotkehlchen.chain.evm.decoding.balancer.types import BalancerV1EventTypes
from rotkehlchen.chain.evm.decoding.balancer.utils import query_balancer_data
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

JOIN_V1: Final = b'c\x98-\xf1\x0e\xfd\x8d\xfa\xaa\xa0\xfc\xc7\xf5\x0b-\x93\xb7\xcb\xa2l\xccH\xad\xee(s"\rH]\xc3\x9a'  # noqa: E501
EXIT_V1: Final = b'\xe7L\x91U+d\xc2\xe2\xe7\xbd%V9\xe0\x04\xe6\x93\xbd>\x1d\x01\xcc3\xe6V\x10\xb8j\xfc\xc1\xff\xed'  # noqa: E501
TRANSFER_TOPIC: Final = b'\xdd\xf2R\xad\x1b\xe2\xc8\x9bi\xc2\xb0h\xfc7\x8d\xaa\x95+\xa7\xf1c\xc4\xa1\x16(\xf5ZM\xf5#\xb3\xef'  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancerv1CommonDecoder(DecoderInterface, BalancerCommonAccountingMixin, ReloadableDecoderMixin):  # noqa: E501

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        BalancerCommonAccountingMixin.__init__(self, counterparty=CPT_BALANCER_V1)
        self.pools: set[ChecksumEvmAddress] = set()

    def _decode_v1_pool_event(self, all_logs: list[EvmTxReceiptLog]) -> list[dict[str, Any]] | None:  # noqa: E501
        """Read the list of logs in search for a Balancer v1 event and return the information
        needed to decode the transfers made in the transaction to/from the ds proxy
        """
        # The transfer event appears after the debt generation event, so we need to transform it
        if len(target_logs := [x for x in all_logs if x.topics[0] in (JOIN_V1, EXIT_V1)]) == 0:
            return None

        events_information = []
        for target_log in target_logs:
            token_address = bytes_to_address(target_log.topics[2])
            amount = int.from_bytes(target_log.data[0:32])
            if target_log.topics[0] == JOIN_V1:
                balancer_event_type = BalancerV1EventTypes.JOIN
                ds_address = bytes_to_address(target_log.topics[1])
            else:
                balancer_event_type = BalancerV1EventTypes.EXIT
                ds_address = target_log.address

            proxy_event_information = {
                'ds_address': ds_address,
                'token_address': token_address,
                'amount': amount,
                'type': balancer_event_type,
            }
            events_information.append(proxy_event_information)

        return events_information

    def _maybe_enrich_balancer_v1_events(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """
        Enrich balancer v1 transfer to read pool events of:
        - Depositing in the pool
        - Withdrawing from the pool

        In balancer v1 pools are managed using a DSProxy so the account doesn't interact
        directly with the pools.
        """
        if (events_information := self._decode_v1_pool_event(all_logs=context.all_logs)) is None:
            return FAILED_ENRICHMENT_OUTPUT

        for proxied_event in events_information:
            if proxied_event.get('ds_address') != context.event.address:
                continue

            if proxied_event.get('type') == BalancerV1EventTypes.JOIN:
                if (
                    context.event.event_type == HistoryEventType.RECEIVE and
                    context.event.event_subtype == HistoryEventSubType.NONE
                ):
                    context.event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    context.event.counterparty = CPT_BALANCER_V1
                    context.event.notes = f'Receive {context.event.balance.amount} {context.token.symbol} from a Balancer v1 pool'  # noqa: E501
                    return TransferEnrichmentOutput(matched_counterparty=CPT_BALANCER_V1)
                if (
                    context.event.event_type == HistoryEventType.SPEND and
                    context.event.event_subtype == HistoryEventSubType.NONE
                ):
                    context.event.event_type = HistoryEventType.DEPOSIT
                    context.event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                    context.event.counterparty = CPT_BALANCER_V1
                    context.event.notes = f'Deposit {context.event.balance.amount} {context.token.symbol} to a Balancer v1 pool'  # noqa: E501
                    return TransferEnrichmentOutput(matched_counterparty=CPT_BALANCER_V1)
            elif proxied_event.get('type') == BalancerV1EventTypes.EXIT:
                if (
                    context.event.event_type == HistoryEventType.RECEIVE and
                    context.event.event_subtype == HistoryEventSubType.NONE
                ):
                    context.event.event_type = HistoryEventType.WITHDRAWAL
                    context.event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                    context.event.counterparty = CPT_BALANCER_V1
                    context.event.notes = f'Receive {context.event.balance.amount} {context.token.symbol} after removing liquidity from a Balancer v1 pool'  # noqa: E501
                    return TransferEnrichmentOutput(matched_counterparty=CPT_BALANCER_V1)
                if (
                    context.event.event_type == HistoryEventType.SPEND and
                    context.event.event_subtype == HistoryEventSubType.NONE
                ):
                    context.event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    context.event.counterparty = CPT_BALANCER_V1
                    context.event.notes = f'Return {context.event.balance.amount} {context.token.symbol} to a Balancer v1 pool'  # noqa: E501
                    return TransferEnrichmentOutput(matched_counterparty=CPT_BALANCER_V1)

        return FAILED_ENRICHMENT_OUTPUT

    def _decode_non_proxy_events(self, context: DecoderContext) -> DecodingOutput:
        """Not all balancer v1 pools are created via the UI. This method decodes the events of such pools."""  # noqa: E501
        if context.tx_log.topics[0] not in (JOIN_V1, EXIT_V1, TRANSFER_TOPIC):
            return DEFAULT_DECODING_OUTPUT

        from_event_subtype, to_event_type, to_event_subtype, location_label = HistoryEventSubType.NONE, None, None, None  # noqa: E501
        if context.tx_log.topics[0] == JOIN_V1:
            from_event_type = HistoryEventType.SPEND
            to_event_type = HistoryEventType.DEPOSIT
            to_event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            location_label = bytes_to_address(context.tx_log.topics[1])
            token = self.base.get_or_create_evm_token(address=bytes_to_address(context.tx_log.topics[2]))  # noqa: E501
            amount = asset_normalized_value(amount=int.from_bytes(context.tx_log.data[:32]), asset=token)  # noqa: E501
            to_notes = f'Deposit {amount} {token.symbol} to a Balancer v1 pool'
        elif context.tx_log.topics[0] == EXIT_V1:
            location_label = bytes_to_address(context.tx_log.topics[1])
            token = self.base.get_or_create_evm_token(address=bytes_to_address(context.tx_log.topics[2]))  # noqa: E501
            amount = asset_normalized_value(amount=int.from_bytes(context.tx_log.data[:32]), asset=token)  # noqa: E501
            from_event_type = HistoryEventType.RECEIVE
            to_event_type = HistoryEventType.WITHDRAWAL
            to_event_subtype = HistoryEventSubType.REMOVE_ASSET
            to_notes = f'Receive {amount} {token.symbol} after removing liquidity from a Balancer v1 pool'  # noqa: E501
        else:
            from_address = bytes_to_address(context.tx_log.topics[1])
            token = self.base.get_or_create_evm_token(address=context.tx_log.address)
            amount = asset_normalized_value(amount=int.from_bytes(context.tx_log.data[:32]), asset=token)  # noqa: E501
            is_receive = from_address == context.tx_log.address
            from_event_type = HistoryEventType.RECEIVE if is_receive else HistoryEventType.SPEND
            to_event_subtype = HistoryEventSubType.RECEIVE_WRAPPED if is_receive else HistoryEventSubType.RETURN_WRAPPED  # noqa: E501
            to_notes = (
                f'Receive {amount} {token.symbol} from a Balancer v1 pool' if is_receive
                else f'Return {amount} {token.symbol} to a Balancer v1 pool'
            )

        return DecodingOutput(action_items=[ActionItem(
            action='transform',
            from_event_type=from_event_type,
            from_event_subtype=from_event_subtype,
            to_event_type=to_event_type,
            location_label=location_label,
            to_event_subtype=to_event_subtype,
            to_counterparty=CPT_BALANCER_V1,
            to_notes=to_notes,
            asset=token,
        )])

    def _check_refunds_v1(
            self,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """
        It can happen that after sending tokens to the DSProxy in balancer V1 the amount of tokens
        required for the deposit is lower than the amount sent and then those tokens are returned
        to the DSProxy and then to the user.
        """
        deposited_assets = set()
        for event in decoded_events:
            if event.counterparty != CPT_BALANCER_V1:
                continue

            if (
                event.event_type == HistoryEventType.DEPOSIT and
                event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET
            ):
                deposited_assets.add(event.asset)
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.RECEIVE_WRAPPED and
                event.asset in deposited_assets
            ):  # in this case we got refunded one of the assets deposited
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REFUND
                asset = event.asset.resolve_to_asset_with_symbol()
                event.notes = f'Refunded {event.balance.amount} {asset.symbol} after depositing in Balancer V1 pool'  # noqa: E501

        return decoded_events

    def reload_data(self) -> Mapping[ChecksumEvmAddress, tuple[Any, ...]] | None:
        if should_update_protocol_cache(cache_key=CacheType.BALANCER_V1_POOLS, args=(self.evm_inquirer.chain_name, '1')) is True:  # noqa: E501
            query_balancer_data(
                version=1,
                protocol=CPT_BALANCER_V1,
                inquirer=self.evm_inquirer,
                cache_type=CacheType.BALANCER_V1_POOLS,
            )

        with GlobalDBHandler().conn.read_ctx() as cursor:
            query_body = """FROM evm_tokens AS et
            INNER JOIN underlying_tokens_list AS utl
            ON et.identifier = utl.parent_token_entry
            WHERE et.protocol=? AND et.chain=?
            """
            bindings = (
                CPT_BALANCER_V1,
                self.evm_inquirer.chain_id.serialize_for_db(),
            )
            cursor.execute(f'SELECT COUNT(et.identifier) {query_body}', bindings)
            if cursor.fetchone()[0] == len(self.pools):
                return None  # up to date

            self.pools = {
                string_to_evm_address(row[1])
                for row in cursor.execute(f'SELECT et.protocol, et.address {query_body}', bindings)
            }

        return self.addresses_to_decoders()

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.pools, (self._decode_non_proxy_events,))

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_balancer_v1_events,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_BALANCER_V1,
            label=BALANCER_LABEL,
            image='balancer.svg',
        ),)

    def addresses_to_counterparties(self) -> dict['ChecksumEvmAddress', str]:
        return dict.fromkeys(self.pools, CPT_BALANCER_V1)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_BALANCER_V1: [
                (0, self._check_refunds_v1),
                (1, self._check_deposits_withdrawals),
            ],
        }
