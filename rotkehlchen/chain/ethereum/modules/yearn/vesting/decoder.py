import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.modules.yearn.constants import YEARN_ICON
from rotkehlchen.chain.evm.constants import SIMPLE_CLAIM
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import bytes_to_address, timestamp_to_date

from .constants import (
    CPT_YEARN_VESTING,
    DISOWNED_TOPIC,
    PERMISSIONLESS_CLAIMS_SET_TOPIC,
    REVOCATION_RENOUNCED_TOPIC,
    REVOKED_V3_TOPIC,
    REVOKED_V4_TOPIC,
    RUG_PULL_TOPIC,
    SET_OPEN_CLAIM_TOPIC,
    TOKEN_VESTING_ESCROW_CREATED_V4_TOPIC,
    VESTING_ESCROW_ABI,
    VESTING_ESCROW_CREATED_TOPIC,
    VESTING_ESCROW_CREATED_V3_TOPIC,
    VESTING_ESCROW_PROXY_CODES,
    VESTING_FACTORY_V1,
    VESTING_FACTORY_V2,
    VESTING_FACTORY_V3,
    VESTING_FACTORY_V4,
    VYPER_DONATION_ADDRESS,
    YEARN_VESTING_LABEL,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import ActionItem
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class YearnvestingDecoder(EvmDecoderInterface):
    """Decoder for the yearn vesting escrows.
    https://github.com/yearn/yearn-vesting-escrow

    The escrows are minimal proxies deployed by the factories, one per recipient,
    so their addresses can't be known statically. Escrow events are matched by
    topic and the emitting address is verified against the known proxy bytecode.
    """

    def __init__(
            self,
            ethereum_inquirer: EthereumInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.escrow_check_cache: dict[ChecksumEvmAddress, bool] = {}
        self.escrow_recipients: dict[ChecksumEvmAddress, ChecksumEvmAddress] = {}

    def _is_vesting_escrow(self, address: ChecksumEvmAddress) -> bool:
        """Check if the given address is a yearn vesting escrow by comparing its
        runtime bytecode against the known escrow proxy bytecodes. Caches results
        since the same escrow is queried for every one of its decoded transactions.
        """
        if (cached_result := self.escrow_check_cache.get(address)) is not None:
            return cached_result

        try:
            code = self.node_inquirer.get_code(address)
        except RemoteError as e:
            log.error('Failed to query the code of a possible yearn vesting escrow %s due to %s', address, e)  # noqa: E501
            return False  # not cached so it can be retried later

        self.escrow_check_cache[address] = (result := code.lower() in VESTING_ESCROW_PROXY_CODES)
        return result

    def _decode_escrow_creation(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the escrow creation events emitted by the vesting escrow factories"""
        if context.tx_log.topics[0] in (VESTING_ESCROW_CREATED_TOPIC, VESTING_ESCROW_CREATED_V3_TOPIC):  # noqa: E501
            funder = bytes_to_address(context.tx_log.topics[1])
            escrow = bytes_to_address(context.tx_log.data[:32])
            raw_amount = int.from_bytes(context.tx_log.data[32:64])
            vesting_start = int.from_bytes(context.tx_log.data[64:96])
            vesting_duration = int.from_bytes(context.tx_log.data[96:128])
        elif context.tx_log.topics[0] == TOKEN_VESTING_ESCROW_CREATED_V4_TOPIC:
            escrow = bytes_to_address(context.tx_log.topics[1])
            funder = bytes_to_address(context.tx_log.data[:32])
            raw_amount = int.from_bytes(context.tx_log.data[64:96])
            vesting_start = int.from_bytes(context.tx_log.data[96:128])
            vesting_duration = int.from_bytes(context.tx_log.data[128:160])
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        self.escrow_check_cache[escrow] = True  # save a get_code query for same-session decodes
        token = self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[2]))
        recipient = bytes_to_address(context.tx_log.topics[3])
        amount = token_normalized_value(token_amount=raw_amount, token=token)
        end_date = timestamp_to_date(
            ts=Timestamp(vesting_start + vesting_duration),
            formatstr='%d/%m/%Y %H:%M:%S',
        )
        deposit_found = False
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.address == escrow and
                    event.amount == amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
                event.counterparty = CPT_YEARN_VESTING
                event.notes = f'Deposit {amount} {token.symbol} in a Yearn vesting escrow for {recipient} vesting until {end_date}'  # noqa: E501
                event.extra_data = {'recipient': recipient}
                deposit_found = True
            elif (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.address == VYPER_DONATION_ADDRESS
            ):
                event.event_subtype = HistoryEventSubType.DONATE
                event.counterparty = CPT_YEARN_VESTING
                event.notes = f'Donate {event.amount} {token.symbol} to the Vyper project'

        if deposit_found is False and self.base.is_tracked(funder):
            # in the v0.1.0/v0.2.0 factories the tokens move from the pre-funded factory
            # to the escrow, so there is no transfer from the funder to turn into a deposit
            return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.NONE,
                asset=token,
                amount=ZERO,
                location_label=funder,
                notes=f'Create a Yearn vesting escrow for {recipient} with {amount} {token.symbol} vesting until {end_date}',  # noqa: E501
                counterparty=CPT_YEARN_VESTING,
                address=escrow,
                extra_data={'recipient': recipient},
            )])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a claim of vested tokens from an escrow. The token transfer to the
        beneficiary is matched by the raw amount instead of the log's address argument
        since v0.3.0+ escrows allow redirecting a claim to any beneficiary address.
        """
        raw_amount = int.from_bytes(context.tx_log.data[:32])
        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == context.tx_log.address and
                    event.amount == asset_normalized_value(
                        amount=raw_amount,
                        asset=(crypto_asset := event.asset.resolve_to_crypto_asset()),
                    )
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                event.counterparty = CPT_YEARN_VESTING
                event.notes = f'Claim {event.amount} {crypto_asset.symbol} from a Yearn vesting escrow'  # noqa: E501
                break
        else:
            log.error('Yearn vesting escrow claim transfer was not found for %s', context.transaction.tx_hash)  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_revocation(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a revocation (rug pull) of an escrow, clawing back the unvested
        tokens. Only the receiver of the clawed back tokens sees an event since the
        transaction is not queried for the vesting recipient.
        """
        if context.tx_log.topics[0] == RUG_PULL_TOPIC:
            recipient = bytes_to_address(context.tx_log.data[:32])
            raw_amount = int.from_bytes(context.tx_log.data[32:64])
        elif context.tx_log.topics[0] == REVOKED_V3_TOPIC:
            recipient = bytes_to_address(context.tx_log.data[:32])
            raw_amount = int.from_bytes(context.tx_log.data[64:96])
        else:  # REVOKED_V4_TOPIC
            recipient = bytes_to_address(context.tx_log.topics[1])
            raw_amount = int.from_bytes(context.tx_log.data[:32])

        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.address == context.tx_log.address and
                    event.amount == asset_normalized_value(
                        amount=raw_amount,
                        asset=(crypto_asset := event.asset.resolve_to_crypto_asset()),
                    )
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
                event.counterparty = CPT_YEARN_VESTING
                event.notes = f'Revoke the Yearn vesting escrow of {recipient} clawing back {event.amount} {crypto_asset.symbol}'  # noqa: E501
                break
        else:
            log.error('Yearn vesting escrow revocation transfer was not found for %s', context.transaction.tx_hash)  # noqa: E501

        return DEFAULT_EVM_DECODING_OUTPUT

    def _get_escrow_recipient(self, escrow: ChecksumEvmAddress) -> ChecksumEvmAddress | None:
        """Query and cache the recipient of the given vesting escrow"""
        if (recipient := self.escrow_recipients.get(escrow)) is not None:
            return recipient

        try:
            recipient = deserialize_evm_address(self.node_inquirer.call_contract(
                contract_address=escrow,
                abi=VESTING_ESCROW_ABI,
                method_name='recipient',
            ))
        except (RemoteError, DeserializationError) as e:
            log.error('Failed to query the recipient of yearn vesting escrow %s due to %s', escrow, e)  # noqa: E501
            return None

        self.escrow_recipients[escrow] = recipient
        return recipient

    def _decode_admin_events(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the escrow administrative events: renouncing the right to revoke and
        toggling permissionless (open) claiming.
        """
        actor: ChecksumEvmAddress | None
        if context.tx_log.topics[0] in (DISOWNED_TOPIC, REVOCATION_RENOUNCED_TOPIC):
            if context.tx_log.topics[0] == DISOWNED_TOPIC:
                if any(  # a v0.3.0 revocation also disowns the escrow, so it is not a standalone renouncement  # noqa: E501
                    tx_log.address == context.tx_log.address and tx_log.topics[0] == REVOKED_V3_TOPIC  # noqa: E501
                    for tx_log in context.all_logs
                ):
                    return DEFAULT_EVM_DECODING_OUTPUT

                actor = bytes_to_address(context.tx_log.data[:32])
            else:
                actor = bytes_to_address(context.tx_log.topics[1])

            notes = 'Renounce the right to revoke a Yearn vesting escrow'
        else:  # SET_OPEN_CLAIM_TOPIC or PERMISSIONLESS_CLAIMS_SET_TOPIC
            # only the recipient can toggle it, but the log doesn't carry it
            actor = self._get_escrow_recipient(context.tx_log.address)
            action = 'Enable' if int.from_bytes(context.tx_log.data[:32]) != 0 else 'Disable'
            notes = f'{action} permissionless claims of a Yearn vesting escrow'

        if actor is None or not self.base.is_tracked(actor):
            return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.UPDATE,
            asset=A_ETH,
            amount=ZERO,
            location_label=actor,
            notes=notes,
            counterparty=CPT_YEARN_VESTING,
            address=context.tx_log.address,
        )])

    def _decode_escrow_events_by_topic(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            action_items: list[ActionItem],
            all_logs: list[EvmTxReceiptLog],
    ) -> EvmDecodingOutput:
        """Match escrow events by topic since the escrow addresses are not known
        statically, verifying the emitting address is a yearn vesting escrow.
        """
        if tx_log.topics[0] not in (
            SIMPLE_CLAIM,
            RUG_PULL_TOPIC,
            REVOKED_V3_TOPIC,
            REVOKED_V4_TOPIC,
            DISOWNED_TOPIC,
            SET_OPEN_CLAIM_TOPIC,
            REVOCATION_RENOUNCED_TOPIC,
            PERMISSIONLESS_CLAIMS_SET_TOPIC,
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self._is_vesting_escrow(tx_log.address):
            return DEFAULT_EVM_DECODING_OUTPUT

        context = DecoderContext(
            tx_log=tx_log,
            transaction=transaction,
            decoded_events=decoded_events,
            action_items=action_items,
            all_logs=all_logs,
        )
        if tx_log.topics[0] == SIMPLE_CLAIM:
            return self._decode_claim(context)
        if tx_log.topics[0] in (RUG_PULL_TOPIC, REVOKED_V3_TOPIC, REVOKED_V4_TOPIC):
            return self._decode_revocation(context)

        return self._decode_admin_events(context)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(
            (VESTING_FACTORY_V1, VESTING_FACTORY_V2, VESTING_FACTORY_V3, VESTING_FACTORY_V4),
            (self._decode_escrow_creation,),
        )

    def decoding_rules(self) -> list[Callable]:
        return [self._decode_escrow_events_by_topic]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (
            CounterpartyDetails(
                identifier=CPT_YEARN_VESTING,
                label=YEARN_VESTING_LABEL,
                image=YEARN_ICON,
            ),
        )
