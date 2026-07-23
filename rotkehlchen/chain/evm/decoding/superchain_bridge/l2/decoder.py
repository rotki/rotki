import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.superchain_bridge.utils import get_messenger_transfer_id
from rotkehlchen.chain.evm.decoding.utils import bridge_match_transfer, bridge_prepare_data
from rotkehlchen.chain.evm.l2_with_l1_fees.decoding.interfaces import L2WithL1FeesDecoderInterface
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, TokenKind
from rotkehlchen.utils.misc import bytes_to_address, from_wei

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2WithL1FeesTransaction
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator


DEPOSIT_FINALIZED: Final = b'\xb0DE#&\x87\x17\xa0&\x98\xbeG\xd0\x80:\xa7F\x8c\x00\xac\xbe\xd2\xf8\xbd\x93\xa0E\x9c\xdea\xdd\x89'  # noqa: E501
WITHDRAWAL_INITIATED: Final = b"s\xd1p\x91\n\xba\x9emP\xb1\x02\xdbR+\x1d\xbc\xd7\x96!oQ(\xb4E\xaa!5'(\x86I~"  # noqa: E501
DEPOSIT_TX_TYPE: Final = 126  # 0x7e. The system transaction relaying an L1 deposit on OP stack chains  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SuperchainL2SideBridgeCommonDecoder(L2WithL1FeesDecoderInterface, ABC):
    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            native_assets: Sequence[Asset],
            bridge_addresses: tuple[ChecksumEvmAddress, ...],
            counterparty: CounterpartyDetails,
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.bride_addresses = bridge_addresses
        # native assets is a sequence because in optimism there is:
        # 1. ETH transfers (no event emitted)
        # 2. Legacy "system" transfers via 0xDeadDeAddeAddEAddeadDEaDDEAdDeaDDeAD0000
        self.native_assets = native_assets
        self.counterparty = counterparty

    def _decode_receive_or_deposit(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decodes a bridging event.

        Note:
            DAI uses special bridge.

        See:
             https://github.com/makerdao/optimism-dai-bridge
             https://docs.optimism.io/app-developers/bridging/custom-bridge
        """
        if context.tx_log.topics[0] not in {DEPOSIT_FINALIZED, WITHDRAWAL_INITIATED}:
            return DEFAULT_EVM_DECODING_OUTPUT

        # Read information from event's topics & data
        l1_token_address = bytes_to_address(context.tx_log.topics[1])
        l2_token_address = bytes_to_address(context.tx_log.topics[2])
        from_address = bytes_to_address(context.tx_log.topics[3])
        to_address = bytes_to_address(context.tx_log.data[:32])
        raw_amount = int.from_bytes(context.tx_log.data[32:64])

        if l1_token_address == ZERO_ADDRESS:
            # This means that ETH was bridged
            asset = self.node_inquirer.native_token
            valid_assets = self.native_assets
        else:
            # Otherwise it is an ERC20 token bridging event
            try:
                asset = EvmToken(identifier=evm_address_to_identifier(
                    address=l2_token_address,
                    chain_id=self.node_inquirer.chain_id,
                    token_type=TokenKind.ERC20,
                ))
                valid_assets = (asset,)
            except (UnknownAsset, WrongAssetType):
                # can't call `notify_user`` since we don't have any particular event here.
                log.error(f'Failed to resolve asset with address {l2_token_address} to an {self.node_inquirer.chain_name} token')  # noqa: E501
                return DEFAULT_EVM_DECODING_OUTPUT

        amount = asset_normalized_value(asset=asset, amount=raw_amount)

        expected_event_type, new_event_type, from_chain, to_chain, expected_location_label = bridge_prepare_data(  # noqa: E501
            tx_log=context.tx_log,  # args are opposite here due to the way logs are
            deposit_topics=(WITHDRAWAL_INITIATED,),
            source_chain=self.node_inquirer.chain_id,
            target_chain=ChainID.ETHEREUM,
            from_address=to_address,
            to_address=from_address,
        )

        # Find one corresponding transfer event and update it. For chains that support
        # multiple native asset representations (e.g. Optimism ETH and OP-ETH), prefer
        # the first entry from valid_assets and avoid decoding the same bridge twice.
        matched_event = None
        for expected_asset in valid_assets:
            if (matched_event := next((
                    event for event in context.decoded_events
                    if (
                        event.event_type == expected_event_type and
                        event.location_label == expected_location_label and
                        event.address in (ZERO_ADDRESS, *self.bride_addresses) and
                        event.asset == expected_asset and
                        event.amount == amount
                    )
            ), None)) is not None:
                break

        if matched_event is not None:
            bridge_match_transfer(
                event=matched_event,
                from_address=from_address,
                to_address=to_address,
                from_chain=from_chain,
                to_chain=to_chain,
                amount=amount,
                asset=asset,
                expected_event_type=expected_event_type,
                new_event_type=new_event_type,
                counterparty=self.counterparty,
                transfer_id=get_messenger_transfer_id(context.all_logs),
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_deposit_transaction(
            self,
            transaction: L2WithL1FeesTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list[EvmEvent]:
        """Decode ETH bridged from L1 by depositing directly to the OptimismPortal.

        The portal mints the deposited ETH on the L2 via a system deposit transaction
        that emits no logs, so the bridging can only be recognized by the transaction
        type. The mint has already been decoded as a plain ETH transfer (a transaction
        to self when bridging to the depositing address), so find that event and turn
        it into a bridge event. Deposit transactions pay no L2 fees and their input
        data is just the deposit's extra data, so also remove the zero gas and message
        events decoded from them.
        """
        if transaction.value == 0:
            return decoded_events  # not an ETH mint. Deposits relayed via the messenger contracts are decoded by their logs  # noqa: E501

        amount = from_wei(FVal(transaction.value))
        for event in decoded_events:
            if (
                    event.event_type in (HistoryEventType.TRANSACTION_TO_SELF, HistoryEventType.RECEIVE) and  # noqa: E501
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.location_label == transaction.to_address and
                    event.asset == (native_token := self.node_inquirer.native_token) and
                    event.amount == amount
            ):
                bridge_match_transfer(
                    event=event,
                    from_address=transaction.from_address,
                    to_address=transaction.to_address,  # type: ignore[arg-type]  # matching location_label above guarantees to_address is not None
                    from_chain=ChainID.ETHEREUM,
                    to_chain=self.node_inquirer.chain_id,
                    amount=amount,
                    asset=native_token,
                    expected_event_type=HistoryEventType.RECEIVE,
                    new_event_type=HistoryEventType.WITHDRAWAL,
                    counterparty=self.counterparty,
                )
                break
        else:
            return decoded_events  # no tracked ETH transfer was decoded for this deposit transaction  # noqa: E501

        return [
            event for event in decoded_events
            if not (
                (event.event_subtype == HistoryEventSubType.FEE and event.counterparty == CPT_GAS) or  # noqa: E501
                event.event_subtype == HistoryEventSubType.MESSAGE
            )
        ]

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.bride_addresses, (self._decode_receive_or_deposit,))

    # -- L2WithL1FeesDecoderInterface methods

    def decoding_by_tx_type(self) -> dict[int, list[tuple[int, Callable]]]:
        return {
            DEPOSIT_TX_TYPE: [
                (0, self._decode_deposit_transaction),  # these transactions contain no logs so we can only run a decoder as a post decoding rule  # noqa: E501
            ],
        }
