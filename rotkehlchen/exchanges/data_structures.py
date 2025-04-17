import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.assets.converters import asset_from_binance
from rotkehlchen.constants import ZERO
from rotkehlchen.crypto import sha3
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_fval,
    deserialize_fval_or_zero,
    deserialize_timestamp,
)
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.fval import FVal


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def hash_id(hashable: str) -> str:
    id_bytes = sha3(hashable.encode())
    return id_bytes.hex()


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
    fee: 'FVal'
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
            fee=deserialize_fval_or_zero(data['fee']),
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
            fee=deserialize_fval_or_zero(entry[6]),
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

    def should_ignore(self, ignored_ids: set[str]) -> bool:
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
    fee: 'FVal'
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
            fee=deserialize_fval_or_zero(data['fee']),
            earned=deserialize_fval(data['earned']),
            amount_lent=deserialize_fval(data['amount_lent']),
        )

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.LOAN

    def get_identifier(self) -> str:
        return 'loan_' + str(self.close_time)

    def should_ignore(self, ignored_ids: set[str]) -> bool:
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
