from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.crypto import sha3
from rotkehlchen.errors import UnknownAsset
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_location,
    deserialize_price,
    deserialize_timestamp,
    deserialize_trade_pair,
    deserialize_trade_type,
    get_pair_position_str,
    pair_get_assets,
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


class Trade(NamedTuple):
    """Represents a Trade

    Pairs are represented as BASE_QUOTE. When a buy is made, then the BASE
    asset is bought with QUOTE asset. When a sell is made then the BASE
    asset is sold for QUOTE asset.

    Exchanges don't use the same part of the pair to denote the same thing. For
    example in Poloniex the pair is called BTC_ETH and you buy and sell ETH for
    BTC. In Kraken XXBTZEUR translates to BTC_EUR. This means we buy BTC for EUR
    or we sell BTC for EUR. So for some exchanges like poloniex when importing a
    trade, the pair needs to be swapped.

    All trades have a unique ID which is generated from some of the attributes.
    For details check identifier() function
    This unique ID is not stored in the NamedTuple since it depends on some of
    its attributes.
    """
    timestamp: Timestamp
    location: Location
    pair: TradePair
    trade_type: TradeType
    # The amount represents the amount bought if it's a buy or or the amount
    # sold if it's a sell. Should NOT include fees
    amount: AssetAmount
    rate: Price
    fee: Fee
    fee_currency: Asset
    # For external trades this is optional and is a link to the trade in an explorer
    # For exchange trades this should be the exchange unique trade identifer
    # For trades imported from third parties we should generate a unique id for this.
    # If trades are both imported from third parties like cointracking.info and from
    # the exchanges themselves then there is no way to avoid duplicates.
    link: str
    notes: str = ''

    @property
    def base_asset(self) -> Asset:
        base, _ = pair_get_assets(self.pair)
        return base

    @property
    def quote_asset(self) -> Asset:
        _, quote = pair_get_assets(self.pair)
        return quote

    @property
    def identifier(self) -> TradeID:
        """Formulates a unique identifier for the trade to become the DB primary key
        """
        string = (
            str(self.location) +
            str(self.timestamp) +
            str(self.trade_type) +
            self.pair +
            str(self.amount) +
            str(self.rate) +
            self.link
        )
        return TradeID(hash_id(string))

    def serialize(self) -> Dict[str, Any]:
        """Serialize the trade into a dict"""
        return {
            'timestamp': self.timestamp,
            'location': str(self.location),
            'pair': self.pair,
            'trade_type': str(self.trade_type),
            'amount': str(self.amount),
            'rate': str(self.rate),
            'fee': str(self.fee),
            'fee_currency': self.fee_currency.identifier,
            'link': self.link,
            'notes': self.notes,
        }


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


def invert_pair(pair: TradePair) -> TradePair:
    left, right = pair_get_assets(pair)
    return trade_pair_from_assets(right, left)


def get_pair_position_asset(pair: TradePair, position: str) -> Asset:
    """
    Get the asset of a trade pair.

    Can throw UnknownAsset if the asset is not known to Rotkehlchen
    """
    return Asset(get_pair_position_str(pair, position))


def trade_get_assets(trade: Union[Trade, AMMTrade]) -> Tuple[Asset, Asset]:
    if isinstance(trade, Trade):
        return pair_get_assets(trade.pair)

    # else should only be AMMTrade
    return trade.base_asset, trade.quote_asset  # type: ignore


def deserialize_trade(data: Dict[str, Any]) -> Trade:
    """
    Takes a dict trade representation of our common trade format and serializes
    it into the Trade object

    May raise:
        - UnknownAsset: If the fee_currency string is not a known asset
        - DeserializationError: If any of the trade dict entries is not as expected
    """
    pair = deserialize_trade_pair(data['pair'])
    rate = deserialize_price(data['rate'])
    amount = deserialize_asset_amount(data['amount'])
    trade_type = deserialize_trade_type(data['trade_type'])
    location = deserialize_location(data['location'])

    trade_link = ''
    if 'link' in data:
        trade_link = data['link']
    trade_notes = ''
    if 'notes' in data:
        trade_notes = data['notes']

    return Trade(
        timestamp=data['timestamp'],
        location=location,
        pair=pair,
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
