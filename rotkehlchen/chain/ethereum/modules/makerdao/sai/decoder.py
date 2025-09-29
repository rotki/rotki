from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.makerdao.constants import (
    MAKER_BURN_TOPIC,
    MAKERDAO_ICON,
    MAKERDAO_LABEL,
)
from rotkehlchen.chain.ethereum.modules.makerdao.sai.constants import CPT_SAI
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    FAILED_ENRICHMENT_OUTPUT,
    ActionItem,
    DecoderContext,
    DecodingOutput,
    EnricherContext,
    TransferEnrichmentOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_PETH, A_SAI, A_WETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

POOLED_ETHER_ADDRESS = string_to_evm_address('0xf53AD2c6851052A81B42133467480961B2321C09')
PETH_MINT_EVENT_TOPIC = b'\x0fg\x98\xa5`y:T\xc3\xbc\xfe\x86\xa9<\xde\x1es\x08}\x94L\x0e\xa2\x05D\x13}A!9h\x85'  # noqa: E501
SAI_CDP_MIGRATION_TOPIC = b'\n\t\x94\xe6\x12<i3\xeeu\x98\x86\x90WW\xde\xfe"\xc1\xf5\xd0<\xd1\xee1\\\xb6\xbd\xe8\xd1\x1a\xe8'  # noqa: E501
MAKERDAO_SAITUB_CONTRACT = string_to_evm_address('0x448a5065aeBB8E423F0896E6c5D525C040f59af3')
MAKERDAO_SAITAP_CONTRACT = string_to_evm_address('0xBda109309f9FafA6Dd6A9CB9f1Df4085B27Ee8eF')
MAKERDAO_SAI_PROXY_CONTRACT = string_to_evm_address('0x526af336D614adE5cc252A407062B8861aF998F5')


class MakerdaosaiDecoder(DecoderInterface):
    """
    Information relating to event topics and contracts came from:
    https://github.com/makerdao/sai/blob/d28fe5074af7c661fb3aa7f117ad419fb6414b91/DEVELOPING.md
    """
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
        self.topics_to_methods: dict[bytes, Callable] = {
            b'\x89\xb8\x89;\x80m\xb5\x08\x97\xc8\xe26,qW\x1c\xfa\xeb\x97a\xee@r\x7fh?\x17\x93\xcd\xa9\xdf\x16': self._decode_new_cdp_event,  # noqa: E501
            b'\xb8M!\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': self._decode_close_cdp,  # noqa: E501
            b'D\x0f\x19\xba\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': self._decode_borrow_sai_event,  # noqa: E501
            b's\xb3\x81\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': self._decode_repay_sai_event,  # noqa: E501
            b'\x04\x98x\xf3\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': self._decode_deposit_eth_event,  # noqa: E501
            b'@\xcc\x88T\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': self._decode_liquidate_event,  # noqa: E501
            b'\xa5\xcd\x18N\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00': self._decode_withdraw_eth,  # noqa: E501
        }
        self.weth = A_WETH.resolve_to_evm_token()
        self.eth = A_ETH.resolve_to_crypto_asset()
        self.sai = A_SAI.resolve_to_evm_token()
        self.peth = A_PETH.resolve_to_evm_token()

    def _decode_sai_tub(self, context: DecoderContext) -> DecodingOutput:
        decoder_function = self.topics_to_methods.get(context.tx_log.topics[0])
        if decoder_function is None:
            return DEFAULT_DECODING_OUTPUT

        return decoder_function(context=context)

    def _decode_withdraw_eth(self, context: DecoderContext) -> DecodingOutput:
        """
        This method decodes ETH withdrawal from a CDP.

        An example of such transaction is:
        https://etherscan.io/tx/0x4e569aa1f23dc771f1c9ad05ab7cdb0af2607358b166a8137b702f81b88e37b9
        """
        cdp_id = int.from_bytes(context.tx_log.topics[2])
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.eth
            ):
                # look for the pooled ether burn event to match the withdrawal
                for log in context.all_logs:
                    if (
                        log.topics[0] == MAKER_BURN_TOPIC and
                        log.address == POOLED_ETHER_ADDRESS and
                        # checks that the amount to be withdrawn matches the amount of PETH burnt
                        int.from_bytes(context.tx_log.topics[3]) == int.from_bytes(log.data[:32])
                    ):
                        event.event_type = HistoryEventType.WITHDRAWAL
                        event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                        event.counterparty = CPT_SAI
                        event.notes = f'Withdraw {event.amount} {self.eth.symbol} from CDP {cdp_id}'  # noqa: E501
                        return DEFAULT_DECODING_OUTPUT

        return DEFAULT_DECODING_OUTPUT

    def _decode_new_cdp_event(self, context: DecoderContext) -> DecodingOutput:
        """
        This method decodes the event of a new CDP creation.

        An example of such transaction is:
        https://etherscan.io/tx/0xf7049668cb7cbb9c00d80092b2dce7ea59984f4c52c83e5c0940535a93f3d5a0
        """
        deposit_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype.NONE and
                event.amount > ZERO and
                event.asset in (self.eth, self.weth) and
                event.counterparty != CPT_GAS
            ):
                deposit_event = event
                break

        cdp_creator = bytes_to_address(context.tx_log.topics[1])
        cdp_id = int.from_bytes(context.tx_log.data[:32])
        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.eth,
            amount=ZERO,
            location_label=cdp_creator,
            counterparty=CPT_SAI,
            notes=f'Create CDP {cdp_id}',
            address=context.transaction.to_address,
        )
        # ensure that the cdp creation event comes before any deposit event
        maybe_reshuffle_events(ordered_events=[event, deposit_event], events_list=context.decoded_events)  # noqa: E501
        return DecodingOutput(events=[event])

    def _decode_close_cdp(self, context: DecoderContext) -> DecodingOutput:
        """
        This method decodes the closing of an already existing CDP.

        An example of such transaction is:
        https://etherscan.io/tx/0xc851e18df6dec02ac2efff000298001e839dde3d6e99d25d1d98ecb0d390c9a6
        """
        cdp_creator = bytes_to_address(context.tx_log.topics[1])
        cdp_id = int.from_bytes(context.tx_log.data[128:])

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.INFORMATIONAL and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == ZERO and
                event.counterparty == CPT_SAI and
                event.asset == self.eth
            ):
                # this is to avoid having duplicated history events
                # which is caused by the tx_logs containing similar log entries
                return DEFAULT_DECODING_OUTPUT

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=self.eth,
            amount=ZERO,
            location_label=cdp_creator,
            counterparty=CPT_SAI,
            notes=f'Close CDP {cdp_id}',
            address=context.transaction.to_address,
        )
        return DecodingOutput(events=[event])

    def _decode_borrow_sai_event(self, context: DecoderContext) -> DecodingOutput:
        """
        This method decodes an event of SAI being borrowed.

        An example of such transaction is:
        https://etherscan.io/tx/0x4aed2d2fe5712a5b65cb6866c51ae672a53e39fa25f343e4c6ebaa8eae21de80
        """
        cdp_id = int.from_bytes(context.tx_log.topics[2])
        withdrawer = bytes_to_address(context.tx_log.topics[1])
        amount_withdrawn_raw = int.from_bytes(context.tx_log.topics[3])
        amount_withdrawn = asset_normalized_value(amount=amount_withdrawn_raw, asset=self.sai)

        for decoded_event in context.decoded_events:
            if (
                decoded_event.asset == self.sai and
                decoded_event.event_type == HistoryEventType.RECEIVE and
                decoded_event.event_subtype == HistoryEventSubType.GENERATE_DEBT and
                decoded_event.amount == amount_withdrawn and
                decoded_event.counterparty == CPT_SAI
            ):
                # this is to avoid having duplicated history events
                # which is caused by the tx_logs containing similar log entries
                return DEFAULT_DECODING_OUTPUT

        if self.base.is_tracked(withdrawer) is True:
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.GENERATE_DEBT,
                asset=self.sai,
                amount=amount_withdrawn,
                location_label=withdrawer,
                counterparty=CPT_SAI,
                notes=f'Borrow {amount_withdrawn} {self.sai.symbol} from CDP {cdp_id}',
                address=context.transaction.to_address,
            )
            return DecodingOutput(events=[event])

        # sai was actually borrowed, but it was handled by a proxy so create an action item
        # to transform the "receive" event later
        action_item = ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=self.sai,
            amount=amount_withdrawn,
            to_event_type=HistoryEventType.RECEIVE,
            to_event_subtype=HistoryEventSubType.GENERATE_DEBT,
            to_notes=f'Borrow {amount_withdrawn} {self.sai.symbol} from CDP {cdp_id}',
            to_counterparty=CPT_SAI,
            extra_data={'cdp_id': cdp_id},
        )
        return DecodingOutput(action_items=[action_item])

    def _decode_repay_sai_event(self, context: DecoderContext) -> DecodingOutput:
        """
        This method decodes an event of SAI loan repayment.

        An example of such transaction is:
        https://etherscan.io/tx/0xe964cb12f4bbfa1ba4b6db8464eb3f2d4234ceafb0b5ec5f4a2188b0264bab27
        """
        cdp_id = int.from_bytes(context.tx_log.topics[2])
        depositor = bytes_to_address(context.tx_log.topics[1])
        amount_paid_raw = int.from_bytes(context.tx_log.topics[3])
        amount_paid = asset_normalized_value(amount=amount_paid_raw, asset=self.sai)

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.sai and
                event.amount == amount_paid
            ):
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.counterparty = CPT_SAI
                event.notes = f'Repay {amount_paid} {self.sai.symbol} to CDP {cdp_id}'
                return DEFAULT_DECODING_OUTPUT

            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.PAYBACK_DEBT and
                event.asset == self.sai and
                event.amount == amount_paid
            ):
                # this is to avoid having duplicated history events
                # which is caused by the tx_logs containing similar log entries
                return DEFAULT_DECODING_OUTPUT

        if self.base.is_tracked(depositor) is True:
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.PAYBACK_DEBT,
                asset=self.sai,
                amount=amount_paid,
                location_label=depositor,
                counterparty=CPT_SAI,
                notes=f'Repay {amount_paid} {self.sai.symbol} to CDP {cdp_id}',
                address=context.transaction.to_address,
            )
            return DecodingOutput(events=[event])

        return DEFAULT_DECODING_OUTPUT

    def _decode_liquidate_event(self, context: DecoderContext) -> DecodingOutput:
        """
        This method decodes a liquidation event in a CDP

        An example of such transaction is:
        https://etherscan.io/tx/0x65d53653c584cde22e559cec4667a7278f75966360590b725d87055fb17552ba
        """
        liquidator = bytes_to_address(context.tx_log.topics[1])
        cdp_id = int.from_bytes(context.tx_log.topics[2])

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.LOSS and
                event.event_subtype == HistoryEventSubType.LIQUIDATE and
                event.asset == self.peth and
                event.counterparty == CPT_SAI
            ):
                # this is to avoid having duplicated history events
                # which is caused by the tx_logs containing similar log entries
                return DEFAULT_DECODING_OUTPUT

        # check for the transfer event of the liquidation to Maker SaiTap contract
        for log in context.all_logs:
            if (
                log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                bytes_to_address(log.topics[1]) == MAKERDAO_SAITUB_CONTRACT and
                bytes_to_address(log.topics[2]) == MAKERDAO_SAITAP_CONTRACT
            ):
                amount_raw = int.from_bytes(log.data[:32])
                amount = asset_normalized_value(amount=amount_raw, asset=self.weth)

                event = self.base.make_event_from_transaction(
                    transaction=context.transaction,
                    tx_log=context.tx_log,
                    event_type=HistoryEventType.LOSS,
                    event_subtype=HistoryEventSubType.LIQUIDATE,
                    asset=self.peth,
                    amount=amount,
                    location_label=liquidator,
                    notes=f'Liquidate {amount} {self.peth.symbol} for CDP {cdp_id}',
                    counterparty=CPT_SAI,
                    address=context.transaction.to_address,
                )
                return DecodingOutput(events=[event])

        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit_eth_event(self, context: DecoderContext) -> DecodingOutput:
        """
        This method decodes a deposit event of ETH into a CDP.

        An example of such transaction is:
        https://etherscan.io/tx/0x5a7849ab4b7f7de2b005deddef24a094387c248c3bcb06066109bd7852c1d8af
        """
        # check if ETH is sent to sai proxy contract or a proxy and mark it
        # as a deposit since the proxy handles the conversion to WETH
        # and transfer to the sai tub contract
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.address == MAKERDAO_SAI_PROXY_CONTRACT and
                event.asset == self.eth
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Supply {event.amount} {self.eth.symbol} to Sai vault'
                event.counterparty = CPT_SAI
                return DEFAULT_DECODING_OUTPUT

            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == self.eth
            ):
                # check for PETH mint event to match the deposit
                for log in context.all_logs:
                    if (
                        log.topics[0] == PETH_MINT_EVENT_TOPIC and
                        log.address == POOLED_ETHER_ADDRESS and
                        # checks that the amount to be deposited matches the amount of PETH minted
                        int.from_bytes(log.data[:32]) == int.from_bytes(context.tx_log.topics[2])
                    ):
                        event.event_type = HistoryEventType.DEPOSIT
                        event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                        event.notes = f'Supply {event.amount} {self.eth.symbol} to Sai vault'
                        event.counterparty = CPT_SAI
                        return DEFAULT_DECODING_OUTPUT

        return DEFAULT_DECODING_OUTPUT

    def _maybe_enrich_sai_tub_transfers(
            self,
            context: EnricherContext,
    ) -> TransferEnrichmentOutput:
        """This method enriches relevant asset transfers to and from the SaiTub contract."""
        if (
            context.event.event_type == HistoryEventType.SPEND and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.event.address in (MAKERDAO_SAITUB_CONTRACT, MAKERDAO_SAI_PROXY_CONTRACT)
        ):
            if context.event.asset == self.weth:
                context.event.event_type = HistoryEventType.DEPOSIT
                context.event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                context.event.notes = f'Supply {context.event.amount} {self.weth.symbol} to Sai vault'  # noqa: E501
                context.event.counterparty = CPT_SAI
                return TransferEnrichmentOutput(matched_counterparty=CPT_SAI)

            if context.event.asset == self.peth:
                context.event.event_type = HistoryEventType.DEPOSIT
                context.event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                context.event.notes = f'Increase CDP collateral by {context.event.amount} {self.peth.symbol}'  # noqa: E501
                context.event.counterparty = CPT_SAI
                return TransferEnrichmentOutput(matched_counterparty=CPT_SAI)

        if (
            context.event.event_type == HistoryEventType.RECEIVE and
            context.event.event_subtype == HistoryEventSubType.NONE and
            context.event.address == MAKERDAO_SAITUB_CONTRACT
        ):
            if context.event.asset == self.weth:
                context.event.event_type = HistoryEventType.WITHDRAWAL
                context.event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                context.event.notes = f'Withdraw {context.event.amount} {self.weth.symbol} from Sai vault'  # noqa: E501
                context.event.counterparty = CPT_SAI
                return TransferEnrichmentOutput(matched_counterparty=CPT_SAI)

            if context.event.asset == self.peth:
                context.event.event_type = HistoryEventType.WITHDRAWAL
                context.event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                context.event.notes = f'Decrease CDP collateral by {context.event.amount} {self.peth.symbol}'  # noqa: E501
                context.event.counterparty = CPT_SAI
                return TransferEnrichmentOutput(matched_counterparty=CPT_SAI)

        return FAILED_ENRICHMENT_OUTPUT

    def _decode_peth_mint_after_deposit(self, context: DecoderContext) -> DecodingOutput:
        """
        This method decodes the receipt of PETH after WETH has been deposited.

        An example of such transaction is:
        https://etherscan.io/tx/0x5a7849ab4b7f7de2b005deddef24a094387c248c3bcb06066109bd7852c1d8af
        """
        if context.tx_log.topics[0] == PETH_MINT_EVENT_TOPIC:
            owner = bytes_to_address(context.tx_log.topics[1])
            amount_raw = int.from_bytes(context.tx_log.data[:32])
            amount = asset_normalized_value(amount=amount_raw, asset=self.peth)

            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                asset=self.peth,
                amount=amount,
                location_label=owner,
                counterparty=CPT_SAI,
                notes=f'Receive {amount} {self.peth.symbol} from Sai Vault',
                address=context.transaction.to_address,
            )
            return DecodingOutput(events=[event])

        return DEFAULT_DECODING_OUTPUT

    def _decode_sai_cdp_migration(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list['EvmEvent'],  # pylint: disable=unused-argument
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        """This method decodes the migration of a Sai CDP to Dai CDP."""
        if tx_log.topics[0] != SAI_CDP_MIGRATION_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        old_cdp_id = int.from_bytes(tx_log.topics[1])
        new_cdp_id = int.from_bytes(tx_log.topics[2])
        owner = bytes_to_address(tx_log.data[:32])

        event = self.base.make_event_from_transaction(
            transaction=transaction,
            tx_log=tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=owner,
            notes=f'Migrate Sai CDP {old_cdp_id} to Dai CDP {new_cdp_id}',
            counterparty=CPT_SAI,
            address=transaction.to_address,
        )
        return DecodingOutput(events=[event])

    def decoding_rules(self) -> list[Callable]:
        return [
            self._decode_sai_cdp_migration,
        ]

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            MAKERDAO_SAITUB_CONTRACT: (self._decode_sai_tub,),
            POOLED_ETHER_ADDRESS: (self._decode_peth_mint_after_deposit,),
        }

    def enricher_rules(self) -> list[Callable]:
        return [
            self._maybe_enrich_sai_tub_transfers,
        ]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SAI,
            label=f'{MAKERDAO_LABEL} SAI',
            image=MAKERDAO_ICON,
        ),)
