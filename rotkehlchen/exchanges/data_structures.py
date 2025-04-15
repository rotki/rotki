import datetime
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.crypto import sha3
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fee,
    deserialize_fval,
    deserialize_optional,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    Fee,
    Location,
    Price,
    Timestamp,
    TradeID,
    TradeType,
)

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.fval import FVal


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def hash_id(hashable: str) -> TradeID:
    id_bytes = sha3(hashable.encode())
    return TradeID(id_bytes.hex())


TradeDBTuple = tuple[
    str,  # id
    int,  # time
    str,  # location
    str,  # base_asset
    str,  # quote_asset
    str,  # type
    str,  # amount
    str,  # rate
    str,  # fee
    str,  # fee_currency
    str,  # link
    str,  # notes
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Trade(AccountingEventMixin):
    """Represents a Trade

    Pairs are represented as BASE_QUOTE. When a buy is made, then the BASE
    asset is bought with QUOTE asset. When a sell is made then the BASE
    asset is sold for QUOTE asset.

    Exchanges don't use the same part of the pair to denote the same thing. For
    example in Poloniex the pair is called BTC_ETH and you buy and sell ETH for
    BTC. In Kraken XXBTZEUR translates to BTC_EUR. This means we buy BTC for EUR
    or we sell BTC for EUR.

    All trades have a unique ID which is generated from some of the attributes.
    For details check identifier() function
    This unique ID is not stored in the structure since it depends on some of
    its attributes.
    """
    timestamp: Timestamp
    location: Location
    base_asset: Asset
    quote_asset: Asset
    trade_type: TradeType
    # The amount represents the amount bought if it's a buy or the amount
    # sold if it's a sell. Should NOT include fees
    amount: 'FVal'
    rate: Price
    fee: Fee | None = None
    fee_currency: Asset | None = None
    # For external trades this is optional and is a link to the trade in an explorer
    # For exchange trades this should be the exchange unique trade identifier
    # For trades imported from third parties we should generate a unique id for this.
    # If trades are both imported from third parties like cointracking.info and from
    # the exchanges themselves then there is no way to avoid duplicates.
    link: str | None = None
    notes: str | None = None

    @property
    def identifier(self) -> TradeID:
        """
        Formulates a unique identifier for the trade to become the DB primary key
        """
        string = (
            str(self.location) +
            str(self.timestamp) +
            str(self.trade_type) +
            self.base_asset.identifier +
            self.quote_asset.identifier +
            str(self.amount) +
            str(self.rate) +
            (self.link or '')
        )
        return TradeID(hash_id(string))

    def serialize(self) -> dict[str, Any]:
        """Serialize the trade into a dict"""
        return {
            'timestamp': self.timestamp,
            'location': str(self.location),
            'base_asset': self.base_asset.identifier,
            'quote_asset': self.quote_asset.identifier,
            'trade_type': str(self.trade_type),
            'amount': str(self.amount),
            'rate': str(self.rate),
            'fee': str(self.fee) if self.fee else None,
            'fee_currency': self.fee_currency.identifier if self.fee_currency else None,
            'link': self.link,
            'notes': self.notes,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> 'Trade':
        """
        Deserializes a trade dict to a Trade object.
        May raise:
            - UnknownAsset
            - DeserializationError
        """
        return deserialize_trade(data)

    def __str__(self) -> str:
        return (
            f'trade at {self.location!s} location and date '
            f'{datetime.datetime.fromtimestamp(self.timestamp, tz=datetime.UTC)} '
            f'of type {self.trade_type!s} with base asset: {self.base_asset.symbol_or_name()} '
            f'and quote asset: {self.quote_asset.symbol_or_name()}'
        )

    @classmethod
    def deserialize_from_db(cls, entry: TradeDBTuple) -> 'Trade':
        """
        May raise:
        - DeserializationError
        - UnknownAsset
        """
        return Trade(
            timestamp=deserialize_timestamp(entry[1]),
            location=Location.deserialize_from_db(entry[2]),
            base_asset=Asset(entry[3]).check_existence(),
            quote_asset=Asset(entry[4]).check_existence(),
            trade_type=TradeType.deserialize_from_db(entry[5]),
            amount=deserialize_fval(entry[6]),
            rate=deserialize_price(entry[7]),
            fee=deserialize_optional(entry[8], deserialize_fee),
            fee_currency=deserialize_optional(entry[9], Asset),
            link=entry[10],
            notes=entry[11],
        )

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.timestamp

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.TRADE

    def get_identifier(self) -> str:
        return self.identifier

    def get_assets(self) -> list[Asset]:
        return [self.base_asset, self.quote_asset]

    def should_ignore(self, ignored_ids_mapping: dict[ActionType, set[str]]) -> bool:
        return self.identifier in ignored_ids_mapping.get(ActionType.TRADE, set())

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        if self.rate == ZERO:
            return 1  # nothing to do for a trade with zero rate

        if self.trade_type == TradeType.BUY:
            asset_in = self.base_asset
            amount_in = self.amount
            asset_out = self.quote_asset
            amount_out = self.rate * self.amount
            notes = f'Buy {asset_in} with {asset_out}.'
        elif self.trade_type == TradeType.SELL:
            asset_out = self.base_asset
            amount_out = self.amount
            asset_in = self.quote_asset
            amount_in = self.rate * self.amount
            notes = f'Sell {asset_out} for {asset_in}.'
        else:  # settlement buy/sell only in poloniex. Should properly process when margin
            return 1  # trades are implemented

        group_id = self.identifier
        taxable = asset_in.is_fiat() or accounting.settings.include_crypto2crypto

        should_calculate_fee = self.fee is not None and self.fee_currency is not None and self.fee != ZERO  # noqa: E501

        fee_info_for_cost_basis = None
        if should_calculate_fee and accounting.settings.include_fees_in_cost_basis is True:
            fee_info_for_cost_basis = (self.fee, self.fee_currency)

        prices = accounting.get_prices_for_swap(
            timestamp=self.timestamp,
            amount_in=amount_in,
            asset_in=asset_in,
            amount_out=amount_out,
            asset_out=asset_out,
            fee_info=fee_info_for_cost_basis,  # type: ignore[arg-type]  # mypy doesn't see that `should_calculate_fee` condition makes sure that the values are not None.
        )
        if prices is None:
            log.debug(f'Skipping {self} at accounting due to inability to find a price')
            return 1

        _, trade_taxable_amount = accounting.add_out_event(
            originating_event_id=None,  # not a history event, but a Trade
            event_type=AccountingEventType.TRADE,
            notes=notes + ' Amount out',
            location=self.location,
            timestamp=self.timestamp,
            asset=asset_out,
            amount=amount_out,
            taxable=taxable,
            given_price=prices[0],
            count_entire_amount_spend=False,
            extra_data={'group_id': group_id},
        )
        accounting.add_in_event(
            event_type=AccountingEventType.TRADE,
            notes=notes + ' Amount in',
            location=self.location,
            timestamp=self.timestamp,
            asset=asset_in,
            amount=amount_in,
            taxable=False,  # For a trade the outgoing part (sell) determined profit
            given_price=prices[1],
            extra_data={'group_id': group_id},
        )

        if should_calculate_fee:  # include fee as a standalone event
            fee_price = None
            if self.fee_currency == accounting.profit_currency:
                fee_price = Price(ONE)
            elif self.fee_currency == asset_in:
                fee_price = prices[1]
            elif self.fee_currency == asset_out:
                fee_price = prices[0]

            if accounting.settings.include_fees_in_cost_basis:
                # If fee is included in cost basis, we just reduce the amount of fee asset owned
                fee_taxable = False
                fee_taxable_amount_ratio = ONE
            else:
                # Otherwise we make it a normal spend event
                fee_taxable = True
                fee_taxable_amount_ratio = trade_taxable_amount / amount_out

            accounting.add_out_event(
                originating_event_id=None,  # not a history event, but a Trade
                event_type=AccountingEventType.FEE,
                notes=notes + 'Fee',
                location=self.location,
                timestamp=self.timestamp,
                asset=self.fee_currency,  # type: ignore[arg-type]  # mypy doesn't see that `calculate_fee` condition makes sure that the values are not None.
                amount=self.fee,  # type: ignore[arg-type]  # mypy doesn't see that `calculate_fee` condition makes sure that the values are not None.
                taxable=fee_taxable,
                given_price=fee_price,
                # By setting the taxable amount ratio we determine how much of the fee
                # spending should be a taxable spend and how much free.
                taxable_amount_ratio=fee_taxable_amount_ratio,
                count_cost_basis_pnl=True,
                count_entire_amount_spend=True,
                extra_data={'group_id': group_id},
            )

        return 1


MarginPositionDBTuple = tuple[
    str,  # id
    str,  # location
    int,  # open_time
    int,  # close_time
    str,  # profit_loss
    str,  # pl_currency
    str,  # fee
    str,  # fee_currency
    str,  # link
    str,  # notes
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class MarginPosition(AccountingEventMixin):
    """We only support margin positions on poloniex and bitmex at the moment"""
    location: Location
    open_time: Timestamp | None
    close_time: Timestamp
    # Profit loss in pl_currency (does not include fees)
    profit_loss: 'FVal'
    # The asset gained or lost
    pl_currency: Asset
    # Amount of fees paid
    fee: Fee
    # The asset in which fees were paid
    fee_currency: Asset
    # For exchange margins this should be the exchange unique identifier
    # For margins imported from third parties we should generate a unique id for this.
    # If margins are both imported from third parties like cointracking.info and from
    # the exchanges themselves then there is no way to avoid duplicates.
    link: str
    notes: str = ''

    @property
    def identifier(self) -> str:
        """Formulates a unique identifier for the margin position to become the DB primary key

        We are not using self.link (unique exchange identifier) as part of the ID
        for exchange margins since it may not be available at import of data from
        third party sources such as cointracking.info

        Unfortunately this makes the Trade identifier pseudo unique and means
        we can't have same trades with all of the following attributes.
        """
        open_time = 'None' if self.open_time is None else str(self.open_time)
        string = (
            str(self.location) +
            open_time +
            str(self.close_time) +
            self.pl_currency.identifier +
            self.fee_currency.identifier +
            self.link
        )
        return hash_id(string)

    def serialize(self) -> dict[str, Any]:
        """Serialize the margin position into a dict."""
        return {
            'location': self.location.serialize(),
            'open_time': self.open_time,
            'close_time': self.close_time,
            'profit_loss': str(self.profit_loss),
            'pl_currency': self.pl_currency.identifier,
            'fee': str(self.fee),
            'link': self.link,
            'notes': self.notes,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> 'MarginPosition':
        """Deserialize a dict margin position to a MarginPosition object.
        May raise:
            - DeserializationError
            - KeyError
            - UnknownAsset
        """
        return cls(
            location=Location.deserialize(data['location']),
            open_time=deserialize_timestamp(data['open_time']),
            close_time=deserialize_timestamp(data['close_time']),
            profit_loss=deserialize_fval(data['profit_loss']),
            pl_currency=Asset(data['pl_currency']).check_existence(),
            fee=deserialize_fee(data['fee']),
            fee_currency=Asset(data['fee_currency']).check_existence(),
            link=str(data['link']),
            notes=str(data['notes']),
        )

    @classmethod
    def deserialize_from_db(cls, entry: MarginPositionDBTuple) -> 'MarginPosition':
        """May raise:
            - DeserializationError
            - UnknownAsset
        """
        if entry[2] == 0:
            open_time = None
        else:
            open_time = deserialize_timestamp(entry[2])
        return MarginPosition(
            location=Location.deserialize_from_db(entry[1]),
            open_time=open_time,
            close_time=deserialize_timestamp(entry[3]),
            profit_loss=deserialize_fval(entry[4]),
            pl_currency=Asset(entry[5]).check_existence(),
            fee=deserialize_fee(entry[6]),
            fee_currency=Asset(entry[7]).check_existence(),
            link=entry[8],
            notes=entry[9],
        )

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.close_time

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.MARGIN_POSITION

    def get_identifier(self) -> str:
        return self.identifier

    def get_assets(self) -> list[Asset]:
        return [self.pl_currency]

    def should_ignore(self, ignored_ids_mapping: dict[ActionType, set[str]]) -> bool:
        return False

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        if self.profit_loss >= ZERO:
            amount = self.profit_loss
            direction = EventDirection.IN
        else:
            direction = EventDirection.OUT
            amount = -self.profit_loss

        accounting.add_asset_change_event(
            direction=direction,
            event_type=AccountingEventType.MARGIN_POSITION,
            notes='Margin position. PnL',
            location=self.location,
            timestamp=self.close_time,
            asset=self.pl_currency,
            amount=amount,
            taxable=True,
        )
        if self.fee != ZERO:  # Fee is not included in the asset price here since it is not a swap/trade event.  # noqa: E501
            accounting.add_out_event(
                originating_event_id=None,  # not a history event, but a Trade
                event_type=AccountingEventType.FEE,
                notes='Margin position. Fee',
                location=self.location,
                timestamp=self.close_time,
                asset=self.fee_currency,
                amount=self.fee,
                taxable=True,
            )

        return 1


@dataclass(init=True, repr=True, eq=False, order=False, unsafe_hash=False, frozen=True)
class Loan(AccountingEventMixin):
    """We only support loans in poloniex at the moment"""
    location: Location
    open_time: Timestamp
    close_time: Timestamp
    currency: Asset
    fee: Fee
    earned: 'FVal'
    amount_lent: 'FVal'

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.close_time

    def serialize(self) -> dict[str, Any]:
        """Serialize the loan into a dict."""
        return {
            'location': self.location.serialize(),
            'open_time': self.open_time,
            'close_time': self.close_time,
            'currency': self.currency.identifier,
            'fee': str(self.fee),
            'earned': str(self.earned),
            'amount_lent': str(self.amount_lent),
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> 'Loan':
        """Deserialize a dict loan to a Loan object.
        May raise:
            - DeserializationError
            - KeyError
            - UnknownAsset
        """
        return cls(
            location=Location.deserialize(data['location']),
            open_time=deserialize_timestamp(data['open_time']),
            close_time=deserialize_timestamp(data['close_time']),
            currency=Asset(data['currency']).check_existence(),
            fee=deserialize_fee(data['fee']),
            earned=deserialize_fval(data['earned']),
            amount_lent=deserialize_fval(data['amount_lent']),
        )

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.LOAN

    def get_identifier(self) -> str:
        return 'loan_' + str(self.close_time)

    def should_ignore(self, ignored_ids_mapping: dict[ActionType, set[str]]) -> bool:
        return False

    def get_assets(self) -> list[Asset]:
        return [self.currency]

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        accounting.add_in_event(
            event_type=AccountingEventType.LOAN,
            notes='Loan',
            location=self.location,
            timestamp=self.close_time,
            asset=self.currency,
            amount=self.earned - self.fee,
            taxable=True,
        )
        return 1


def deserialize_trade(data: dict[str, Any]) -> Trade:
    """
    Takes a dict trade representation of our common trade format and serializes
    it into the Trade object

    May raise:
        - UnknownAsset: If the base, quote, fee asset string is not a known asset
        - DeserializationError: If any of the trade dict entries is not as expected
    """
    rate = deserialize_price(data['rate'])
    amount = deserialize_fval(data['amount'])
    trade_type = TradeType.deserialize(data['trade_type'])
    location = Location.deserialize(data['location'])

    trade_link = ''
    if 'link' in data:
        trade_link = data['link']
    trade_notes = ''
    if 'notes' in data:
        trade_notes = data['notes']

    return Trade(
        timestamp=data['timestamp'],
        location=location,
        base_asset=Asset(data['base_asset']).check_existence(),
        quote_asset=Asset(data['quote_asset']).check_existence(),
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=deserialize_optional(data['fee'], deserialize_fee),
        fee_currency=Asset(data['fee_currency']).check_existence() if data['fee_currency'] is not None else None,  # noqa: E501
        link=trade_link,
        notes=trade_notes,
    )


BINANCE_PAIR_DB_TUPLE = tuple[str, str, str, str]


class BinancePair(NamedTuple):
    """A binance pair. Contains the symbol in the Binance mode e.g. "ETHBTC" and
    the base and quote assets of that symbol as parsed from exchangeinfo endpoint
    result"""
    symbol: str
    base_asset: AssetWithOracles
    quote_asset: AssetWithOracles
    location: Location  # Should only be binance or binanceus

    def serialize_for_db(self) -> BINANCE_PAIR_DB_TUPLE:
        """Create tuple to be inserted in the database containing:
        - symbol for the pair. Example: ETHBTC
        - identifier of the base asset
        - identifier of the quote asset
        - the location, this is to differentiate binance from binanceus
        """
        return (
            self.symbol,
            self.base_asset.identifier,
            self.quote_asset.identifier,
            self.location.serialize_for_db(),
        )

    @classmethod
    def deserialize_from_db(cls, entry: BINANCE_PAIR_DB_TUPLE) -> 'BinancePair':
        """Create a BinancePair from data in the database. May raise:
        - DeserializationError
        - UnsupportedAsset
        - UnknownAsset
        """
        return BinancePair(
            symbol=entry[0],
            base_asset=asset_from_binance(entry[1]),
            quote_asset=asset_from_binance(entry[2]),
            location=Location.deserialize_from_db(entry[3]),
        )
