from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.crypto import sha3
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_movement_category_from_db,
    deserialize_fee,
    deserialize_optional,
    deserialize_timestamp,
    deserialize_trade_type,
    deserialize_trade_type_from_db,
)
from rotkehlchen.typing import (
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


class AssetMovement(NamedTuple):
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
        result = self._asdict()  # pylint: disable=no-member
        result['identifier'] = self.identifier
        return result

    @classmethod
    def deserialize_from_db(cls, entry: AssetMovementDBTuple) -> 'AssetMovement':
        """May raise:
            - DeserializationError
            - UnknownAsset
        """
        return AssetMovement(
            location=Location.deserialize_from_db(entry[1]),
            category=deserialize_asset_movement_category_from_db(entry[2]),
            address=entry[3],
            transaction_id=entry[4],
            timestamp=Timestamp(entry[5]),
            asset=Asset(entry[6]),
            # TODO: should we also _force_positive here? I guess not since
            # we always make sure to save it as positive
            amount=deserialize_asset_amount(entry[7]),
            fee_asset=Asset(entry[8]),
            fee=deserialize_fee(entry[9]),
            link=entry[10],
        )


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


class Trade(NamedTuple):
    """Represents a Trade

    Pairs are represented as BASE_QUOTE. When a buy is made, then the BASE
    asset is bought with QUOTE asset. When a sell is made then the BASE
    asset is sold for QUOTE asset.

    Exchanges don't use the same part of the pair to denote the same thing. For
    example in Poloniex the pair is called BTC_ETH and you buy and sell ETH for
    BTC. In Kraken XXBTZEUR translates to BTC_EUR. This means we buy BTC for EUR
    or we sell BTC for EUR. So for some exchanges like poloniex when importing a
    trade, the base and quote assets need to be swapped.

    All trades have a unique ID which is generated from some of the attributes.
    For details check identifier() function
    This unique ID is not stored in the NamedTuple since it depends on some of
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
    fee: Optional[Fee]
    fee_currency: Optional[Asset]
    # For external trades this is optional and is a link to the trade in an explorer
    # For exchange trades this should be the exchange unique trade identifer
    # For trades imported from third parties we should generate a unique id for this.
    # If trades are both imported from third parties like cointracking.info and from
    # the exchanges themselves then there is no way to avoid duplicates.
    link: Optional[str]
    notes: Optional[str] = None

    @property
    def identifier(self) -> TradeID:
        """Formulates a unique identifier for the trade to become the DB primary key
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

    def __str__(self) -> str:
        return (
            f'trade at {str(self.location)} location and date '
            f'{datetime.fromtimestamp(self.timestamp)} '
            f'of type {str(self.trade_type)} with base asset: {self.base_asset.name} '
            f'and quote asset: {self.quote_asset.name}'
        )

    @classmethod
    def deserialize_from_db(cls, entry: TradeDBTuple) -> 'Trade':
        """May raise:
            - DeserializationError
            - UnknownAsset
        """
        return Trade(
            timestamp=deserialize_timestamp(entry[1]),
            location=Location.deserialize_from_db(entry[2]),
            base_asset=Asset(entry[3]),
            quote_asset=Asset(entry[4]),
            trade_type=deserialize_trade_type_from_db(entry[5]),
            amount=deserialize_asset_amount(entry[6]),
            rate=deserialize_price(entry[7]),
            fee=deserialize_optional(entry[8], deserialize_fee),
            fee_currency=deserialize_optional(entry[9], Asset),
            link=entry[10],
            notes=entry[11],
        )


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


class MarginPosition(NamedTuple):
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


class Loan(NamedTuple):
    """We only support loans in poloniex at the moment"""
    location: Location
    open_time: Timestamp
    close_time: Timestamp
    currency: Asset
    fee: Fee
    earned: AssetAmount
    amount_lent: AssetAmount


def trade_pair_from_assets(base: Asset, quote: Asset) -> TradePair:
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
    trade_type = deserialize_trade_type(data['trade_type'])
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
        fee=deserialize_fee(data['fee']),
        fee_currency=Asset(data['fee_currency']),
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
