import logging
from dataclasses import dataclass
from typing import Any, Dict, NamedTuple, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_optional,
    deserialize_timestamp,
)
from rotkehlchen.typing import AssetAmount, Location, Price, Timestamp, Tuple
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn

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


class GitcoinEventTxType(DBEnumMixIn):
    ETHEREUM = 1
    ZKSYNC = 2


GitcoinEventDataDB = Tuple[
    int,            # parent_id
    str,            # tx_id
    int,            # grant_id
    Optional[int],  # clr_round
    str,            # tx_type
]


class GitcoinEventData(NamedTuple):
    tx_id: str
    grant_id: int
    clr_round: Optional[int]
    tx_type: GitcoinEventTxType

    def serialize_for_db(self, parent_id: int) -> GitcoinEventDataDB:
        """Serializes Gitcoin event data to a tuple for writing to DB"""
        return (
            parent_id,
            self.tx_id,
            self.grant_id,
            self.clr_round,
            self.tx_type.serialize_for_db(),
        )

    @staticmethod
    def deserialize_from_db(data: GitcoinEventDataDB) -> 'GitcoinEventData':
        """May raise:
        - DeserializationError
        """
        return GitcoinEventData(
            tx_id=data[1],
            grant_id=data[2],
            clr_round=data[3],
            tx_type=GitcoinEventTxType.deserialize_from_db(data[4]),
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class LedgerAction:
    """Represents an income/loss/expense for accounting purposes"""
    identifier: int  # the unique id of the action and DB primary key
    timestamp: Timestamp
    action_type: LedgerActionType
    location: Location
    amount: AssetAmount
    asset: Asset
    rate: Optional[Price]
    rate_asset: Optional[Asset]
    link: Optional[str]
    notes: Optional[str]
    extra_data: Optional[GitcoinEventData] = None

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

    def serialize_for_gitcoin(self) -> Dict[str, Any]:
        """Should only be called for actions that have gitcoin data"""
        extra_data: GitcoinEventData = self.extra_data  # type: ignore
        return {
            'timestamp': self.timestamp,
            'amount': str(self.amount),
            'asset': self.asset.identifier,
            'usd_value': str(self.amount * self.rate),  # type: ignore
            'grant_id': extra_data.grant_id,
            'tx_id': extra_data.tx_id,
            'tx_type': str(extra_data.tx_type),
            'clr_round': extra_data.clr_round,
        }

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
            given_gitcoin_map: Optional[Dict[int, GitcoinEventDataDB]] = None,
    ) -> 'LedgerAction':
        """May raise:
        - DeserializationError
        - UnknownAsset
        """
        extra_data = None
        gitcoin_map = {} if not given_gitcoin_map else given_gitcoin_map
        gitcoin_data = gitcoin_map.get(data[0], None)
        if gitcoin_data is not None:
            extra_data = GitcoinEventData.deserialize_from_db(data=gitcoin_data)

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
            extra_data=extra_data,
        )

    def is_profitable(self) -> bool:
        return self.action_type.is_profitable()
