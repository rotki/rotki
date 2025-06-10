import logging
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import TokenEncounterInfo
from rotkehlchen.chain.ethereum.utils import (
    asset_normalized_value,
    should_update_protocol_cache,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface, ReloadableDecoderMixin
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType, ChecksumEvmAddress, EvmTransaction
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_BEEFY_FINANCE,
    SUPPORTED_BEEFY_CHAINS,
    TOKEN_RETURNED_TOPIC,
)
from .utils import query_beefy_vaults

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import FVal
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BeefyFinanceCommonDecoder(DecoderInterface, ReloadableDecoderMixin):
    """Decodes Beefy Finance vault transactions into structured history events.

    Handles both direct vault interactions and zap contract operations for
    depositing and withdrawing from yield farming vaults.
    """

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
        self.vaults: set[ChecksumEvmAddress] = set()
        self.zap_contract_address = SUPPORTED_BEEFY_CHAINS[self.evm_inquirer.chain_id]

    def _process_beefy_events(
            self,
            events: list['EvmEvent'],
            transaction: 'EvmTransaction',
            from_address: ChecksumEvmAddress | None = None,
            expected_amount: 'FVal | None' = None,
            expected_asset: 'Asset | None' = None,
    ) -> list['EvmEvent']:
        """Core logic for processing Beefy finance events.

        If `from_address` is provided, only processes events from that specific contract.

        If `expected_amount` or `expected_asset` are provided, only matches receive events
        with those exact values when multiple receives occur in transactions.
        """
        spend_events, receive_events = [], []
        is_withdrawal = False

        # process spend events and determine transaction type
        for event in events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    (from_address is None or event.address == from_address)
            ):
                # determine if withdrawal by checking if vault tokens are being spent
                spend_asset = event.asset.resolve_to_crypto_asset()
                if spend_asset.is_evm_token():
                    is_withdrawal = spend_asset.evm_address in self.vaults  # type: ignore[attr-defined]  # this is an evm token

                event.counterparty = CPT_BEEFY_FINANCE
                if is_withdrawal:
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.notes = f'Return {event.amount} {spend_asset.symbol} to a Beefy vault'
                else:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.notes = f'Deposit {event.amount} {spend_asset.symbol} in a Beefy vault'

                spend_events.append(event)

            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    (expected_amount is None or event.amount == expected_amount) and
                    (expected_asset is None or event.asset == expected_asset)
            ):
                event.counterparty = CPT_BEEFY_FINANCE
                asset_symbol = event.asset.resolve_to_asset_with_symbol().symbol

                if is_withdrawal:
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    event.notes = f'Withdraw {event.amount} {asset_symbol} from a Beefy vault'
                else:
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.notes = f'Receive {event.amount} {asset_symbol} after depositing in a Beefy vault'  # noqa: E501

                receive_events.append(event)

        if len(spend_events) == 0 or len(receive_events) == 0:
            log.error(f'Unable to find both spend and receive events for Beefy transaction {transaction}')  # noqa: E501
            return events

        maybe_reshuffle_events(
            ordered_events=spend_events + receive_events,
            events_list=events,
        )
        return events

    def _decode_deposit_or_withdrawal(
            self,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> list['EvmEvent']:
        """Decodes vault interactions by identifying spend and receive events.

        Transforms generic spend and receive events into structured deposit and withdrawal
        operations for Beefy vaults. Deposits involve spending LP tokens to receive
        vault tokens, while withdrawals involve spending vault tokens to receive LP tokens.
        """
        return self._process_beefy_events(
            events=decoded_events,
            transaction=transaction,
        )

    def _decode_zap_deposits_and_withdrawals(self, context: DecoderContext) -> DecodingOutput:
        """Decodes zap contract transactions that bundle token swaps with vault operations.

        Zap contracts allow users to deposit any token into a vault by automatically
        swapping it for the required LP tokens, or withdraw vault tokens as any desired token.
        """
        if context.tx_log.topics[0] != TOKEN_RETURNED_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        amount_returned = asset_normalized_value(
            amount=int.from_bytes(context.tx_log.data[:32]),
            asset=(token_returned := self.base.get_token_or_native(
                address=bytes_to_address(context.tx_log.topics[1]),
                encounter=TokenEncounterInfo(should_notify=False),
            )),
        )
        self._process_beefy_events(
            events=context.decoded_events,
            transaction=context.transaction,
            from_address=self.zap_contract_address,
            expected_amount=amount_returned,
            expected_asset=token_returned,
        )

        return DEFAULT_DECODING_OUTPUT

    def reload_data(self) -> Mapping['ChecksumEvmAddress', tuple[Any, ...]] | None:
        if (is_cache_updated := should_update_protocol_cache(
                userdb=self.base.database,
                cache_key=CacheType.BEEFY_VAULTS,
                args=(str(self.evm_inquirer.chain_id.serialize()),),
        )) is True:
            query_beefy_vaults(self.evm_inquirer)
            is_cache_updated = True

        if len(self.vaults) != 0 and not is_cache_updated:  # Skip database query if we already have vault data and cache wasn't updated  # noqa: E501
            return None

        with GlobalDBHandler().conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT address FROM evm_tokens WHERE protocol=? AND chain=?',
                (CPT_BEEFY_FINANCE, self.evm_inquirer.chain_id.serialize_for_db()),
            )
            self.vaults = {string_to_evm_address(row[0]) for row in cursor}

        return self.addresses_to_decoders()

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.zap_contract_address: (self._decode_zap_deposits_and_withdrawals,)}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys(self.vaults, CPT_BEEFY_FINANCE)

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {
            CPT_BEEFY_FINANCE: [(0, self._decode_deposit_or_withdrawal)],
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_BEEFY_FINANCE,
            label='Beefy Finance',
            darkmode_image='beefy_finance_dark.svg',
            image='beefy_finance_light.svg',
        ),)
