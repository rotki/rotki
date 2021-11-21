import json
from typing import Dict, Any, Optional, NamedTuple, Tuple

from rotkehlchen.assets.asset import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_timestamp, deserialize_asset_amount
from rotkehlchen.typing import NamedJson, EventType, Location, Timestamp, SchemaEventType

AccountingEventCacheEntryDBTuple = (
    Tuple[
        str,  # type
        str,  # location
        str,  # paid_in_profit_currency
        str,  # paid_asset
        str,  # paid_in_asset
        str,  # taxable_amount
        str,  # taxable_bought_cost_in_profit_currency
        str,  # received_asset
        str,  # taxable_received_in_profit_currency
        str,  # received_in_asset
        str,  # net_profit_or_loss
        int,  # time
        str,  # cost_basis
        bool,  # is_virtual
        str,  # link
        str,  # notes
    ]
)


class AccountingEventCacheEntry(NamedTuple):
    type: EventType
    location: Location
    paid_in_profit_currency: FVal
    paid_asset: Optional[Asset]
    paid_in_asset: FVal
    taxable_amount: FVal
    taxable_bought_cost_in_profit_currency: FVal
    received_asset: Optional[Asset]
    taxable_received_in_profit_currency: FVal
    received_in_asset: FVal
    net_profit_or_loss: FVal
    time: Timestamp
    cost_basis: Optional[Dict[str, Any]]
    is_virtual: bool
    link: Optional[str]
    notes: Optional[str]

    @classmethod
    def deserialize_from_db(
            cls,
            event_tuple: AccountingEventCacheEntryDBTuple,
    ) -> 'AccountingEventCacheEntry':
        """Turns a tuple read from the database into an appropriate AccountingEvent.
        May raise a DeserializationError if something is wrong with the DB data
        Event_tuple index - Schema columns
        ----------------------------------
        0 - type
        1 - location
        2 - aid_in_profit_currency
        3 - paid_asset
        4 - paid_in_asset
        5 - taxable_amount
        6 - taxable_bought_cost_in_profit_currency
        7 - received_asset
        8 - taxable_received_in_profit_currency
        9 - received_in_asset
        10 - net_profit_or_loss
        11 - time
        12 - cost_basis
        13 - is_virtual
        14 - link
        15 - notes
        """
        return cls(
            type=EventType(event_tuple[0]),
            location=Location.deserialize_from_db(event_tuple[1]),
            paid_in_profit_currency=deserialize_asset_amount(event_tuple[2]),
            paid_asset=Asset(event_tuple[3]),
            paid_in_asset=deserialize_asset_amount(event_tuple[4]),
            taxable_amount=deserialize_asset_amount(event_tuple[5]),
            taxable_bought_cost_in_profit_currency=deserialize_asset_amount(event_tuple[6]),
            received_asset=Asset(event_tuple[7]),
            taxable_received_in_profit_currency=deserialize_asset_amount(event_tuple[8]),
            received_in_asset=deserialize_asset_amount(event_tuple[9]),
            net_profit_or_loss=deserialize_asset_amount(event_tuple[10]),
            time=deserialize_timestamp(event_tuple[11]),
            cost_basis=json.loads(event_tuple[12]),
            is_virtual=bool(event_tuple[13]),
            link=json.loads(event_tuple[14]),
            notes=json.loads(event_tuple[15]),
        )

    def to_db_tuple(self) -> AccountingEventCacheEntryDBTuple:
        return (
            str(self.type),
            str(self.location),
            str(self.paid_in_profit_currency),
            str(self.paid_asset),
            str(self.paid_in_asset),
            str(self.taxable_amount),
            str(self.taxable_bought_cost_in_profit_currency),
            str(self.received_asset),
            str(self.taxable_received_in_profit_currency),
            str(self.received_in_asset),
            str(self.net_profit_or_loss),
            int(self.time),
            json.dumps(self.cost_basis),
            bool(self.is_virtual),
            json.dumps(self.link),
            json.dumps(self.notes),
        )

    def serialize(self) -> Dict[str, Any]:
        """Returns a dict with python primitive types compatible with the NamedJson schema"""
        exported_paid_asset = (
            self.paid_asset if isinstance(self.paid_asset, str) else str(self.paid_asset)
        )
        exported_received_asset = (
            self.received_asset if isinstance(self.received_asset, str) else str(self.received_asset)  # noqa E501
        )
        result_dict = {
            'event_type': str(self.type),
            'location': str(self.location),
            'paid_in_profit_currency': str(self.paid_in_profit_currency),
            'paid_asset': exported_paid_asset,
            'paid_in_asset': str(self.paid_in_asset),
            'taxable_amount': str(self.taxable_amount),
            'taxable_bought_cost_in_profit_currency': str(
                self.taxable_bought_cost_in_profit_currency),  # noqa E501
            'received_asset': exported_received_asset,
            'taxable_received_in_profit_currency': str(self.taxable_received_in_profit_currency),
            'received_in_asset': str(self.received_in_asset),
            'net_profit_or_loss': str(self.net_profit_or_loss),
            'time': int(self.time),
            'cost_basis': self.cost_basis,
            'is_virtual': self.is_virtual,
            'link': self.link,
            'notes': self.notes,
        }
        named_json: NamedJson = NamedJson(SchemaEventType.ACCOUNTING_EVENT, result_dict)
        return named_json.data
