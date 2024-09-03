import logging
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Optional, Union

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import OUTGOING_EVENT_TYPES
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.assets.utils import TokenEncounterInfo
    from rotkehlchen.chain.evm.l2_with_l1_fees.node_inquirer import (
        DSProxyL2WithL1FeesInquirerWithCacheData,
    )
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer, EvmNodeInquirerWithDSProxy
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

from rotkehlchen.chain.ethereum.utils import asset_normalized_value, token_normalized_value
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTokenKind, EvmTransaction, EVMTxHash, Location
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int, ts_sec_to_ms

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BaseDecoderTools:
    """A class that keeps a common state and offers some common decoding functionality"""

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            is_non_conformant_erc721_fn: Callable[[ChecksumEvmAddress], bool],
            address_is_exchange_fn: Callable[[ChecksumEvmAddress], str | None],
    ) -> None:
        self.database = database
        self.evm_inquirer = evm_inquirer
        self.address_is_exchange = address_is_exchange_fn
        self.is_non_conformant_erc721 = is_non_conformant_erc721_fn
        with self.database.conn.read_ctx() as cursor:
            self.tracked_accounts = self.database.get_blockchain_accounts(cursor)
        self.sequence_counter = 0

    def reset_sequence_counter(self) -> None:
        self.sequence_counter = 0

    def get_next_sequence_counter(self) -> int:
        """Returns current counter and also increases it.
        Meant to be called for all transaction events that do not have a corresponding log index"""
        value = self.sequence_counter
        self.sequence_counter += 1
        return value

    def get_sequence_index(self, tx_log: EvmTxReceiptLog) -> int:
        """Get the value that should go for this event's sequence index

        This function exists to calculate the index bases on the pre-calculated
        sequence index and the event's log index"""
        return self.sequence_counter + tx_log.log_index

    def refresh_tracked_accounts(self, cursor: 'DBCursor') -> None:
        self.tracked_accounts = self.database.get_blockchain_accounts(cursor)

    def is_tracked(self, adddress: ChecksumEvmAddress) -> bool:
        return adddress in self.tracked_accounts.get(self.evm_inquirer.chain_id.to_blockchain())

    def any_tracked(self, addresses: Sequence[ChecksumEvmAddress]) -> bool:
        return set(addresses).isdisjoint(self.tracked_accounts.get(self.evm_inquirer.chain_id.to_blockchain())) is False  # noqa: E501

    def maybe_get_proxy_owner(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:  # pylint: disable=unused-argument
        """
        Checks whether given address is a proxy owned by any of the tracked accounts.
        If it is a proxy, it returns the owner of the proxy, otherwise `None`.
        """
        return None

    def get_address_or_proxy_owner(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:  # pylint: disable=unused-argument
        """If the address is a DS proxy return its owner, if not return address itself"""
        owner = self.maybe_get_proxy_owner(address)
        return owner or address

    def decode_direction(
            self,
            from_address: ChecksumEvmAddress,
            to_address: ChecksumEvmAddress | None,
    ) -> tuple[HistoryEventType, HistoryEventSubType, str | None, ChecksumEvmAddress, str, str] | None:  # noqa: E501
        """Depending on addresses, if they are tracked by the user or not, if they
        are an exchange address etc. determine the type of event to classify the transfer as.

        Returns event type, location label, address, counterparty and verb.
        address is the address on the opposite side of the event. counterparty is the exchange name
        if it is a deposit / withdrawal to / from an exchange.
        """
        tracked_from = from_address in self.tracked_accounts.get(self.evm_inquirer.chain_id.to_blockchain())  # noqa: E501
        tracked_to = to_address in self.tracked_accounts.get(self.evm_inquirer.chain_id.to_blockchain())  # noqa: E501
        if not tracked_from and not tracked_to:
            return None

        from_exchange = self.address_is_exchange(from_address)
        to_exchange = self.address_is_exchange(to_address) if to_address else None

        counterparty: str | None = None
        event_subtype = HistoryEventSubType.NONE
        if tracked_from and tracked_to:
            event_type = HistoryEventType.TRANSFER
            location_label = from_address
            address = to_address
            verb = 'Transfer'
        elif tracked_from:
            if to_exchange is not None:
                event_type = HistoryEventType.DEPOSIT
                verb = 'Deposit'
                counterparty = to_exchange
                event_subtype = HistoryEventSubType.DEPOSIT_ASSET
            else:
                event_type = HistoryEventType.SPEND
                verb = 'Send'

            address = to_address
            location_label = from_address
        else:  # can only be tracked_to
            if from_exchange:
                event_type = HistoryEventType.WITHDRAWAL
                verb = 'Withdraw'
                counterparty = from_exchange
                event_subtype = HistoryEventSubType.REMOVE_ASSET
            else:
                event_type = HistoryEventType.RECEIVE
                verb = 'Receive'

            address = from_address
            location_label = to_address  # type: ignore  # to_address can't be None here

        return event_type, event_subtype, location_label, address, counterparty, verb  # type: ignore

    def decode_erc20_721_transfer(
            self,
            token: EvmToken,
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,
    ) -> Optional['EvmEvent']:
        """
        Caller should know this is a transfer of either an ERC20 or an ERC721 token.
        Call this method to decode it.

        May raise:
        - DeserializationError
        - ConversionError
        """
        from_address = hex_or_bytes_to_address(tx_log.topics[1])
        to_address = hex_or_bytes_to_address(tx_log.topics[2])
        direction_result = self.decode_direction(
            from_address=from_address,
            to_address=to_address,
        )
        if direction_result is None:
            return None

        extra_data = None
        event_type, event_subtype, location_label, address, counterparty, verb = direction_result
        counterparty_or_address = counterparty or address
        amount_raw_or_token_id = hex_or_bytes_to_int(tx_log.data)
        if token.token_kind == EvmTokenKind.ERC20:
            amount = token_normalized_value(token_amount=amount_raw_or_token_id, token=token)
            if event_type in OUTGOING_EVENT_TYPES:
                notes = f'{verb} {amount} {token.symbol} from {location_label} to {counterparty_or_address}'  # noqa: E501
            else:
                notes = f'{verb} {amount} {token.symbol} from {counterparty_or_address} to {location_label}'  # noqa: E501
        elif token.token_kind == EvmTokenKind.ERC721:
            try:
                if self.is_non_conformant_erc721(token.evm_address):  # id is in the data
                    token_id = hex_or_bytes_to_int(tx_log.data[0:32])
                else:
                    token_id = hex_or_bytes_to_int(tx_log.topics[3])
            except IndexError as e:
                log.debug(
                    f'At decoding of token {token.evm_address} as ERC721 got '
                    f'insufficient number of topics: {tx_log.topics} and error: {e!s}',
                )
                return None

            amount = ONE
            name = 'ERC721 token' if token.name == '' else token.name
            extra_data = {'token_id': token_id, 'token_name': name}
            if event_type in {HistoryEventType.SPEND, HistoryEventType.TRANSFER}:
                notes = f'{verb} {name} with id {token_id} from {location_label} to {counterparty_or_address}'  # noqa: E501
            else:
                notes = f'{verb} {name} with id {token_id} from {counterparty_or_address} to {location_label}'  # noqa: E501
        else:
            return None  # unknown kind

        if amount == ZERO:
            return None  # Zero transfers are useless, so ignoring them

        return self.make_event(
            tx_hash=transaction.tx_hash,
            sequence_index=self.get_sequence_index(tx_log),
            timestamp=transaction.timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=token,
            balance=Balance(amount=amount),
            location_label=location_label,
            notes=notes,
            address=address,
            counterparty=counterparty,
            extra_data=extra_data,
        )

    def make_event(
            self,
            tx_hash: EVMTxHash,
            sequence_index: int,
            timestamp: Timestamp,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            balance: Balance,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            product: EvmProduct | None = None,
            address: ChecksumEvmAddress | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> 'EvmEvent':
        """A convenience function to create an EvmEvent depending on the
        decoder's chain id"""
        return EvmEvent(
            tx_hash=tx_hash,
            sequence_index=sequence_index,
            timestamp=ts_sec_to_ms(timestamp),
            location=Location.from_chain_id(self.evm_inquirer.chain_id),
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            balance=balance,
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            product=product,
            address=address,
            extra_data=extra_data,
        )

    def make_event_from_transaction(
            self,
            transaction: EvmTransaction,
            tx_log: EvmTxReceiptLog,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            balance: Balance,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            product: EvmProduct | None = None,
            address: ChecksumEvmAddress | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> 'EvmEvent':
        """Convenience function on top of make_event to use transaction and ReceiptLog"""
        return self.make_event(
            tx_hash=transaction.tx_hash,
            sequence_index=self.get_sequence_index(tx_log),
            timestamp=transaction.timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            balance=balance,
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            product=product,
            address=address,
            extra_data=extra_data,
        )

    def make_event_next_index(
            self,
            tx_hash: EVMTxHash,
            timestamp: Timestamp,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            asset: 'Asset',
            balance: Balance,
            location_label: str | None = None,
            notes: str | None = None,
            counterparty: str | None = None,
            product: EvmProduct | None = None,
            address: ChecksumEvmAddress | None = None,
            extra_data: dict[str, Any] | None = None,
    ) -> 'EvmEvent':
        """Convenience function on top of make_event to use next sequence index"""
        return self.make_event(
            tx_hash=tx_hash,
            sequence_index=self.get_next_sequence_counter(),
            timestamp=timestamp,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            balance=balance,
            location_label=location_label,
            notes=notes,
            counterparty=counterparty,
            product=product,
            address=address,
            extra_data=extra_data,
        )

    def get_or_create_evm_token(
            self,
            address: ChecksumEvmAddress,
            encounter: 'TokenEncounterInfo | None' = None,
    ) -> EvmToken:
        """A version of get_create_evm_token to be called from the decoders"""
        return get_or_create_evm_token(
            userdb=self.database,
            evm_address=address,
            chain_id=self.evm_inquirer.chain_id,
            evm_inquirer=self.evm_inquirer,
            encounter=encounter,
        )

    def get_or_create_evm_asset(self, address: ChecksumEvmAddress) -> CryptoAsset:
        """A version of get_create_evm_token to be called from the decoders

        Also checks for special cases like the special ETH (or MATIC etc)
        address used in some protocols
        """
        if address == ETH_SPECIAL_ADDRESS:
            return self.evm_inquirer.native_token
        return self.get_or_create_evm_token(address)

    def resolve_tokens_data(
            self,
            token_addresses: list['ChecksumEvmAddress'],
            token_amounts: list[int],
    ) -> dict[str, FVal]:
        """Returns the resolved evm tokens or native currency and their amounts"""
        resolved_result: dict[str, FVal] = {}
        for token_address, token_amount in zip(token_addresses, token_amounts, strict=True):
            if token_address == ZERO_ADDRESS:
                asset = self.evm_inquirer.native_token
            else:
                asset = get_or_create_evm_token(
                    userdb=self.database,
                    evm_inquirer=self.evm_inquirer,
                    evm_address=token_address,
                    chain_id=self.evm_inquirer.chain_id,
                    token_kind=EvmTokenKind.ERC20,
                )

            resolved_result[asset.identifier] = asset_normalized_value(amount=token_amount, asset=asset)  # noqa: E501

        return resolved_result


class BaseDecoderToolsWithDSProxy(BaseDecoderTools):
    """Like BaseDecoderTools but with DSProxy evm inquirers"""

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: Union['EvmNodeInquirerWithDSProxy', 'DSProxyL2WithL1FeesInquirerWithCacheData'],  # noqa: E501
            is_non_conformant_erc721_fn: Callable[[ChecksumEvmAddress], bool],
            address_is_exchange_fn: Callable[[ChecksumEvmAddress], str | None],
    ) -> None:
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            is_non_conformant_erc721_fn=is_non_conformant_erc721_fn,
            address_is_exchange_fn=address_is_exchange_fn,
        )
        self.evm_inquirer: EvmNodeInquirerWithDSProxy  # to specify the type

    def maybe_get_proxy_owner(self, address: ChecksumEvmAddress) -> ChecksumEvmAddress | None:
        """
        Checks whether given address is a proxy owned by any of the tracked accounts.
        If it is a proxy, it returns the owner of the proxy, otherwise `None`.
        """
        self.evm_inquirer.proxies_inquirer.get_accounts_having_proxy()  # calling to make sure that proxies are queried  # noqa: E501
        return self.evm_inquirer.proxies_inquirer.proxy_to_address.get(address)
