import builtins
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Literal, TypeVar, overload

from rotkehlchen.accounting.cost_basis import CostBasisInfo
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.constants import EVM_ADDRESS_REGEX
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.db.addressbook import DBAddressbook
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import (
    EVM_EVMLIKE_LOCATIONS,
    AddressbookType,
    ChainAddress,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.serialization import rlk_jsondumps

T = TypeVar('T', bound='ProcessedAccountingEvent')


class AccountingEventExportType(Enum):
    API = auto()
    CSV = auto()
    DB = auto()


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ProcessedAccountingEvent:
    """An event after having been processed by accounting. This is what:
        - Gets returned via the API
        - Gets saved in the DB for saved reports
        - Exported via CSV
    """
    event_type: AccountingEventType
    notes: str
    location: Location
    timestamp: Timestamp
    asset: Asset
    free_amount: FVal
    taxable_amount: FVal
    price: Price
    pnl: PNL
    cost_basis: CostBasisInfo | None
    index: int
    # This is set only for some events to remember extra data that can be used later
    # such as the transaction hash of an event
    extra_data: dict[str, Any] = field(default_factory=dict)
    # These are set by calculate pnl and are only here to be remembered by the
    # processed accounting event so that the CSV export formulas can be correctly made
    count_entire_amount_spend: bool = field(init=False, default=False)
    count_cost_basis_pnl: bool = field(init=False, default=False)

    def to_string(self, ts_converter: Callable[[Timestamp], str]) -> str:
        desc = f'{self.event_type.name} for {self.free_amount}/{self.taxable_amount} {self.asset.symbol_or_name()} with price: {self.price} and PNL: {self.pnl}.'  # noqa: E501
        if self.cost_basis:
            taxable, free = self.cost_basis.to_string(ts_converter)
            desc += f'Cost basis. Taxable {taxable}. Free: {free}'

        return desc

    def _maybe_add_label_with_address(
            self,
            database: DBHandler,
            matched_address: re.Match[str],
    ) -> str:
        """Aux method to enrich addresses in the event notes using the addressbook"""
        chain_address = ChainAddress(
            address=string_to_evm_address(matched_address.group()),
            blockchain=SupportedBlockchain.from_location(self.location),  # type: ignore  # where this is called from we check self.location in EVM_EVMLIKE_LOCATIONS
        )
        name = DBAddressbook(database).get_addressbook_entry_name(AddressbookType.PRIVATE, chain_address)  # noqa: E501
        return f'{chain_address.address} [{name}]' if name else chain_address.address

    @overload
    def to_exported_dict(
            self,
            ts_converter: Callable[[Timestamp], str],
            export_type: Literal[AccountingEventExportType.CSV],
            database: DBHandler,
            evm_explorer: str | None,
    ) -> dict[str, Any]:
        ...

    @overload
    def to_exported_dict(
            self,
            ts_converter: Callable[[Timestamp], str],
            export_type: Literal[AccountingEventExportType.API, AccountingEventExportType.DB],
    ) -> dict[str, Any]:
        ...

    def to_exported_dict(
            self,
            ts_converter: Callable[[Timestamp], str],
            export_type: AccountingEventExportType,
            database: DBHandler | None = None,
            evm_explorer: str | None = None,
    ) -> dict[str, Any]:
        """These are the fields that will appear in CSV, report API and are also exported to the
        database.

        `export_type` will affect the information that is added to the exported mapping.
        If `export_type` is set to CSV then `evm_explorer` is used to format the notes adding
        a link to each transaction.
        """
        exported_dict = {
            'type': self.event_type.serialize(),
            'notes': self.notes,
            'location': str(self.location),
            'timestamp': self.timestamp,
            'asset_identifier': self.asset.identifier,
            'free_amount': str(self.free_amount),
            'taxable_amount': str(self.taxable_amount),
            'price': str(self.price),
            'pnl_taxable': str(self.pnl.taxable),
            'pnl_free': str(self.pnl.free),
        }
        tx_hash = self.extra_data.get('tx_hash', None)
        if export_type == AccountingEventExportType.CSV:
            taxable_basis = free_basis = ''
            if self.cost_basis is not None:
                taxable_basis, free_basis = self.cost_basis.to_string(ts_converter)
            exported_dict['cost_basis_taxable'] = taxable_basis
            exported_dict['cost_basis_free'] = free_basis
            exported_dict['asset_identifier'] = str(self.asset)
            try:
                exported_dict['asset'] = self.asset.symbol_or_name()
            except UnknownAsset:
                exported_dict['asset'] = ''
            if tx_hash is not None:
                exported_dict['notes'] = f'{evm_explorer}{tx_hash}  ->  {self.notes}'

            if self.location in EVM_EVMLIKE_LOCATIONS and database is not None:
                # call _maybe_add_label_with_address on each address in the note
                exported_dict['notes'] = EVM_ADDRESS_REGEX.sub(
                    repl=lambda matched_address: self._maybe_add_label_with_address(
                        database=database,
                        matched_address=matched_address,
                    ),
                    string=exported_dict['notes'],  # type: ignore [call-overload]  # exported_dict['notes'] is always a string
                )
        else:  # for the other types of export we include the cost basis information
            cost_basis = None
            if self.cost_basis is not None:
                cost_basis = self.cost_basis.serialize()
            exported_dict['cost_basis'] = cost_basis

        if export_type == AccountingEventExportType.API:
            if tx_hash is not None:
                exported_dict['notes'] = f'transaction {tx_hash} {self.notes}'

            group_id = self.extra_data.get('group_id', None)
            if group_id is not None:
                exported_dict['group_id'] = group_id

        return exported_dict

    def serialize_to_dict(self, ts_converter: Callable[[Timestamp], str]) -> dict[str, Any]:
        """This is used to serialize to dict for saving to the DB"""
        data = self.to_exported_dict(ts_converter=ts_converter, export_type=AccountingEventExportType.DB)  # noqa: E501
        data['extra_data'] = self.extra_data
        data['notes'] = self.notes  # undo the tx_hash addition to notes before going to the DB
        data['index'] = self.index
        data['count_entire_amount_spend'] = self.count_entire_amount_spend
        data['count_cost_basis_pnl'] = self.count_cost_basis_pnl
        return data

    def calculate_pnl(
            self,
            count_entire_amount_spend: bool,
            count_cost_basis_pnl: bool,
    ) -> PNL:
        """Calculate PnL for this event and return it.
        Only called for events that should have PnL counted

        If count_entire_amount_spend is True then the entire amount is counted as a spend.
        Which means an expense (negative pnl).

        If count_cost_basis_pnl is True then the PnL between buying the asset amount
        and spending it is calculated and added to PnL.
        """
        self.count_entire_amount_spend = count_entire_amount_spend
        self.count_cost_basis_pnl = count_cost_basis_pnl
        taxable_bought_cost = taxfree_bought_cost = ZERO
        taxable_value = self.taxable_amount * self.price
        free_value = self.free_amount * self.price
        self.pnl = PNL()
        if count_entire_amount_spend:
            # for fees and other types we also need to consider the entire amount as spent
            self.pnl -= PNL(taxable=taxable_value + free_value, free=ZERO)
            if self.asset.is_fiat():
                return self.pnl  # no need to calculate spending pnl if asset is fiat

        if count_cost_basis_pnl is False:
            return self.pnl

        if self.cost_basis is not None:
            taxable_bought_cost = self.cost_basis.taxable_bought_cost
            taxfree_bought_cost = self.cost_basis.taxfree_bought_cost

        self.pnl += PNL(
            taxable=taxable_value - taxable_bought_cost,
            free=free_value - taxfree_bought_cost,
        )

        return self.pnl

    def serialize_for_db(self, ts_converter: Callable[[Timestamp], str]) -> str:
        """May raise:

        - DeserializationError if something fails during conversion to the DB tuple
        """
        json_data = self.serialize_to_dict(ts_converter)
        try:
            string_data = rlk_jsondumps(json_data)
        except (OverflowError, ValueError, TypeError) as e:
            raise DeserializationError(
                f'Could not dump json to string for NamedJson. Error was {e!s}',
            ) from e

        return string_data

    @classmethod
    def deserialize_from_db(cls: builtins.type[T], timestamp: Timestamp, stringified_json: str) -> T:  # noqa: E501
        """May raise:
        - DeserializationError if something is wrong with reading this from the DB
        """
        try:
            data = json.loads(stringified_json)
        except json.decoder.JSONDecodeError as e:
            raise DeserializationError(
                f'Could not decode processed accounting event json from the DB due to {e!s}',
            ) from e

        try:
            pnl_taxable = deserialize_fval(data['pnl_taxable'], name='pnl_taxable', location='processed event decoding')  # noqa: E501
            pnl_free = deserialize_fval(data['pnl_free'], name='pnl_free', location='processed event decoding')  # noqa: E501
            if data['cost_basis'] is None:
                cost_basis = None
            else:
                cost_basis = CostBasisInfo.deserialize(data['cost_basis'])
            event = cls(
                event_type=AccountingEventType.deserialize(data['type']),
                notes=data['notes'],
                location=Location.deserialize(data['location']),
                timestamp=timestamp,
                asset=Asset(data['asset_identifier']).check_existence(),
                free_amount=deserialize_fval(data['free_amount'], name='free_amount', location='processed event decoding'),  # noqa: E501
                taxable_amount=deserialize_fval(data['taxable_amount'], name='taxable_amount', location='processed event decoding'),  # noqa: E501
                price=deserialize_price(data['price']),
                pnl=PNL(free=pnl_free, taxable=pnl_taxable),
                cost_basis=cost_basis,
                index=data['index'],
                extra_data=data['extra_data'],
            )
            event.count_cost_basis_pnl = data['count_cost_basis_pnl']
            event.count_entire_amount_spend = data['count_entire_amount_spend']
        except KeyError as e:
            raise DeserializationError(f'Could not decode processed accounting event json from the DB due to missing key {e!s}') from e  # noqa: E501
        except UnknownAsset as e:
            raise DeserializationError(f'Couldnt deserialize processed accounting event due to unknown asset {e.identifier}') from e  # noqa: E501
        else:
            return event
