import logging
from typing import TYPE_CHECKING, Any, Final, NamedTuple

import rlp
from eth_utils import keccak, to_checksum_address

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import (
    TokenEncounterInfo,
    asset_normalized_value,
    get_or_create_evm_token,
)
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.constants import ERC20_OR_ERC721_TRANSFER
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import NotERC20Conformant, NotERC721Conformant, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Timestamp, TokenKind
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CPT_FLUID,
    DEX_BORROW_DEBT,
    DEX_BORROW_PERFECT_DEBT,
    DEX_DEPOSIT_COL,
    DEX_DEPOSIT_PERFECT_COL,
    DEX_PAYBACK_DEBT,
    DEX_PAYBACK_DEBT_ONE_TOKEN,
    DEX_PAYBACK_PERFECT_DEBT,
    DEX_SHARES_FIRST_COL_TOPICS,
    DEX_SHARES_FIRST_DEBT_TOPICS,
    DEX_SHARES_LAST_COL_TOPICS,
    DEX_SHARES_LAST_DEBT_TOPICS,
    DEX_WITHDRAW_COL,
    DEX_WITHDRAW_COL_ONE_TOKEN,
    DEX_WITHDRAW_PERFECT_COL,
    FLUID_CPT_DETAILS,
    FLUID_LIQUIDITY,
    FLUID_VAULT_FACTORY,
    LIQUIDITY_LOG_OPERATE,
    NEW_POSITION_MINTED,
    VAULT_CONSTANTS_ABI,
    VAULT_FACTORY_ABI,
    VAULT_LOG_LIQUIDATE,
    VAULT_LOG_OPERATE,
)

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset, EvmToken
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

FLUID_PRECOMPUTED_VAULT_LIMIT: Final = 256
_FACTORY_BYTES: Final = hexstring_to_bytes(FLUID_VAULT_FACTORY)
# Fluid deploys every vault via CREATE from FLUID_VAULT_FACTORY with nonce == vaultId (1..N).
PRECOMPUTED_FLUID_VAULTS: Final[frozenset[ChecksumEvmAddress]] = frozenset(
    string_to_evm_address(to_checksum_address(
        keccak(rlp.encode([_FACTORY_BYTES, vault_id]))[-20:],
    ))
    for vault_id in range(1, FLUID_PRECOMPUTED_VAULT_LIMIT + 1)
)

DEX_COL_DEPOSIT_TOPICS: Final = frozenset({DEX_DEPOSIT_COL, DEX_DEPOSIT_PERFECT_COL})
DEX_COL_WITHDRAW_TOPICS: Final = frozenset({
    DEX_WITHDRAW_COL,
    DEX_WITHDRAW_PERFECT_COL,
    DEX_WITHDRAW_COL_ONE_TOKEN,
})
DEX_DEBT_BORROW_TOPICS: Final = frozenset({DEX_BORROW_DEBT, DEX_BORROW_PERFECT_DEBT})
DEX_DEBT_PAYBACK_TOPICS: Final = frozenset({
    DEX_PAYBACK_DEBT,
    DEX_PAYBACK_PERFECT_DEBT,
    DEX_PAYBACK_DEBT_ONE_TOKEN,
})

_OPERATE_LEG_CONFIG: Final = {
    (True, True): (
        HistoryEventType.SPEND,
        HistoryEventType.DEPOSIT,
        HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
        'Deposit {amount} {symbol} as collateral to Fluid',
    ),
    (True, False): (
        HistoryEventType.RECEIVE,
        HistoryEventType.WITHDRAWAL,
        HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
        'Withdraw {amount} {symbol} as collateral from Fluid',
    ),
    (False, True): (
        HistoryEventType.RECEIVE,
        HistoryEventType.RECEIVE,
        HistoryEventSubType.GENERATE_DEBT,
        'Borrow {amount} {symbol} from Fluid',
    ),
    (False, False): (
        HistoryEventType.SPEND,
        HistoryEventType.SPEND,
        HistoryEventSubType.PAYBACK_DEBT,
        'Repay {amount} {symbol} to Fluid',
    ),
}


class VaultConstants(NamedTuple):
    supply_address: ChecksumEvmAddress
    borrow_address: ChecksumEvmAddress
    col_tokens: tuple[ChecksumEvmAddress, ChecksumEvmAddress]
    debt_tokens: tuple[ChecksumEvmAddress, ChecksumEvmAddress]


class FluidCommonDecoder(EvmDecoderInterface):
    """Decoder for Fluid borrow/collateral vaults (T1..T4) across EVM chains."""

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
        self.factory_contract = EvmContract(address=FLUID_VAULT_FACTORY, abi=VAULT_FACTORY_ABI)
        self.vault_checks: dict[ChecksumEvmAddress, bool] = {}
        self.vault_constants: dict[ChecksumEvmAddress, VaultConstants] = {}

    def _call_view(
            self,
            contract: EvmContract,
            method_name: str,
            arguments: list[Any] | None = None,
    ) -> Any | None:
        try:
            (success, result), = self.node_inquirer.multicall_2(
                calls=[(contract.address, contract.encode(method_name, arguments=arguments))],
                require_success=False,
            )
        except RemoteError as e:
            log.error(
                'Failed to query Fluid contract view',
                address=contract.address,
                method=method_name,
                error=str(e),
            )
            return None

        if not success:
            return None

        try:
            return contract.decode(result=result, method_name=method_name, arguments=arguments)[0]
        except DeserializationError as e:
            log.error(
                'Failed to decode Fluid contract view',
                address=contract.address,
                method=method_name,
                error=str(e),
            )
            return None

    def _get_prior_nft_owner(
            self,
            nft_id: int,
            transaction: EvmTransaction,
    ) -> ChecksumEvmAddress | None:
        """Return the tracked holder of a vault position NFT right before `transaction`.

        @remarks
        Ownership is rebuilt from the position NFT events decoded so far instead of `ownerOf`,
        which only reports the current holder. Only tracked accounts get events, so the latest
        one names the holder: a mint or receive leaves the NFT with its location_label, while a
        send or transfer moves it to the event's address. Events in the same second as the
        transaction are skipped since their order relative to it is unknown.

        @returns The holder, or None when no history exists or the holder is not tracked.
        """
        nft_asset = Asset(evm_address_to_identifier(
            address=FLUID_VAULT_FACTORY,
            chain_id=self.node_inquirer.chain_id,
            token_type=TokenKind.ERC721,
            collectible_id=str(nft_id),
        ))
        with self.base.database.conn.read_ctx() as cursor:
            events = DBHistoryEvents(self.base.database).get_history_events_internal(
                cursor=cursor,
                filter_query=EvmEventFilterQuery.make(
                    assets=(nft_asset,),
                    to_ts=Timestamp(transaction.timestamp - 1),
                    order_by_rules=[('timestamp', False), ('sequence_index', False)],
                    limit=1,
                ),
            )

        if len(events) == 0:
            return None

        last_event = events[0]
        holder = (
            last_event.address
            if last_event.event_type in (HistoryEventType.SPEND, HistoryEventType.TRANSFER) else
            last_event.location_label
        )
        if holder is None or not self.base.is_tracked(owner := string_to_evm_address(holder)):
            return None

        return owner

    def _is_fluid_vault(self, address: ChecksumEvmAddress) -> bool:
        """Check whether an address is a Fluid vault via CREATE table or on-chain factory."""
        if address in PRECOMPUTED_FLUID_VAULTS:
            return True

        if (cached := self.vault_checks.get(address)) is not None:
            return cached

        if (result := self._call_view(self.factory_contract, 'isVault', [address])) is None:
            return False

        self.vault_checks[address] = (is_vault := bool(result))
        return is_vault

    def _get_vault_constants(self, vault_address: ChecksumEvmAddress) -> VaultConstants | None:
        """Fetch and cache constantsView() for smart collateral / smart debt vaults."""
        if (cached := self.vault_constants.get(vault_address)) is not None:
            return cached

        vault_contract = EvmContract(address=vault_address, abi=VAULT_CONSTANTS_ABI)
        if (constants_view := self._call_view(vault_contract, 'constantsView')) is None:
            return None

        vault_constants = VaultConstants(
            supply_address=constants_view[6],
            borrow_address=constants_view[7],
            col_tokens=(constants_view[8][0], constants_view[8][1]),
            debt_tokens=(constants_view[9][0], constants_view[9][1]),
        )
        self.vault_constants[vault_address] = vault_constants
        return vault_constants

    def _resolve_asset(self, address: ChecksumEvmAddress) -> CryptoAsset | EvmToken | None:
        try:
            return self.base.get_token_or_native(address=address)
        except (NotERC20Conformant, NotERC721Conformant) as e:
            log.error('Failed to resolve Fluid token %s due to %s', address, e)
            return None

    def _decode_liquidity_log(self, context: DecoderContext) -> EvmDecodingOutput:
        """Mark transaction for Fluid post-decoding only when a vault event is also present.

        FluidLiquidity is shared with Fluid fTokens and standalone DEX swaps, so matching
        unconditionally would drag unrelated transactions into Fluid post-decoding.
        """
        if len(context.tx_log.topics) == 0 or context.tx_log.topics[0] != LIQUIDITY_LOG_OPERATE:
            return DEFAULT_EVM_DECODING_OUTPUT

        if any(
            len(tx_log.topics) != 0 and
            tx_log.topics[0] in (VAULT_LOG_OPERATE, VAULT_LOG_LIQUIDATE)
            for tx_log in context.all_logs
        ):
            return EvmDecodingOutput(matched_counterparty=CPT_FLUID)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_vault_factory_log(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode position NFT mints and secondary transfers from FluidVaultFactory."""
        if len(context.tx_log.topics) == 0:
            return DEFAULT_EVM_DECODING_OUTPUT

        if context.tx_log.topics[0] == NEW_POSITION_MINTED:
            return EvmDecodingOutput(matched_counterparty=CPT_FLUID)

        if (
            context.tx_log.topics[0] != ERC20_OR_ERC721_TRANSFER or
            len(context.tx_log.topics) != 4
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        from_addr = bytes_to_address(context.tx_log.topics[1])
        to_addr = bytes_to_address(context.tx_log.topics[2])
        nft_id = int.from_bytes(context.tx_log.topics[3])
        if not self.base.any_tracked((from_addr, to_addr)):
            return EvmDecodingOutput(matched_counterparty=CPT_FLUID)

        nft_token = get_or_create_evm_token(
            userdb=self.base.database,
            evm_address=FLUID_VAULT_FACTORY,
            chain_id=self.node_inquirer.chain_id,
            token_kind=TokenKind.ERC721,
            symbol=f'fVLT-{nft_id}',
            name=f'Fluid Vault #{nft_id}',
            decimals=0,
            collectible_id=str(nft_id),
            protocol=CPT_FLUID,
            encounter=TokenEncounterInfo(tx_ref=context.transaction.tx_hash),
        )
        mint_vault, mint_user = next((
            (bytes_to_address(tx_log.topics[1]), bytes_to_address(tx_log.topics[2]))
            for tx_log in context.all_logs
            if (
                tx_log.address == FLUID_VAULT_FACTORY and
                len(tx_log.topics) == 4 and
                tx_log.topics[0] == NEW_POSITION_MINTED and
                int.from_bytes(tx_log.topics[3]) == nft_id
            )
        ), (None, None))

        if (
            self.base.is_tracked(to_addr) and
            not self.base.is_tracked(from_addr) and
            from_addr in (ZERO_ADDRESS, mint_user)
        ):
            event = self.base.make_event_from_transaction(
                transaction=context.transaction,
                tx_log=context.tx_log,
                event_type=HistoryEventType.MINT,
                event_subtype=HistoryEventSubType.NFT,
                asset=nft_token,
                amount=ONE,
                location_label=to_addr,
                notes=f'Create Fluid vault position {nft_id}',
                counterparty=CPT_FLUID,
                address=mint_vault or FLUID_VAULT_FACTORY,
            )
            return EvmDecodingOutput(events=[event], matched_counterparty=CPT_FLUID)

        if (direction_result := self.base.decode_direction(
            from_address=from_addr,
            to_address=to_addr,
        )) is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        event_type, event_subtype, location_label, address, _counterparty, _verb = direction_result
        if event_type == HistoryEventType.RECEIVE:
            notes = f'Receive Fluid vault position {nft_id} from {from_addr}'
        elif event_type == HistoryEventType.SPEND:
            notes = f'Send Fluid vault position {nft_id} to {to_addr}'
        else:
            notes = f'Transfer Fluid vault position {nft_id} from {from_addr} to {to_addr}'

        event = self.base.make_event_from_transaction(
            transaction=context.transaction,
            tx_log=context.tx_log,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=nft_token,
            amount=ONE,
            location_label=location_label,
            notes=notes,
            counterparty=CPT_FLUID,
            address=address,
        )
        return EvmDecodingOutput(events=[event], matched_counterparty=CPT_FLUID)

    def _resolve_normal_leg(
            self,
            all_logs: list[EvmTxReceiptLog],
            vault_log_pos: int,
            vault_addr: ChecksumEvmAddress,
            is_collateral: bool,
            expected_sign: int,
            used_liq_legs: set[tuple[int, bool]],
    ) -> list[tuple[CryptoAsset | EvmToken, FVal]] | None:
        """Resolve a non-smart vault leg from its preceding FluidLiquidity.LogOperate event."""
        word_offset = 0 if is_collateral else 32
        for pos in range(vault_log_pos - 1, -1, -1):
            candidate = all_logs[pos]
            if (
                candidate.address == vault_addr and
                len(candidate.topics) != 0 and
                candidate.topics[0] in (VAULT_LOG_OPERATE, VAULT_LOG_LIQUIDATE)
            ):
                break

            if (
                candidate.address != FLUID_LIQUIDITY or
                len(candidate.topics) < 3 or
                candidate.topics[0] != LIQUIDITY_LOG_OPERATE or
                len(candidate.data) < 64 or
                (candidate.log_index, is_collateral) in used_liq_legs or
                bytes_to_address(candidate.topics[1]) != vault_addr
            ):
                continue

            raw_amt = int.from_bytes(candidate.data[word_offset:word_offset + 32], signed=True)
            if raw_amt == 0 or (raw_amt > 0) != (expected_sign > 0):
                continue

            used_liq_legs.add((candidate.log_index, is_collateral))
            if (asset := self._resolve_asset(bytes_to_address(candidate.topics[2]))) is None:
                return []
            return [(asset, asset_normalized_value(amount=abs(raw_amt), asset=asset))]

        return None

    def _resolve_smart_leg(
            self,
            all_logs: list[EvmTxReceiptLog],
            vault_log_pos: int,
            vault_addr: ChecksumEvmAddress,
            shares_abs: int,
            is_collateral: bool,
            expected_sign: int,
            used_dex_logs: set[int],
    ) -> list[tuple[CryptoAsset | EvmToken, FVal]]:
        """Resolve a smart collateral / smart debt leg via constantsView() + FluidDexT1 event."""
        if (constants := self._get_vault_constants(vault_addr)) is None:
            return []

        if is_collateral:
            dex_addr, tokens = constants.supply_address, constants.col_tokens
            allowed_topics = (
                DEX_COL_DEPOSIT_TOPICS if expected_sign > 0 else DEX_COL_WITHDRAW_TOPICS
            )
            shares_last_topics = DEX_SHARES_LAST_COL_TOPICS
            shares_first_topics = DEX_SHARES_FIRST_COL_TOPICS
        else:
            dex_addr, tokens = constants.borrow_address, constants.debt_tokens
            allowed_topics = (
                DEX_DEBT_BORROW_TOPICS if expected_sign > 0 else DEX_DEBT_PAYBACK_TOPICS
            )
            shares_last_topics = DEX_SHARES_LAST_DEBT_TOPICS
            shares_first_topics = DEX_SHARES_FIRST_DEBT_TOPICS

        # Withdraw/payback operatePerfect emits its DEX event right after VAULT_LOG_OPERATE, while
        # standard operate emits it before; check both neighbors nearest to vault_log_pos.
        for pos in (*range(vault_log_pos - 1, -1, -1), *range(vault_log_pos + 1, len(all_logs))):
            candidate = all_logs[pos]
            if (
                candidate.address != dex_addr or
                len(candidate.topics) == 0 or
                candidate.log_index in used_dex_logs or
                len(candidate.data) < 96 or
                (topic0 := candidate.topics[0]) not in allowed_topics
            ):
                continue

            if topic0 in shares_last_topics:
                amt0 = int.from_bytes(candidate.data[0:32])
                amt1 = int.from_bytes(candidate.data[32:64])
                shares = int.from_bytes(candidate.data[64:96])
            elif topic0 in shares_first_topics:
                shares = int.from_bytes(candidate.data[0:32])
                amt0 = int.from_bytes(candidate.data[32:64])
                amt1 = int.from_bytes(candidate.data[64:96])
            else:
                continue

            if shares != shares_abs:
                continue

            used_dex_logs.add(candidate.log_index)
            resolved: list[tuple[CryptoAsset | EvmToken, FVal]] = []
            for token_addr, raw_amt in zip(tokens, (amt0, amt1), strict=True):
                if raw_amt != 0 and (asset := self._resolve_asset(token_addr)) is not None:
                    resolved.append((asset, asset_normalized_value(amount=raw_amt, asset=asset)))
            return resolved

        return []

    def _resolve_vault_leg(
            self,
            all_logs: list[EvmTxReceiptLog],
            vault_log_pos: int,
            vault_addr: ChecksumEvmAddress,
            raw_or_shares_amt: int,
            is_collateral: bool,
            expected_sign: int,
            used_liq_legs: set[tuple[int, bool]],
            used_dex_logs: set[int],
    ) -> list[tuple[CryptoAsset | EvmToken, FVal]]:
        if (normal_leg := self._resolve_normal_leg(
            all_logs=all_logs,
            vault_log_pos=vault_log_pos,
            vault_addr=vault_addr,
            is_collateral=is_collateral,
            expected_sign=expected_sign,
            used_liq_legs=used_liq_legs,
        )) is not None:
            return normal_leg

        return self._resolve_smart_leg(
            all_logs=all_logs,
            vault_log_pos=vault_log_pos,
            vault_addr=vault_addr,
            shares_abs=abs(raw_or_shares_amt),
            is_collateral=is_collateral,
            expected_sign=expected_sign,
            used_dex_logs=used_dex_logs,
        )

    def _reconcile_transfer(
            self,
            decoded_events: list[EvmEvent],
            from_event_type: HistoryEventType,
            asset: CryptoAsset | EvmToken,
            amount: FVal,
            allowed_addresses: set[ChecksumEvmAddress],
            to_event_type: HistoryEventType,
            to_event_subtype: HistoryEventSubType,
            address: ChecksumEvmAddress | None,
            notes_template: str,
            allow_native_refund: bool = False,
            location_label: ChecksumEvmAddress | None = None,
    ) -> EvmEvent | None:
        candidate = next((
            event for event in decoded_events
            if (
                event.event_type == from_event_type and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == asset and
                event.amount == amount and
                event.address in allowed_addresses and
                (location_label is None or event.location_label == location_label)
            )
        ), None)

        if (
            candidate is None and
            allow_native_refund and
            from_event_type == HistoryEventType.SPEND and
            asset == self.node_inquirer.native_token
        ):
            for spend_event in decoded_events:
                if (
                    spend_event.event_type != HistoryEventType.SPEND or
                    spend_event.event_subtype != HistoryEventSubType.NONE or
                    spend_event.asset != asset or
                    spend_event.address not in allowed_addresses or
                    spend_event.amount <= amount or
                    (location_label is not None and spend_event.location_label != location_label)
                ):
                    continue

                refund_event = next((
                    event for event in decoded_events
                    if (
                        event.event_type == HistoryEventType.RECEIVE and
                        event.event_subtype == HistoryEventSubType.NONE and
                        event.asset == asset and
                        event.location_label == spend_event.location_label and
                        event.address in allowed_addresses and
                        spend_event.amount - event.amount == amount
                    )
                ), None)
                if refund_event is not None:
                    spend_event.amount = amount
                    decoded_events.remove(refund_event)
                    candidate = spend_event
                    break

        if candidate is None:
            return None

        symbol = candidate.asset.resolve_to_asset_with_symbol().symbol
        candidate.event_type = to_event_type
        candidate.event_subtype = to_event_subtype
        candidate.counterparty = CPT_FLUID
        if address is not None:
            candidate.address = address
        candidate.notes = notes_template.format(amount=candidate.amount, symbol=symbol)
        return candidate

    def _apply_position_leg(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            asset: CryptoAsset | EvmToken,
            amount: FVal,
            allowed_addresses: set[ChecksumEvmAddress],
            is_collateral: bool,
            is_increase: bool,
            vault_addr: ChecksumEvmAddress,
            position_owner: ChecksumEvmAddress,
            nft_id: int,
    ) -> None:
        """Book one vault leg on the position owner.

        @remarks
        The owner's own matching wallet transfer becomes the protocol event. Deposits and
        repayments are permissionless, so another tracked account may pay them: that payer's
        spend becomes a transfer to the owner, followed by a synthetic protocol event of the
        owner, so the value leaves the combined portfolio's wallets only once. Legs settled
        entirely between Fluid contracts (e.g. flash leverage) also get a synthetic event.
        """
        spec = _OPERATE_LEG_CONFIG[is_collateral, is_increase]
        from_type, to_type, to_subtype, notes_template = spec
        allow_native_refund = not is_collateral and not is_increase
        if self._reconcile_transfer(
            decoded_events=decoded_events,
            from_event_type=from_type,
            asset=asset,
            amount=amount,
            allowed_addresses=allowed_addresses,
            to_event_type=to_type,
            to_event_subtype=to_subtype,
            address=vault_addr,
            notes_template=notes_template,
            allow_native_refund=allow_native_refund,
            location_label=position_owner,
        ) is not None:
            return

        if from_type == HistoryEventType.SPEND:
            self._reconcile_transfer(
                decoded_events=decoded_events,
                from_event_type=HistoryEventType.SPEND,
                asset=asset,
                amount=amount,
                allowed_addresses=allowed_addresses,
                to_event_type=HistoryEventType.TRANSFER,
                to_event_subtype=HistoryEventSubType.NONE,
                address=position_owner,
                notes_template=(
                    f'Transfer {{amount}} {{symbol}} to {position_owner} '
                    f'for Fluid vault position {nft_id}'
                ),
                allow_native_refund=allow_native_refund,
            )

        decoded_events.append(self.base.make_event_next_index(
            tx_ref=transaction.tx_hash,
            timestamp=transaction.timestamp,
            event_type=to_type,
            event_subtype=to_subtype,
            asset=asset,
            amount=amount,
            location_label=position_owner,
            notes=notes_template.format(
                amount=amount,
                symbol=asset.resolve_to_asset_with_symbol().symbol,
            ),
            counterparty=CPT_FLUID,
            address=vault_addr,
        ))

    def _resolve_position_owner(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            nft_owners: dict[int, ChecksumEvmAddress],
            nft_id: int,
            operate_user: ChecksumEvmAddress,
            has_owner_only_leg: bool,
    ) -> ChecksumEvmAddress | None:
        """Return the tracked owner of the operated position, or None if it is not proven.

        @remarks
        Fluid checks `ownerOf(nftId) == msg.sender` only to withdraw collateral or borrow, so
        for those the caller is the owner. Deposits and repayments are permissionless and need
        ownership proven by the NFT transfers of this transaction or by previously decoded
        position history; the paying caller says nothing about who owns the position.
        """
        has_third_party_mint = any(
            event.event_type == HistoryEventType.RECEIVE and
            event.address == ZERO_ADDRESS and
            event.asset != self.node_inquirer.native_token and
            event.counterparty != CPT_FLUID
            for event in decoded_events
        )
        in_tx_owner = nft_owners.get(nft_id)
        if in_tx_owner is not None and self.base.is_tracked(in_tx_owner):
            return in_tx_owner

        if has_owner_only_leg:
            if self.base.is_tracked(operate_user):
                return operate_user
            if self.base.is_tracked(transaction.from_address) and not has_third_party_mint:
                return transaction.from_address
            return None

        if in_tx_owner is None and (
            self.base.is_tracked(operate_user) or
            (self.base.is_tracked(transaction.from_address) and not has_third_party_mint)
        ):
            return self._get_prior_nft_owner(nft_id=nft_id, transaction=transaction)

        return None

    def _process_vault_operate(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            vault_log_pos: int,
            all_logs: list[EvmTxReceiptLog],
            decoded_events: list[EvmEvent],
            nft_owners: dict[int, ChecksumEvmAddress],
            used_liq_legs: set[tuple[int, bool]],
            used_dex_logs: set[int],
    ) -> None:
        vault_addr = tx_log.address
        operate_user = bytes_to_address(tx_log.data[0:32])
        nft_id = int.from_bytes(tx_log.data[32:64])
        col_amt = int.from_bytes(tx_log.data[64:96], signed=True)
        debt_amt = int.from_bytes(tx_log.data[96:128], signed=True)
        to_addr = bytes_to_address(tx_log.data[128:160])
        position_owner = self._resolve_position_owner(
            transaction=transaction,
            decoded_events=decoded_events,
            nft_owners=nft_owners,
            nft_id=nft_id,
            operate_user=operate_user,
            has_owner_only_leg=col_amt < 0 or debt_amt > 0,
        )
        if position_owner is None and not self.base.is_tracked(to_addr):
            return

        allowed_addresses = {FLUID_LIQUIDITY, vault_addr, operate_user}
        legs = (
            ((False, debt_amt), (True, col_amt))
            if debt_amt > 0 else
            ((True, col_amt), (False, debt_amt))
        )
        for is_collateral, raw_amt in legs:
            pays_out_to_receiver = is_collateral != (raw_amt > 0)
            if raw_amt == 0 or (position_owner is None and not pays_out_to_receiver):
                continue

            for asset, amount in self._resolve_vault_leg(
                all_logs=all_logs,
                vault_log_pos=vault_log_pos,
                vault_addr=vault_addr,
                raw_or_shares_amt=raw_amt,
                is_collateral=is_collateral,
                expected_sign=1 if raw_amt > 0 else -1,
                used_liq_legs=used_liq_legs,
                used_dex_logs=used_dex_logs,
            ):
                if position_owner is not None:
                    self._apply_position_leg(
                        transaction=transaction,
                        decoded_events=decoded_events,
                        asset=asset,
                        amount=amount,
                        allowed_addresses=allowed_addresses,
                        is_collateral=is_collateral,
                        is_increase=raw_amt > 0,
                        vault_addr=vault_addr,
                        position_owner=position_owner,
                        nft_id=nft_id,
                    )
                    continue

                action = 'withdrawal' if is_collateral else 'borrow'
                self._reconcile_transfer(
                    decoded_events=decoded_events,
                    from_event_type=HistoryEventType.RECEIVE,
                    asset=asset,
                    amount=amount,
                    allowed_addresses=allowed_addresses,
                    to_event_type=HistoryEventType.RECEIVE,
                    to_event_subtype=HistoryEventSubType.NONE,
                    address=None,
                    notes_template=(
                        f'Receive {{amount}} {{symbol}} from a Fluid {action} by {operate_user}'
                    ),
                    location_label=to_addr,
                )

    def _process_vault_liquidate(
            self,
            tx_log: EvmTxReceiptLog,
            vault_log_pos: int,
            all_logs: list[EvmTxReceiptLog],
            decoded_events: list[EvmEvent],
            used_liq_legs: set[tuple[int, bool]],
            used_dex_logs: set[int],
    ) -> None:
        vault_addr = tx_log.address
        liquidator = bytes_to_address(tx_log.data[0:32])
        col_raw = int.from_bytes(tx_log.data[32:64])
        debt_raw = int.from_bytes(tx_log.data[64:96])
        to_addr = bytes_to_address(tx_log.data[96:128])
        if not self.base.any_tracked((liquidator, to_addr)):
            return

        allowed_addresses = {FLUID_LIQUIDITY, vault_addr, liquidator}
        spend_events: list[EvmEvent] = []
        receive_events: list[EvmEvent] = []
        for is_collateral, raw_amt, event_type, notes_template, target_list in (
            (
                False,
                debt_raw,
                HistoryEventType.SPEND,
                'Pay {amount} {symbol} to liquidate Fluid vault',
                spend_events,
            ),
            (
                True,
                col_raw,
                HistoryEventType.RECEIVE,
                'Receive {amount} {symbol} from Fluid vault liquidation',
                receive_events,
            ),
        ):
            if raw_amt == 0:
                continue

            for asset, amount in self._resolve_vault_leg(
                all_logs=all_logs,
                vault_log_pos=vault_log_pos,
                vault_addr=vault_addr,
                raw_or_shares_amt=raw_amt,
                is_collateral=is_collateral,
                expected_sign=-1,
                used_liq_legs=used_liq_legs,
                used_dex_logs=used_dex_logs,
            ):
                if (event := self._reconcile_transfer(
                    decoded_events=decoded_events,
                    from_event_type=event_type,
                    asset=asset,
                    amount=amount,
                    allowed_addresses=allowed_addresses,
                    to_event_type=event_type,
                    to_event_subtype=HistoryEventSubType.NONE,
                    address=vault_addr,
                    notes_template=notes_template,
                )) is not None:
                    target_list.append(event)

        if spend_events and receive_events:
            for event in spend_events:
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.SPEND
            for event in receive_events:
                event.event_type = HistoryEventType.TRADE
                event.event_subtype = HistoryEventSubType.RECEIVE
            maybe_reshuffle_events(
                ordered_events=[*spend_events, *receive_events],
                events_list=decoded_events,
            )

    def _decode_vault_events(
            self,
            transaction: EvmTransaction,
            decoded_events: list[EvmEvent],
            all_logs: list[EvmTxReceiptLog],
    ) -> list[EvmEvent]:
        """Post-decoding hook transforming token/ETH transfers into Fluid vault events."""
        nft_owners: dict[int, ChecksumEvmAddress] = {}  # holder of each NFT moved in this tx
        for tx_log in all_logs:
            if (
                tx_log.address == FLUID_VAULT_FACTORY and
                len(tx_log.topics) == 4 and
                tx_log.topics[0] == ERC20_OR_ERC721_TRANSFER
            ):
                nft_owners[int.from_bytes(tx_log.topics[3])] = bytes_to_address(tx_log.topics[2])

        used_liq_legs: set[tuple[int, bool]] = set()
        used_dex_logs: set[int] = set()

        for pos, tx_log in enumerate(all_logs):
            if len(tx_log.topics) == 0:
                continue

            topic0 = tx_log.topics[0]
            if (
                topic0 == VAULT_LOG_OPERATE and
                len(tx_log.data) == 160 and
                self._is_fluid_vault(tx_log.address)
            ):
                self._process_vault_operate(
                    transaction=transaction,
                    tx_log=tx_log,
                    vault_log_pos=pos,
                    all_logs=all_logs,
                    decoded_events=decoded_events,
                    nft_owners=nft_owners,
                    used_liq_legs=used_liq_legs,
                    used_dex_logs=used_dex_logs,
                )
            elif (
                topic0 == VAULT_LOG_LIQUIDATE and
                len(tx_log.data) == 128 and
                self._is_fluid_vault(tx_log.address)
            ):
                self._process_vault_liquidate(
                    tx_log=tx_log,
                    vault_log_pos=pos,
                    all_logs=all_logs,
                    decoded_events=decoded_events,
                    used_liq_legs=used_liq_legs,
                    used_dex_logs=used_dex_logs,
                )

        return decoded_events

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            FLUID_LIQUIDITY: (self._decode_liquidity_log,),
            FLUID_VAULT_FACTORY: (self._decode_vault_factory_log,),
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {FLUID_VAULT_FACTORY: CPT_FLUID}

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Any]]]:
        return {CPT_FLUID: [(0, self._decode_vault_events)]}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (FLUID_CPT_DETAILS,)
