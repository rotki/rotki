import logging
from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import UnderlyingToken
from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    get_evm_token,
    get_or_create_evm_token,
    token_normalized_value,
)
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC, WITHDRAW_TOPIC_V3, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    EvmDecodingOutput,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import TokenKind
from rotkehlchen.utils.misc import bytes_to_address

from .constants import CPT_KILN, KILN_CPT_DETAILS, KILN_DEFI_VAULT_BEACONS, KILN_VAULT_ABI
from .utils import has_beacon

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.decoding.structures import ActionItem
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class KilnDefiCommonDecoder(EvmDecoderInterface):
    """Decoder for Kiln DeFi vaults.

    These are ERC4626 vaults that lend the deposited asset in a protocol such as Aave,
    Compound or Morpho. Kiln deploys one vault per partner, protocol, asset and chain, so
    there are too many, and too often new ones, to list. Instead the ERC4626 Deposit and
    Withdraw logs of tracked accounts are checked for coming from a vault behind the
    chain's Kiln vault beacon, once per vault.
    """

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.vault_beacon = KILN_DEFI_VAULT_BEACONS[evm_inquirer.chain_id]
        # results of the on chain vault checks, only cached when the check completed
        self.vault_checks: dict[ChecksumEvmAddress, bool] = {}

    def _is_kiln_vault(self, address: ChecksumEvmAddress) -> bool:
        if (is_vault := self.vault_checks.get(address)) is not None:
            return is_vault

        try:
            is_vault = has_beacon(
                evm_inquirer=self.node_inquirer,
                address=address,
                beacon=self.vault_beacon,
            )
        except RemoteError as e:
            log.error('Failed to query the beacon of possible Kiln DeFi vault', address=address, error=str(e))  # noqa: E501
            return False

        self.vault_checks[address] = is_vault
        return is_vault

    def _get_vault_and_asset_tokens(
            self,
            vault_address: ChecksumEvmAddress,
            transaction: EvmTransaction,
    ) -> tuple[EvmToken, EvmToken] | None:
        """Get the vault share token, tagged with the Kiln protocol and its underlying
        asset so that it can be priced, and the asset token. The asset is only queried
        on chain the first time a vault is seen."""
        if (
                (vault_token := get_evm_token(
                    evm_address=vault_address,
                    chain_id=self.node_inquirer.chain_id,
                )) is not None and
                vault_token.protocol == CPT_KILN and
                len(vault_token.underlying_tokens) == 1
        ):
            asset_address = vault_token.underlying_tokens[0].address
        else:
            try:
                asset_address = self.node_inquirer.call_contract(
                    contract_address=vault_address,
                    abi=KILN_VAULT_ABI,
                    method_name='asset',
                )
            except RemoteError as e:
                log.error('Failed to query the asset of Kiln DeFi vault', address=vault_address, error=str(e))  # noqa: E501
                return None

            vault_token = get_or_create_evm_token(
                userdb=self.base.database,
                evm_address=vault_address,
                chain_id=self.node_inquirer.chain_id,
                evm_inquirer=self.node_inquirer,
                protocol=CPT_KILN,
                underlying_tokens=[UnderlyingToken(
                    address=asset_address,
                    token_kind=TokenKind.ERC20,
                    weight=ONE,
                )],
                encounter=(encounter := TokenEncounterInfo(tx_ref=transaction.tx_hash)),
            )
            self.base.get_or_create_evm_token(address=asset_address, encounter=encounter)

        return vault_token, self.base.get_or_create_evm_token(address=asset_address)

    def _decode_deposit(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
    ) -> EvmDecodingOutput:
        """Decode a deposit of the asset by `sender` for vault shares minted to `owner`"""
        sender, owner = bytes_to_address(tx_log.topics[1]), bytes_to_address(tx_log.topics[2])
        if (tokens := self._get_vault_and_asset_tokens(
            vault_address=tx_log.address,
            transaction=transaction,
        )) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        vault_token, asset = tokens
        asset_amount = token_normalized_value(int.from_bytes(tx_log.data[:32]), asset)
        shares_amount = token_normalized_value(int.from_bytes(tx_log.data[32:64]), vault_token)
        out_event, in_event = None, None
        for event in decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == asset and
                    event.amount == asset_amount and
                    event.address == tx_log.address and
                    event.location_label == sender
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {asset_amount} {asset.symbol} in Kiln DeFi'
                event.counterparty = CPT_KILN
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == vault_token and
                    event.amount == shares_amount and
                    event.address == ZERO_ADDRESS and
                    event.location_label == owner
            ):
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {shares_amount} {vault_token.symbol} from depositing in Kiln DeFi'  # noqa: E501
                event.counterparty = CPT_KILN
                in_event = event

        if out_event is None and in_event is None:
            log.error('Failed to find the transfers of a Kiln DeFi vault deposit', transaction=transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KILN)

    def _decode_withdrawal(
            self,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
    ) -> EvmDecodingOutput:
        """Decode burning the shares of `owner` for the asset sent to `receiver`"""
        receiver, owner = bytes_to_address(tx_log.topics[2]), bytes_to_address(tx_log.topics[3])
        if (tokens := self._get_vault_and_asset_tokens(
            vault_address=tx_log.address,
            transaction=transaction,
        )) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        vault_token, asset = tokens
        asset_amount = token_normalized_value(int.from_bytes(tx_log.data[:32]), asset)
        shares_amount = token_normalized_value(int.from_bytes(tx_log.data[32:64]), vault_token)
        out_event, in_event = None, None
        for event in decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == vault_token and
                    event.amount == shares_amount and
                    event.address == ZERO_ADDRESS and
                    event.location_label == owner
            ):
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {shares_amount} {vault_token.symbol} to Kiln DeFi'
                event.counterparty = CPT_KILN
                out_event = event
            elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == asset and
                    event.amount == asset_amount and
                    event.address == tx_log.address and
                    event.location_label == receiver
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Withdraw {asset_amount} {asset.symbol} from Kiln DeFi'
                event.counterparty = CPT_KILN
                in_event = event

        if out_event is None and in_event is None:
            log.error('Failed to find the transfers of a Kiln DeFi vault withdrawal', transaction=transaction)  # noqa: E501
            return DEFAULT_EVM_DECODING_OUTPUT

        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=decoded_events,
        )
        return EvmDecodingOutput(matched_counterparty=CPT_KILN)

    def _decode_vault_event(
            self,
            token: EvmToken | None,  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
            strict: bool = False,  # pylint: disable=unused-argument
    ) -> EvmDecodingOutput:
        """Decode ERC4626 deposits and withdrawals of tracked accounts in Kiln vaults.

        Only vaults whose shares were minted to or burned from a tracked owner, and whose
        share transfer no other decoder has claimed, get the on chain vault check. Vaults
        of other protocols are decoded by their own decoders before the rules run, so
        this avoids a query for each of them.
        """
        if (topic := tx_log.topics[0]) == DEPOSIT_TOPIC and len(tx_log.topics) == 3:
            decode_fn: Callable[..., EvmDecodingOutput] = self._decode_deposit
        elif topic == WITHDRAW_TOPIC_V3 and len(tx_log.topics) == 4:
            decode_fn = self._decode_withdrawal
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        owner = bytes_to_address(tx_log.topics[-1])
        shares_identifier = evm_address_to_identifier(
            address=tx_log.address,
            chain_id=self.node_inquirer.chain_id,
            token_type=TokenKind.ERC20,
        )
        if (
                not any(
                    event.asset.identifier == shares_identifier and
                    event.counterparty is None and
                    event.address == ZERO_ADDRESS and
                    event.location_label == owner
                    for event in decoded_events
                ) or
                not self._is_kiln_vault(tx_log.address)
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        return decode_fn(tx_log=tx_log, transaction=transaction, decoded_events=decoded_events)

    # -- DecoderInterface methods

    def decoding_rules(self) -> list[Callable]:
        return [self._decode_vault_event]

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (KILN_CPT_DETAILS,)
