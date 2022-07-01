import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.base import ActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_optional,
    deserialize_timestamp,
)
from rotkehlchen.types import AssetAmount, Location, Price, Timestamp, Tuple
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class LedgerActionType(DBEnumMixIn):
    INCOME = 1
    EXPENSE = 2
    LOSS = 3
    DIVIDENDS_INCOME = 4
    DONATION_RECEIVED = 5
    AIRDROP = 6
    GIFT = 7
    GRANT = 8

    def is_profitable(self) -> bool:
        return self in (
            LedgerActionType.INCOME,
            LedgerActionType.DIVIDENDS_INCOME,
            LedgerActionType.DONATION_RECEIVED,
            LedgerActionType.AIRDROP,
            LedgerActionType.GIFT,
            LedgerActionType.GRANT,
        )


LedgerActionDBTuple = Tuple[
    int,  # timestamp
    str,  # action_type
    str,  # location
    str,  # amount
    str,  # asset
    Optional[str],  # rate
    Optional[str],  # rate_asset
    Optional[str],  # link
    Optional[str],  # notes
]


LedgerActionDBTupleWithIdentifier = Tuple[
    int,  # identifier
    int,  # timestamp
    str,  # action_type
    str,  # location
    str,  # amount
    str,  # asset
    Optional[str],  # rate
    Optional[str],  # rate_asset
    Optional[str],  # link
    Optional[str],  # notes
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class LedgerAction(AccountingEventMixin):
    """Represents an income/loss/expense for accounting purposes"""
    identifier: int  # the unique id of the action and DB primary key
    timestamp: Timestamp
    action_type: LedgerActionType
    location: Location
    amount: AssetAmount
    asset: Asset
    rate: Optional[Price] = None
    rate_asset: Optional[Asset] = None
    link: Optional[str] = None
    notes: Optional[str] = None

    def __hash__(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return (
            f'<LedgerAction '
            f'id={self.identifier} timestamp={self.timestamp} action_type={str(self.action_type)} '
            f'location={str(self.location)} amount={str(self.amount)} '
            f'asset={self.asset.identifier} rate={str(self.rate) if self.rate else None}'
            f'rate_asset={self.rate_asset.identifier if self.rate_asset else None} '
            f'link={self.link} notes={self.notes}>'
        )

    def serialize(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
            'timestamp': self.timestamp,
            'action_type': str(self.action_type),
            'location': str(self.location),
            'amount': str(self.amount),
            'asset': self.asset.identifier,
            'rate': str(self.rate) if self.rate else None,
            'rate_asset': self.rate_asset.identifier if self.rate_asset else None,
            'link': self.link,
            'notes': self.notes,
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'LedgerAction':
        """Deserializes a ledger action dict to a LedgerAction object.
        May raise:
            - DeserializationError
            - KeyError
            - UnknownAsset
        """
        return cls(
            identifier=int(data['identifier']),
            timestamp=deserialize_timestamp(data['timestamp']),
            action_type=LedgerActionType.deserialize(data['action_type']),
            location=Location.deserialize(data['location']),
            asset=Asset(data['asset']),
            amount=deserialize_asset_amount(data['amount']),
            rate=deserialize_optional(data['rate'], deserialize_price),
            link=deserialize_optional(data['link'], str),
            notes=deserialize_optional(data['notes'], str),
            rate_asset=Asset(data['rate_asset']) if data.get('rate_asset') is not None else None,
        )

    def serialize_for_db(self) -> LedgerActionDBTuple:
        """Serializes an action for writing in the DB.
        Identifier and extra_data are ignored"""
        return (
            self.timestamp,
            self.action_type.serialize_for_db(),
            self.location.serialize_for_db(),
            str(self.amount),
            self.asset.identifier,
            str(self.rate) if self.rate else None,
            self.rate_asset.identifier if self.rate_asset else None,
            self.link,
            self.notes,
        )

    @classmethod
    def deserialize_from_db(
            cls,
            data: LedgerActionDBTupleWithIdentifier,
    ) -> 'LedgerAction':
        """May raise:
        - DeserializationError
        - UnknownAsset
        """
        return cls(
            identifier=data[0],
            timestamp=deserialize_timestamp(data[1]),
            action_type=LedgerActionType.deserialize_from_db(data[2]),
            location=Location.deserialize_from_db(data[3]),
            amount=deserialize_asset_amount(data[4]),
            asset=Asset(data[5]),
            rate=deserialize_optional(data[6], deserialize_price),
            rate_asset=deserialize_optional(data[7], Asset),
            link=data[8],
            notes=data[9],
        )

    def is_profitable(self) -> bool:
        return self.action_type.is_profitable()

    # -- Methods of AccountingEventMixin

    def get_timestamp(self) -> Timestamp:
        return self.timestamp

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.LEDGER_ACTION

    def get_identifier(self) -> str:
        return str(self.identifier)

    def should_ignore(self, ignored_ids_mapping: Dict[ActionType, List[str]]) -> bool:
        return self.get_identifier() in ignored_ids_mapping.get(ActionType.LEDGER_ACTION, [])

    def get_assets(self) -> List[Asset]:
        return [self.asset]

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: Iterator['AccountingEventMixin'],  # pylint: disable=unused-argument
    ) -> int:
        given_price = None  # Determine if non-standard price should be used
        if self.rate is not None and self.rate_asset is not None:
            if self.rate_asset == accounting.profit_currency:
                given_price = self.rate
            else:
                quote_rate = accounting.get_rate_in_profit_currency(self.rate_asset, self.timestamp)  # noqa: E501
                given_price = Price(self.rate * quote_rate)

        taxed = self.action_type in accounting.settings.taxable_ledger_actions
        notes = self.notes if self.notes else f'{self.action_type} ledger action'
        if self.is_profitable():
            accounting.add_acquisition(
                event_type=AccountingEventType.LEDGER_ACTION,
                notes=notes,
                location=self.location,
                timestamp=self.timestamp,
                asset=self.asset,
                amount=self.amount,
                taxable=taxed,
                given_price=given_price,
            )
        else:
            accounting.add_spend(
                event_type=AccountingEventType.LEDGER_ACTION,
                notes=notes,
                location=self.location,
                timestamp=self.timestamp,
                asset=self.asset,
                amount=self.amount,
                taxable=taxed,
                given_price=given_price,
            )

        return 1
