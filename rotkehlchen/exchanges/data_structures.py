import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, NamedTuple, Optional, Tuple

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.crypto import sha3
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_fval,
    deserialize_optional,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeID,
    TradePair,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def hash_id(hashable: str) -> TradeID:
    id_bytes = sha3(hashable.encode())
    return TradeID(id_bytes.hex())


AssetMovementDBTuple = Tuple[
    str,  # id
    str,  # location
    str,  # category
    str,  # address
    str,  # transaction_id
    int,  # time
    str,  # asset
    str,  # amount
    str,  # fee_asset
    str,  # fee
    str,  # link
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class AssetMovement(AccountingEventMixin):
    location: Location
    category: AssetMovementCategory
    timestamp: Timestamp
    # The source address if this is a deposit and the destination address if withdrawal
    address: Optional[str]
    transaction_id: Optional[str]
    asset: Asset
    # Amount is the original amount removed from the account
    amount: FVal
    # The asset that is kept as fee for the deposit/withdrawal
    fee_asset: Asset
    # Fee is the amount of fee_currency that is kept for the deposit/withdrawal. Can be zero
    fee: Fee
    # For exchange asset movements this should be the exchange unique identifier
    # For movements imported from third parties we should generate a unique id for this.
    # If movements are both imported from third parties like cointracking.info and from
    # the exchanges themselves then there is no way to avoid duplicates.
    link: str

    @property
    def identifier(self) -> str:
        """Formulates a unique identifier for the asset movements to become the DB primary key

        We are not using the "self.link" unique exchange identifier as it may not
        be available if importing from third party sources such as cointracking.info

        Unfortunately this makes the AssetMovement identifier pseudo unique and means
        we can't have same asset movements with all of the following attributes.
        """
        string = (
            str(self.location) +
            str(self.category) +
            str(self.timestamp) +
            self.asset.identifier +
            self.fee_asset.identifier +
            self.link
        )
        return hash_id(string)

    def serialize(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
            'timestamp': self.timestamp,
            'location': self.location.serialize(),
            'category': self.category.serialize(),
            'address': self.address,
            'transaction_id': self.transaction_id,
            'asset': self.asset.serialize(),
            'amount': str(self.amount),
            'fee_asset': self.fee_asset.serialize(),
            'fee': str(self.fee),
            'link': self.link,
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'AssetMovement':
        """Deserializes an asset movement dict to an AssetMovement object.
        May raise:
            - DeserializationError
            - KeyError
            - UnknownAsset
        """
        return AssetMovement(
            location=Location.deserialize(data['location']),
            category=AssetMovementCategory.deserialize(data['category']),
            timestamp=deserialize_timestamp(data['timestamp']),
            address=deserialize_optional(data['address'], str),
            transaction_id=deserialize_optional(data['transaction_id'], str),
            asset=Asset(data['asset']),
            amount=deserialize_fval(data['amount'], name='amount', location='data structure'),
            fee_asset=Asset(data['fee_asset']),
            fee=deserialize_fee(data['fee']),
            link=str(data['link']),
        )

    @classmethod
    def deserialize_from_db(cls, entry: AssetMovementDBTuple) -> 'AssetMovement':
        """May raise:
            - DeserializationError
            - UnknownAsset
        """
        return AssetMovement(
            location=Location.deserialize_from_db(entry[1]),
            category=AssetMovementCategory.deserialize_from_db(entry[2]),
            address=entry[3],
            transaction_id=entry[4],
            timestamp=Timestamp(entry[5]),
            asset=Asset(entry[6]),
            amount=deserialize_asset_amount(entry[7]),
            fee_asset=Asset(entry[8]),
            fee=deserialize_fee(entry[9]),
            link=entry[10],
        )

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.timestamp

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.ASSET_MOVEMENT

    def get_identifier(self) -> str:
        return self.identifier

    def get_assets(self) -> List[Asset]:
        return [self.asset, self.fee_asset]

    def should_ignore(self, ignored_ids_mapping: Dict[ActionType, List[str]]) -> bool:
        return self.identifier in ignored_ids_mapping.get(ActionType.ASSET_MOVEMENT, [])

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        if self.asset.identifier == 'KFEE' or not accounting.settings.account_for_assets_movements:
            # There is no reason to process deposits of KFEE for kraken as it has only value
            # internal to kraken and KFEE has no value and will error at cryptocompare price query
            return 1

        if self.fee == ZERO:
            return 1

        accounting.add_spend(
            event_type=AccountingEventType.ASSET_MOVEMENT,
            notes=f'{self.location} {str(self.category)}',
            location=self.location,
            timestamp=self.timestamp,
            asset=self.fee_asset,
            amount=self.fee,
            taxable=True,
            count_entire_amount_spend=True,
            count_cost_basis_pnl=True,
        )
        return 1


TradeDBTuple = Tuple[
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
    # The amount represents the amount bought if it's a buy or or the amount
    # sold if it's a sell. Should NOT include fees
    amount: AssetAmount
    rate: Price
    fee: Optional[Fee] = None
    fee_currency: Optional[Asset] = None
    # For external trades this is optional and is a link to the trade in an explorer
    # For exchange trades this should be the exchange unique trade identifer
    # For trades imported from third parties we should generate a unique id for this.
    # If trades are both imported from third parties like cointracking.info and from
    # the exchanges themselves then there is no way to avoid duplicates.
    link: Optional[str] = None
    notes: Optional[str] = None

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
            (self.link if self.link else '')
        )
        return TradeID(hash_id(string))

    def serialize(self) -> Dict[str, Any]:
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
    def deserialize(cls, data: Dict[str, Any]) -> 'Trade':
        """
        Deserializes a trade dict to a Trade object.
        May raise:
            - UnknownAsset
            - DeserializationError
        """
        return deserialize_trade(data)

    def __str__(self) -> str:
        return (
            f'trade at {str(self.location)} location and date '
            f'{datetime.fromtimestamp(self.timestamp)} '
            f'of type {str(self.trade_type)} with base asset: {self.base_asset.resolve_to_asset_with_name_and_type().name} '  # noqa: E501
            f'and quote asset: {self.quote_asset.resolve_to_asset_with_name_and_type().name}'
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
            base_asset=Asset(entry[3]),
            quote_asset=Asset(entry[4]),
            trade_type=TradeType.deserialize_from_db(entry[5]),
            amount=deserialize_asset_amount(entry[6]),
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

    def get_assets(self) -> List[Asset]:
        return [self.base_asset, self.quote_asset]

    def should_ignore(self, ignored_ids_mapping: Dict[ActionType, List[str]]) -> bool:
        return self.identifier in ignored_ids_mapping.get(ActionType.TRADE, [])

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
            amount_in = self.rate * self.amount  # type: ignore
            notes = f'Sell {asset_out} for {asset_in}.'
        else:  # settlement buy/sell only in poloniex. Should properly process when margin
            return 1  # trades are implemented

        prices = accounting.get_prices_for_swap(
            timestamp=self.timestamp,
            amount_in=amount_in,
            asset_in=asset_in,
            amount_out=amount_out,
            asset_out=asset_out,
            fee=self.fee,
            fee_asset=self.fee_currency,
        )
        if prices is None:
            log.debug(f'Skipping {self} at accounting due to inability to find a price')
            return 1

        group_id = self.identifier
        taxable = accounting.settings.include_crypto2crypto
        if taxable is False:
            try:
                asset_in.resolve_to_fiat_asset()
                taxable = True  # if asset_in is fiat
            except UnknownAsset:
                pass

        _, trade_taxable_amount = accounting.add_spend(
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
        accounting.add_acquisition(
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

        if self.fee is not None and self.fee_currency is not None and self.fee != ZERO:
            # also checking fee_asset != None due to https://github.com/rotki/rotki/issues/4172
            accounting.add_spend(
                event_type=AccountingEventType.FEE,
                notes=notes + 'Fee',
                location=self.location,
                timestamp=self.timestamp,
                asset=self.fee_currency,
                amount=self.fee,
                taxable=True,
                # By setting the taxable amount ratio we determine how much of the fee
                # spending should be a taxable spend and how much free.
                taxable_amount_ratio=trade_taxable_amount / amount_out,
                count_cost_basis_pnl=accounting.settings.include_crypto2crypto,
                count_entire_amount_spend=True,
                extra_data={'group_id': group_id},
            )

        return 1


MarginPositionDBTuple = Tuple[
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
    open_time: Optional[Timestamp]
    close_time: Timestamp
    # Profit loss in pl_currency (does not include fees)
    profit_loss: AssetAmount
    # The asset gained or lost
    pl_currency: Asset
    # Amount of fees paid
    fee: Fee
    # The asset in which fees were paid
    fee_currency: Asset
    # For exchange margins this should be the exchange unique identifer
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

    def serialize(self) -> Dict[str, Any]:
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
    def deserialize(cls, data: Dict[str, Any]) -> 'MarginPosition':
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
            profit_loss=deserialize_asset_amount(data['profit_loss']),
            pl_currency=Asset(data['pl_currency']),
            fee=deserialize_fee(data['fee']),
            fee_currency=Asset(data['fee_currency']),
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
            profit_loss=deserialize_asset_amount(entry[4]),
            pl_currency=Asset(entry[5]),
            fee=deserialize_fee(entry[6]),
            fee_currency=Asset(entry[7]),
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

    def get_assets(self) -> List[Asset]:
        return [self.pl_currency]

    def should_ignore(self, ignored_ids_mapping: Dict[ActionType, List[str]]) -> bool:
        return False

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        if self.profit_loss >= ZERO:
            amount = self.profit_loss
            method = 'acquisition'
        else:
            method = 'spend'
            amount = -self.profit_loss  # type: ignore

        accounting.add_asset_change_event(
            method=method,  # type: ignore
            event_type=AccountingEventType.MARGIN_POSITION,
            notes='Margin position. PnL',
            location=self.location,
            timestamp=self.close_time,
            asset=self.pl_currency,
            amount=amount,
            taxable=True,
        )
        if self.fee != ZERO:
            accounting.add_spend(
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
    earned: AssetAmount
    amount_lent: AssetAmount

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.close_time

    def serialize(self) -> Dict[str, Any]:
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
    def deserialize(cls, data: Dict[str, Any]) -> 'Loan':
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
            currency=Asset(data['currency']),
            fee=deserialize_fee(data['fee']),
            earned=deserialize_asset_amount(data['earned']),
            amount_lent=deserialize_asset_amount(data['amount_lent']),
        )

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.LOAN

    def get_identifier(self) -> str:
        return 'loan_' + str(self.close_time)

    def should_ignore(self, ignored_ids_mapping: Dict[ActionType, List[str]]) -> bool:
        return False

    def get_assets(self) -> List[Asset]:
        return [self.currency]

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        accounting.add_acquisition(
            event_type=AccountingEventType.LOAN,
            notes='Loan',
            location=self.location,
            timestamp=self.close_time,
            asset=self.currency,
            amount=self.earned - self.fee,
            taxable=True,
        )
        return 1


def trade_pair_from_assets(base: AssetWithOracles, quote: AssetWithOracles) -> TradePair:
    return TradePair(f'{base.identifier}_{quote.identifier}')


def deserialize_trade(data: Dict[str, Any]) -> Trade:
    """
    Takes a dict trade representation of our common trade format and serializes
    it into the Trade object

    May raise:
        - UnknownAsset: If the base, quote, fee asset string is not a known asset
        - DeserializationError: If any of the trade dict entries is not as expected
    """
    rate = deserialize_price(data['rate'])
    amount = deserialize_asset_amount(data['amount'])
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
        base_asset=Asset(data['base_asset']),
        quote_asset=Asset(data['quote_asset']),
        trade_type=trade_type,
        amount=amount,
        rate=rate,
        fee=deserialize_optional(data['fee'], deserialize_fee),
        fee_currency=Asset(data['fee_currency']) if data['fee_currency'] is not None else None,  # noqa: E501
        link=trade_link,
        notes=trade_notes,
    )


def trades_from_dictlist(
        given_trades: List[Dict[str, Any]],
        start_ts: Timestamp,
        end_ts: Timestamp,
        location: str,
        msg_aggregator: MessagesAggregator,
) -> List[Trade]:
    """ Gets a list of dict trades, most probably read from the json files and
    a time period. Returns it as a list of the Trade tuples that are inside the time period

    Can raise:
      - KeyError: If a trade dict does not have a key as we expect it
      - DeserializationError: If a trade dict entry is of an unexpected format
    """
    returned_trades = []
    for given_trade in given_trades:
        timestamp = deserialize_timestamp(given_trade['timestamp'])
        if timestamp < start_ts:
            continue
        if timestamp > end_ts:
            break

        try:
            returned_trades.append(deserialize_trade(given_trade))
        except UnknownAsset as e:
            msg_aggregator.add_warning(
                f'When processing {location} trades found a trade containing unknown '
                f'asset {e.asset_name}. Ignoring it.')
            continue

    return returned_trades


BINANCE_PAIR_DB_TUPLE = Tuple[str, str, str, str]


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
