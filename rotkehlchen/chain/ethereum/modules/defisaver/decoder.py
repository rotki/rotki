import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

from .constants import (
    CPT_DEFISAVER,
    DEACTIVATE_SUB,
    DFS_GENERIC_LOGGER_LEGACY,
    FL_AAVEV2,
    FL_AAVEV3,
    FL_AAVEV3_CARRY_DEBT,
    FL_AAVEV3_WITH_FEE,
    FL_ACTION_V1_0_0,
    FL_ACTION_V1_0_1,
    FL_ACTION_V1_0_2,
    FL_ACTION_V1_0_3,
    FL_ACTION_V1_0_3_BIS,
    FL_BALANCER,
    FL_BALANCER_VPREV_1,
    FL_BALANCER_VPREV_2,
    FL_DYDX,
    FL_DYDX_VPREV_1,
    FL_DYDX_VPREV_2,
    FL_EULER_V1_0_0,
    FL_EULER_V1_0_1,
    FL_GHO,
    FL_MAKER_V1_0_0,
    FL_MAKER_V1_0_1,
    FL_MAKER_V1_0_2,
    FL_MAKER_V1_0_3,
    FL_MORPHO_BLUE,
    FL_SPARK,
    FL_UNIV3,
    SUB_STORAGE,
    SUBSCRIBE,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DefisaverDecoder(DecoderInterface):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.flashloan_addresses = (
            FL_ACTION_V1_0_0,
            FL_ACTION_V1_0_1,
            FL_ACTION_V1_0_2,
            FL_ACTION_V1_0_3,
            FL_ACTION_V1_0_3_BIS,
            FL_MORPHO_BLUE,
            FL_BALANCER,
            FL_BALANCER_VPREV_1,
            FL_BALANCER_VPREV_2,
            FL_AAVEV3,
            FL_EULER_V1_0_1,
            FL_EULER_V1_0_0,
            FL_SPARK,
            FL_AAVEV3_WITH_FEE,
            FL_AAVEV3_CARRY_DEBT,
            FL_AAVEV2,
            FL_DYDX,
            FL_DYDX_VPREV_1,
            FL_DYDX_VPREV_2,
            FL_GHO,
            FL_MAKER_V1_0_3,
            FL_MAKER_V1_0_2,
            FL_MAKER_V1_0_1,
            FL_MAKER_V1_0_0,
            FL_UNIV3,
        )
        self.dfs_logger_addresses = (DFS_GENERIC_LOGGER_LEGACY, )

    def _decode_subscribe(self, context: DecoderContext) -> DecodingOutput:
        sub_id = int.from_bytes(context.tx_log.topics[1])
        proxy = bytes_to_address(context.tx_log.topics[2])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Subscribe to defisaver automation with subscription id {sub_id} for proxy {proxy}',  # noqa: E501
            address=context.tx_log.address,
            counterparty=CPT_DEFISAVER,
        )
        return DecodingOutput(event=event)

    def _decode_deactivate_sub(self, context: DecoderContext) -> DecodingOutput:
        sub_id = int.from_bytes(context.tx_log.topics[1])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=context.transaction.from_address,
            notes=f'Deactivate defisaver automation subscription with id {sub_id}',
            address=context.tx_log.address,
            counterparty=CPT_DEFISAVER,
        )
        return DecodingOutput(event=event)

    def _decode_substorage_action(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == DEACTIVATE_SUB:
            return self._decode_deactivate_sub(context)
        if context.tx_log.topics[0] == SUBSCRIBE:
            return self._decode_subscribe(context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_flashloan_events(self, context: DecoderContext) -> DecodingOutput:
        """
        Decodes DeFi Saver events from the given context.
        """
        # We want only to remap the ERC20 transfers, so
        # we just match the counterparty for triggering the post-decoding rules
        for event in context.decoded_events:
            if (
                event.address in self.flashloan_addresses and
                event.location_label is not None and
                self.base.is_tracked(string_to_evm_address(event.location_label))
            ):
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_subtype = HistoryEventSubType.GENERATE_DEBT  # TODO: should  we create a new subtype for flashloans?  # noqa: E501
                    event.counterparty = CPT_DEFISAVER
                    event.notes = f'Executed flashloan of {event.balance.amount} {event.asset.symbol_or_name()} via DefiSaver'  # noqa: E501
                elif (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
                ):
                    event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                    event.counterparty = CPT_DEFISAVER
                    event.notes = f'Repaid flashloan of {event.balance.amount} {event.asset.symbol_or_name()} via DefiSaver'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        dfs_automation_decoders = {SUB_STORAGE: (self._decode_substorage_action,)}
        flashloan_decoders = dict.fromkeys(self.flashloan_addresses, (self._decode_flashloan_events,))  # noqa: E501
        # We intercept DFS generic logger events to capture transactions from DFS contracts
        # that do not emit any log events (e.g. FL_DYDX_VPREV_1 and FL_DYDX_VPREV_2)
        logevent_decoders = dict.fromkeys(self.dfs_logger_addresses, (self._decode_flashloan_events,))  # noqa: E501
        # TODO: defisaver swap decoders
        return dfs_automation_decoders | flashloan_decoders | logevent_decoders

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(GlobalDBHandler.get_addresses_by_protocol(
            chain_id=self.evm_inquirer.chain_id,
            protocol=CPT_DEFISAVER,
        ), CPT_DEFISAVER) | dict.fromkeys(self.flashloan_addresses, CPT_DEFISAVER)

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_DEFISAVER,
            label='Defisaver',
            image='defisaver.jpeg',
        ),)
