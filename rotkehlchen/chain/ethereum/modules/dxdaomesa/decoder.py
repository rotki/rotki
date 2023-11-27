import json
import os
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_DXDAO_MESA

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

DEPOSIT = b'\xc1\x1c\xc3N\x93\xc6z\x938+\x99\xf2I\x8e\x997\x19\x87\x98\xf3\xc1\xc2\x88\x80\x08\xff\xc0\xee\xb8/h\xc4'  # noqa: E501
ORDER_PLACEMENT = b'\xde\xcfo\xde\x82C\x98\x12\x99\xf7\xb7\xa7v\xf2\x9a\x9f\xc6z,\x98H\xe2]w\xc5\x0e\xb1\x1f\xa5\x8a~!'  # noqa: E501
WITHDRAW_REQUEST = b',bE\xafPo\x0f\xc1\x08\x99\x18\xc0,\x1d\x01\xbd\xe9\xcc\x80v\t\xb34\xb3\xe7dMm\xfbZl^'  # noqa: E501
WITHDRAW = b'\x9b\x1b\xfa\x7f\xa9\xeeB\n\x16\xe1$\xf7\x94\xc3Z\xc9\xf9\x04r\xac\xc9\x91@\xeb/dG\xc7\x14\xca\xd8\xeb'  # noqa: E501


class DxdaomesaDecoder(DecoderInterface):

    def __init__(  # pylint: disable=super-init-not-called
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
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(dir_path, 'data', 'contracts.json'), encoding='utf8') as f:
            contracts = json.loads(f.read())

        self.contract = EvmContract(
            address=contracts['DXDAOMESA']['address'],
            abi=contracts['DXDAOMESA']['abi'],
            deployed_block=contracts['DXDAOMESA']['deployed_block'],
        )

    def _decode_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT:
            return self._decode_deposit(context=context)
        if context.tx_log.topics[0] == ORDER_PLACEMENT:
            return self._decode_order_placement(context=context)
        if context.tx_log.topics[0] == WITHDRAW_REQUEST:
            return self._decode_withdraw_request(context=context)
        if context.tx_log.topics[0] == WITHDRAW:
            return self._decode_withdraw(context=context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit(self, context: DecoderContext) -> DecodingOutput:
        topic_data, log_data = self.contract.decode_event(
            tx_log=context.tx_log,
            event_name='Deposit',
            argument_names=('user', 'token', 'amount', 'batchId'),
        )
        deposited_asset = self.base.get_or_create_evm_asset(topic_data[1])
        amount = asset_normalized_value(amount=log_data[0], asset=deposited_asset)

        for event in context.decoded_events:
            # Find the transfer event which should come before the deposit
            if event.event_type == HistoryEventType.SPEND and event.asset == deposited_asset and event.balance.amount == amount and event.address == self.contract.address:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_DXDAO_MESA
                event.notes = f'Deposit {amount} {deposited_asset.symbol} to DXDao mesa exchange'
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_withdraw(self, context: DecoderContext) -> DecodingOutput:
        topic_data, log_data = self.contract.decode_event(
            tx_log=context.tx_log,
            event_name='Withdraw',
            argument_names=('user', 'token', 'amount'),
        )
        withdraw_asset = self.base.get_or_create_evm_asset(topic_data[1])
        amount = asset_normalized_value(amount=log_data[0], asset=withdraw_asset)

        for event in context.decoded_events:
            # Find the transfer event which should come before the withdraw
            if event.event_type == HistoryEventType.RECEIVE and event.asset == withdraw_asset and event.balance.amount == amount and event.address == self.contract.address:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_DXDAO_MESA
                event.notes = f'Withdraw {amount} {withdraw_asset.symbol} from DXDao mesa exchange'
                break

        return DEFAULT_DECODING_OUTPUT

    def _decode_withdraw_request(self, context: DecoderContext) -> DecodingOutput:
        topic_data, log_data = self.contract.decode_event(
            tx_log=context.tx_log,
            event_name='WithdrawRequest',
            argument_names=('user', 'token', 'amount', 'batchId'),
        )
        user = topic_data[0]
        if not self.base.is_tracked(user):
            return DEFAULT_DECODING_OUTPUT

        token = self.base.get_or_create_evm_asset(topic_data[1])
        amount = asset_normalized_value(amount=log_data[0], asset=token)

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            location_label=user,
            asset=token,
            balance=Balance(amount=amount),
            notes=f'Request a withdrawal of {amount} {token.symbol} from DXDao Mesa',
            counterparty=CPT_DXDAO_MESA,
            address=context.transaction.to_address,
        )
        return DecodingOutput(event=event)

    def _decode_order_placement(self, context: DecoderContext) -> DecodingOutput:
        """Some docs: https://docs.gnosis.io/protocol/docs/tutorial-limit-orders/"""
        topic_data, log_data = self.contract.decode_event(
            tx_log=context.tx_log,
            event_name='OrderPlacement',
            argument_names=('owner', 'index', 'buyToken', 'sellToken', 'validFrom', 'validUntil', 'priceNumerator', 'priceDenominator'),  # noqa: E501
        )
        owner = topic_data[0]
        if not self.base.is_tracked(owner):
            return DEFAULT_DECODING_OUTPUT

        result = self.evm_inquirer.multicall_specific(
            contract=self.contract,
            method_name='tokenIdToAddressMap',
            arguments=[[topic_data[1]], [topic_data[2]]],
        )  # The resulting addresses are non checksumed but they can be found in the DB
        buy_token = self.base.get_or_create_evm_asset(result[0][0])
        sell_token = self.base.get_or_create_evm_asset(result[1][0])
        buy_amount = asset_normalized_value(amount=log_data[3], asset=buy_token)
        sell_amount = asset_normalized_value(amount=log_data[4], asset=sell_token)
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            location_label=owner,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.PLACE_ORDER,
            asset=sell_token,
            balance=Balance(amount=sell_amount),
            notes=f'Place an order in DXDao Mesa to sell {sell_amount} {sell_token.symbol} for {buy_amount} {buy_token.symbol}',  # noqa: E501
            counterparty=CPT_DXDAO_MESA,
            address=context.transaction.to_address,
        )
        return DecodingOutput(event=event)

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            self.contract.address: (self._decode_events,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_DXDAO_MESA, label='dxdao', image='dxdao.svg'),)
