import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Type, TypeVar

from rotkehlchen.accounting.cost_basis import CostBasisInfo
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.utils.serialization import rlk_jsondumps

T = TypeVar('T', bound='ProcessedAccountingEvent')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ProcessedAccountingEvent:
    """An event after having been processed by accounting. This is what:
        - Gets returned via the API
        - Gets saved in the DB for saved reports
        - Exported via CSV
    """
    type: AccountingEventType
    notes: str
    location: Location
    timestamp: Timestamp
    asset: Asset
    free_amount: FVal
    taxable_amount: FVal
    price: Price
    pnl: PNL
    cost_basis: Optional['CostBasisInfo']
    index: int
    # This is set only for some events to remember extra data that can be used later
    # such as the transaction hash of an event
    extra_data: Dict[str, Any] = field(default_factory=dict)
    # These are set by calculate pnl and are only here to be remembered by the
    # processed accounting event so that the CSV export formulas can be correctly made
    count_entire_amount_spend: bool = field(init=False, default=False)
    count_cost_basis_pnl: bool = field(init=False, default=False)

    def to_string(self, ts_converter: Callable[[Timestamp], str]) -> str:
        desc = f'{self.type.name} for {self.free_amount}/{self.taxable_amount} {self.asset.symbol_or_name()} with price: {self.price} and PNL: {self.pnl}.'  # noqa: E501
        if self.cost_basis:
            taxable, free = self.cost_basis.to_string(ts_converter)
            desc += f'Cost basis. Taxable {taxable}. Free: {free}'

        return desc

    def to_exported_dict(
            self,
            ts_converter: Callable[[Timestamp], str],
            eth_explorer: Optional[str],
            for_api: bool,
    ) -> Dict[str, Any]:
        """These are the fields that will appear in CSV and report API

        If `eth_explorer` is given then this is for exporting to CSV
        If `for_api` is True then this is for exporting to the rest API
        """
        exported_dict = {
            'type': self.type.serialize(),
            'notes': self.notes,
            'location': str(self.location),
            'timestamp': self.timestamp,
            'asset': self.asset.identifier,
            'free_amount': str(self.free_amount),
            'taxable_amount': str(self.taxable_amount),
            'price': str(self.price),
            'pnl_taxable': str(self.pnl.taxable),
            'pnl_free': str(self.pnl.free),
        }
        tx_hash = self.extra_data.get('tx_hash', None)
        if eth_explorer:
            taxable_basis = free_basis = ''
            if self.cost_basis is not None:
                taxable_basis, free_basis = self.cost_basis.to_string(ts_converter)
            exported_dict['cost_basis_taxable'] = taxable_basis
            exported_dict['cost_basis_free'] = free_basis
            exported_dict['asset'] = str(self.asset)
            if tx_hash:
                exported_dict['notes'] = f'{eth_explorer}{tx_hash}  ->  {self.notes}'
        else:
            cost_basis = None
            if self.cost_basis is not None:
                cost_basis = self.cost_basis.serialize()
            exported_dict['cost_basis'] = cost_basis

        if for_api is True:
            if tx_hash is not None:
                exported_dict['notes'] = f'transaction {tx_hash} {self.notes}'

            group_id = self.extra_data.get('group_id', None)
            if group_id is not None:
                exported_dict['group_id'] = group_id

        return exported_dict

    def serialize_to_dict(self, ts_converter: Callable[[Timestamp], str]) -> Dict[str, Any]:
        """This is used to serialize to dict for saving to the DB"""
        data = self.to_exported_dict(
            ts_converter=ts_converter,
            eth_explorer=None,
            for_api=False,
        )
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

        if self.asset.is_fiat() or count_cost_basis_pnl is False:
            return self.pnl  # no need to calculate spending pnl if asset is fiat

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
                f'Could not dump json to string for NamedJson. Error was {str(e)}',
            ) from e

        return string_data

    @classmethod
    def deserialize_from_db(cls: Type[T], timestamp: Timestamp, stringified_json: str) -> T:
        """May raise:
        - DeserializationError if something is wrong with reading this from the DB
        """
        try:
            data = json.loads(stringified_json)
        except json.decoder.JSONDecodeError as e:
            raise DeserializationError(
                f'Could not decode processed accounting event json from the DB due to {str(e)}',
            ) from e

        try:
            pnl_taxable = deserialize_fval(data['pnl_taxable'], name='pnl_taxable', location='processed event decoding')  # noqa: E501
            pnl_free = deserialize_fval(data['pnl_free'], name='pnl_free', location='processed event decoding')  # noqa: E501
            if data['cost_basis'] is None:
                cost_basis = None
            else:
                cost_basis = CostBasisInfo.deserialize(data['cost_basis'])
            event = cls(
                type=AccountingEventType.deserialize(data['type']),
                notes=data['notes'],
                location=Location.deserialize(data['location']),
                timestamp=timestamp,
                asset=Asset(data['asset']).check_existence(),
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
            return event
        except KeyError as e:
            raise DeserializationError(f'Could not decode processed accounting event json from the DB due to missing key {str(e)}') from e  # noqa: E501
        except UnknownAsset as e:
            raise DeserializationError(f'Couldnt deserialize processed accounting event due to unkown asset {e.identifier}') from e  # noqa: E501
