import logging
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.modules.lido.constants import (
    STETH_MAX_ROUND_ERROR_WEI,
    WITHDRAWAL_QUEUE,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.constants.assets import A_ETH, A_STETH, A_WSTETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, TokenKind
from rotkehlchen.utils.misc import bytes_to_address, from_wei

from .constants import (
    BOND_CLAIMED_STETH,
    BOND_CLAIMED_UNSTETH,
    BOND_CLAIMED_WSTETH,
    BOND_DEPOSITED_ETH,
    BOND_DEPOSITED_STETH,
    BOND_DEPOSITED_WSTETH,
    CPT_LIDO_CSM,
    FEE_DISTRIBUTED_V1,
    LIDO_CSM_MODULE_CONTRACTS,
    NODE_OPERATOR_ADDED,
    NODE_OPERATOR_ADDED_V1,
    NODE_OPERATOR_MANAGER_ADDRESS_CHANGED,
    NODE_OPERATOR_REWARD_ADDRESS_CHANGED,
    OPERATOR_FEE_DISTRIBUTED,
    SIGNING_KEY_ADDED,
    LidoCsmStakingModule,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.types import ChecksumEvmAddress
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BOND_CLAIM_TOPICS: Final = {BOND_CLAIMED_STETH, BOND_CLAIMED_WSTETH, BOND_CLAIMED_UNSTETH}


class LidoCsmDecoder(EvmDecoderInterface):
    """Decodes node operator, bond, and reward events for Lido CSM.

    Only transactions already imported through normal Ethereum transaction discovery are decoded.
    An address appearing solely in a CSM log topic does not make that transaction discoverable.
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
        self.steth = A_STETH.resolve_to_evm_token()
        self.wsteth = A_WSTETH.resolve_to_evm_token()
        self.steth_tolerance = from_wei(STETH_MAX_ROUND_ERROR_WEI)
        self.modules_by_address: dict[ChecksumEvmAddress, LidoCsmStakingModule] = {}
        for staking_module, contracts in LIDO_CSM_MODULE_CONTRACTS.items():
            for address in (contracts.module, contracts.accounting, contracts.fee_distributor):
                self.modules_by_address[address] = staking_module

    def _get_operator(self, context: DecoderContext) -> tuple[LidoCsmStakingModule, int]:
        """Return the staking module that emitted the log and the node operator id it is about.
        Every decoded event of the modules has the node operator id as its first topic."""
        return (
            self.modules_by_address[context.tx_log.address],
            int.from_bytes(context.tx_log.topics[1]),
        )

    def _get_tracked_tx_party(self, context: DecoderContext) -> ChecksumEvmAddress | None:
        """Return the tracked sender of the transaction or, for contract wallets such as a Safe,
        the tracked contract it called. Used for events whose log names no user address."""
        if self.base.is_tracked(context.transaction.from_address):
            return context.transaction.from_address
        if (
                context.transaction.to_address is not None and
                self.base.is_tracked(context.transaction.to_address)
        ):
            return context.transaction.to_address
        return None

    def _make_informational_event(
            self,
            context: DecoderContext,
            event_subtype: HistoryEventSubType,
            location_label: ChecksumEvmAddress,
            notes: str,
            asset: Asset = A_ETH,
            amount: FVal = ZERO,
    ) -> EvmDecodingOutput:
        return EvmDecodingOutput(events=[self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            location_label=location_label,
            notes=notes,
            counterparty=CPT_LIDO_CSM,
            address=context.tx_log.address,
        )])

    def _find_transfer_event(
            self,
            context: DecoderContext,
            event_type: HistoryEventType,
            asset: Asset,
            user: ChecksumEvmAddress,
            amount: FVal,
            address: ChecksumEvmAddress | None,
    ) -> EvmEvent | None:
        """Find the not yet decoded transfer of the given asset from or to the user.

        stETH moves shares, so the transferred amount can differ by a few wei from the amount
        that the module logs. The address is None for ETH deposits, which can go through a gate
        contract before reaching the module.
        """
        tolerance = self.steth_tolerance if asset == self.steth else ZERO
        for event in context.decoded_events:
            if (
                    event.event_type == event_type and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == asset and
                    event.location_label == user and
                    (address is None or event.address == address) and
                    abs(event.amount - amount) <= tolerance
            ):
                return event

        return None

    def _find_steth_transfer(
            self,
            context: DecoderContext,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress,
    ) -> FVal | None:
        """Find the amount of the last stETH transfer between the two addresses that precedes
        the log being decoded. Used to get the stETH that a conversion moves from or to a bond,
        since the module logs the amount in the asset that the user deposited or claimed.
        """
        amount = None
        for tx_log in context.all_logs:
            if (
                    tx_log.log_index < context.tx_log.log_index and
                    tx_log.address == self.steth.evm_address and
                    len(tx_log.topics) == 3 and
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    bytes_to_address(tx_log.topics[1]) == from_address and
                    bytes_to_address(tx_log.topics[2]) == to_address
            ):
                amount = from_wei(int.from_bytes(tx_log.data[:32]))

        return amount

    def _make_bond_event(
            self,
            context: DecoderContext,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            amount: FVal,
            user: ChecksumEvmAddress,
            notes: str,
    ) -> EvmEvent:
        """Make a stETH event for the part of a bond movement that has no transfer of its own,
        such as the stETH an ETH deposit is converted to inside the accounting contract."""
        return self.base.make_event_next_index(
            tx_ref=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=self.steth,
            amount=amount,
            location_label=user,
            notes=notes,
            counterparty=CPT_LIDO_CSM,
            address=context.tx_log.address,
        )

    def _decode_node_operator_added(self, context: DecoderContext) -> EvmDecodingOutput:
        manager = bytes_to_address(context.tx_log.topics[2])
        reward = bytes_to_address(context.tx_log.topics[3])
        if self.base.is_tracked(manager):
            user = manager
        elif self.base.is_tracked(reward):
            user = reward
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        staking_module, operator_id = self._get_operator(context)
        addresses = (
            f'manager and reward address {manager}' if manager == reward else
            f'manager address {manager} and reward address {reward}'
        )
        return self._make_informational_event(
            context=context,
            event_subtype=HistoryEventSubType.CREATE,
            location_label=user,
            notes=f'Create {staking_module.label} node operator {operator_id} with {addresses}',
        )

    def _decode_address_changed(self, context: DecoderContext, role: str) -> EvmDecodingOutput:
        old_address = bytes_to_address(context.tx_log.topics[2])
        new_address = bytes_to_address(context.tx_log.topics[3])
        if self.base.is_tracked(new_address):
            user = new_address
        elif self.base.is_tracked(old_address):
            user = old_address
        else:
            return DEFAULT_EVM_DECODING_OUTPUT

        staking_module, operator_id = self._get_operator(context)
        return self._make_informational_event(
            context=context,
            event_subtype=HistoryEventSubType.UPDATE,
            location_label=user,
            notes=(
                f'Change the {role} address of {staking_module.label} node operator '
                f'{operator_id} from {old_address} to {new_address}'
            ),
        )

    def _decode_signing_keys_added(self, context: DecoderContext) -> EvmDecodingOutput:
        """Create one event for all the keys a transaction uploads for a node operator.

        Each key emits its own SigningKeyAdded log, so the event is created when decoding the
        first of them and the others are skipped.
        """
        keys_count = 0
        for tx_log in context.all_logs:
            if (
                    tx_log.address != context.tx_log.address or
                    tx_log.topics[0] != SIGNING_KEY_ADDED or
                    tx_log.topics[1] != context.tx_log.topics[1]
            ):
                continue
            if keys_count == 0 and tx_log.log_index != context.tx_log.log_index:
                return DEFAULT_EVM_DECODING_OUTPUT  # not the first key, already decoded
            keys_count += 1

        if (user := self._get_tracked_tx_party(context)) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        staking_module, operator_id = self._get_operator(context)
        return self._make_informational_event(
            context=context,
            event_subtype=HistoryEventSubType.NONE,
            location_label=user,
            notes=(
                f'Add {keys_count} validator key{"s" if keys_count > 1 else ""} to '
                f'{staking_module.label} node operator {operator_id}'
            ),
        )

    def _decode_module_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] in (NODE_OPERATOR_ADDED, NODE_OPERATOR_ADDED_V1):
            return self._decode_node_operator_added(context)
        elif context.tx_log.topics[0] == NODE_OPERATOR_MANAGER_ADDRESS_CHANGED:
            return self._decode_address_changed(context, role='manager')
        elif context.tx_log.topics[0] == NODE_OPERATOR_REWARD_ADDRESS_CHANGED:
            return self._decode_address_changed(context, role='reward')
        elif context.tx_log.topics[0] == SIGNING_KEY_ADDED:
            return self._decode_signing_keys_added(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_bond_deposit(self, context: DecoderContext, asset: Asset) -> EvmDecodingOutput:
        if not self.base.is_tracked(depositor := bytes_to_address(context.tx_log.data[:32])):
            return DEFAULT_EVM_DECODING_OUTPUT

        staking_module, operator_id = self._get_operator(context)
        if (event := self._find_transfer_event(
            context=context,
            event_type=HistoryEventType.SPEND,
            asset=asset,
            user=depositor,
            amount=from_wei(int.from_bytes(context.tx_log.data[32:64])),
            address=None if asset == A_ETH else context.tx_log.address,
        )) is None:
            log.error(
                'Could not find the transfer of a Lido CSM bond deposit',
                staking_module=staking_module.name,
                node_operator_id=operator_id,
                asset=asset.identifier,
                tx_hash=str(context.transaction.tx_hash),
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        event.counterparty = CPT_LIDO_CSM
        bond = f'as bond for {staking_module.label} node operator {operator_id}'
        if asset == self.steth:
            event.event_type = HistoryEventType.DEPOSIT
            event.event_subtype = HistoryEventSubType.DEPOSIT_TO_PROTOCOL
            event.notes = f'Deposit {event.amount} stETH {bond}'
            return DEFAULT_EVM_DECODING_OUTPUT

        # The bond is always held as stETH. So ETH and wstETH are first converted to it in the
        # wallet and the received stETH is then deposited, which is what the balances should see.
        if (steth_amount := self._find_steth_transfer(
            context=context,
            from_address=ZERO_ADDRESS if asset == A_ETH else self.wsteth.evm_address,
            to_address=LIDO_CSM_MODULE_CONTRACTS[staking_module].accounting,
        )) is None:
            log.error(
                'Could not find the stETH of a Lido CSM bond deposit',
                staking_module=staking_module.name,
                node_operator_id=operator_id,
                asset=asset.identifier,
                tx_hash=str(context.transaction.tx_hash),
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if asset == A_ETH:
            event.event_type = HistoryEventType.DEPOSIT
            event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
            event.notes = f'Submit {event.amount} ETH to Lido {bond}'
            conversion_type, conversion_subtype = HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED  # noqa: E501
            conversion_notes = f'Receive {steth_amount} stETH in exchange for the deposited ETH'
        else:
            event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
            event.notes = f'Return {event.amount} wstETH to be unwrapped {bond}'
            conversion_type, conversion_subtype = HistoryEventType.WITHDRAWAL, HistoryEventSubType.REDEEM_WRAPPED  # noqa: E501
            conversion_notes = f'Unwrap {steth_amount} stETH'

        conversion_event = self._make_bond_event(
            context=context,
            event_type=conversion_type,
            event_subtype=conversion_subtype,
            amount=steth_amount,
            user=depositor,
            notes=conversion_notes,
        )
        deposit_event = self._make_bond_event(
            context=context,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
            amount=steth_amount,
            user=depositor,
            notes=f'Deposit {steth_amount} stETH {bond}',
        )
        maybe_reshuffle_events(
            ordered_events=[event, conversion_event, deposit_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(events=[conversion_event, deposit_event])

    def _decode_bond_claim(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode a claim of the bond in excess of what the operator's validators require, which
        is where the rewards accrue, as stETH, wstETH or a Lido withdrawal request (unstETH).

        If the recipient is tracked, the claim is a withdrawal of stETH from the bond, followed
        by its conversion to what the recipient gets (wstETH or a withdrawal request NFT). If
        only the party that sent the claim is tracked, an informational event records it.
        """
        staking_module, operator_id = self._get_operator(context)
        recipient = bytes_to_address(context.tx_log.data[:32])
        amount = from_wei(int.from_bytes(context.tx_log.data[32:64]))
        request_id: int | None = None  # only set for a withdrawal request (unstETH) claim
        if is_withdrawal_request := context.tx_log.topics[0] == BOND_CLAIMED_UNSTETH:
            # The stETH goes to the Lido withdrawal queue, which mints a withdrawal NFT to the
            # recipient. The ETH is later claimed from the queue as for any Lido withdrawal.
            request_id = int.from_bytes(context.tx_log.data[64:96])
            transfer_asset: Asset = Asset(evm_address_to_identifier(
                address=WITHDRAWAL_QUEUE,
                chain_id=ChainID.ETHEREUM,
                token_type=TokenKind.ERC721,
                collectible_id=str(request_id),
            ))
            transfer_amount, transfer_address = ONE, ZERO_ADDRESS
            token, notes_suffix = self.steth, f' as Lido withdrawal request {request_id}'
        else:
            token = self.steth if context.tx_log.topics[0] == BOND_CLAIMED_STETH else self.wsteth
            transfer_asset, transfer_amount = token, amount
            transfer_address, notes_suffix = context.tx_log.address, ''

        source = (
            f'from the bond of {staking_module.label} node operator {operator_id}{notes_suffix}'
        )
        if not self.base.is_tracked(recipient):
            if (user := self._get_tracked_tx_party(context)) is None:
                return DEFAULT_EVM_DECODING_OUTPUT

            return self._make_informational_event(
                context=context,
                event_subtype=HistoryEventSubType.NONE,
                location_label=user,
                notes=f'Claim {amount} {token.symbol} {source} to {recipient}',
                asset=token,
                amount=amount,
            )

        if (event := self._find_transfer_event(
            context=context,
            event_type=HistoryEventType.RECEIVE,
            asset=transfer_asset,
            user=recipient,
            amount=transfer_amount,
            address=transfer_address,
        )) is None:
            log.error(
                'Could not find the transfer of a Lido CSM bond claim',
                staking_module=staking_module.name,
                node_operator_id=operator_id,
                tx_hash=str(context.transaction.tx_hash),
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        event.counterparty = CPT_LIDO_CSM
        if token == self.steth and not is_withdrawal_request:
            event.event_type = HistoryEventType.WITHDRAWAL
            event.event_subtype = HistoryEventSubType.WITHDRAW_FROM_PROTOCOL
            # the received stETH can be a few wei off the logged amount
            event.notes = f'Claim {event.amount} stETH {source}'
            return DEFAULT_EVM_DECODING_OUTPUT

        # The bond is held as stETH. So it is first withdrawn from the bond as stETH and then
        # converted in the wallet to what the user receives, which is what the balances should see.
        if is_withdrawal_request:
            steth_amount: FVal | None = amount  # the log has the stETH amount
        else:
            steth_amount = self._find_steth_transfer(
                context=context,
                from_address=context.tx_log.address,
                to_address=self.wsteth.evm_address,
            )
        if steth_amount is None:
            log.error(
                'Could not find the stETH of a Lido CSM bond claim',
                staking_module=staking_module.name,
                node_operator_id=operator_id,
                tx_hash=str(context.transaction.tx_hash),
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        withdraw_event = self._make_bond_event(
            context=context,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            amount=steth_amount,
            user=recipient,
            notes=f'Claim {steth_amount} stETH {source}',
        )
        if is_withdrawal_request:
            event.notes = f'Receive Lido withdrawal request {request_id}'
            conversion_event = self._make_bond_event(
                context=context,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                amount=steth_amount,
                user=recipient,
                notes=f'Request withdrawal of {steth_amount} stETH from Lido',
            )
        else:
            conversion_event = self._make_bond_event(
                context=context,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                amount=steth_amount,
                user=recipient,
                notes=f'Wrap {steth_amount} stETH in wstETH',
            )
            event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
            event.notes = f'Receive {event.amount} wstETH after wrapping'

        maybe_reshuffle_events(
            ordered_events=[withdraw_event, conversion_event, event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(events=[withdraw_event, conversion_event])

    def _decode_accounting_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == BOND_DEPOSITED_ETH:
            return self._decode_bond_deposit(context, asset=A_ETH)
        elif context.tx_log.topics[0] == BOND_DEPOSITED_STETH:
            return self._decode_bond_deposit(context, asset=self.steth)
        elif context.tx_log.topics[0] == BOND_DEPOSITED_WSTETH:
            return self._decode_bond_deposit(context, asset=self.wsteth)
        elif context.tx_log.topics[0] in BOND_CLAIM_TOPICS:
            return self._decode_bond_claim(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_fee_distributed(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode the rewards that the fee distributor moves into a node operator's bond.

        This happens when the rewards are claimed or pulled, so the event goes to the tracked
        recipient of a claim of the same operator in this transaction, or else to the tracked
        party of the transaction. The log only has the stETH shares, so the amount is taken
        from the stETH transfer to the accounting contract that precedes it.
        """
        staking_module, operator_id = self._get_operator(context)
        contracts = LIDO_CSM_MODULE_CONTRACTS[staking_module]
        user, amount = None, None
        for tx_log in context.all_logs:
            if (
                    tx_log.log_index < context.tx_log.log_index and
                    tx_log.address == self.steth.evm_address and
                    tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER and
                    bytes_to_address(tx_log.topics[1]) == contracts.fee_distributor and
                    bytes_to_address(tx_log.topics[2]) == contracts.accounting
            ):
                amount = from_wei(int.from_bytes(tx_log.data[:32]))
            elif (
                    user is None and
                    tx_log.address == contracts.accounting and
                    tx_log.topics[0] in BOND_CLAIM_TOPICS and
                    tx_log.topics[1] == context.tx_log.topics[1] and
                    self.base.is_tracked(recipient := bytes_to_address(tx_log.data[:32]))
            ):
                user = recipient

        if user is None and (user := self._get_tracked_tx_party(context)) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        if amount is None:
            log.error(
                'Could not find the stETH transfer of a Lido CSM rewards distribution',
                staking_module=staking_module.name,
                node_operator_id=operator_id,
                tx_hash=str(context.transaction.tx_hash),
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        return self._make_informational_event(
            context=context,
            event_subtype=HistoryEventSubType.NONE,
            location_label=user,
            notes=(
                f'Distribute {amount} stETH of rewards to the bond of '
                f'{staking_module.label} node operator {operator_id}'
            ),
            asset=self.steth,
            amount=amount,
        )

    def _decode_fee_distributor_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] in (OPERATOR_FEE_DISTRIBUTED, FEE_DISTRIBUTED_V1):
            return self._decode_fee_distributed(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        mappings: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        for contracts in LIDO_CSM_MODULE_CONTRACTS.values():
            mappings[contracts.module] = (self._decode_module_event,)
            mappings[contracts.accounting] = (self._decode_accounting_event,)
            mappings[contracts.fee_distributor] = (self._decode_fee_distributor_event,)
        return mappings

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_LIDO_CSM, label='Lido CSM', image='lido_csm.svg'),)  # noqa: E501
