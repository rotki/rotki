import logging
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional, Union, get_args

import marshmallow
import webargs
from eth_utils import to_checksum_address
from marshmallow import Schema, fields, post_load, validate, validates_schema
from marshmallow.exceptions import ValidationError

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.accounting.structures.base import HistoryBaseEntryType
from rotkehlchen.accounting.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.accounting.types import SchemaEventType
from rotkehlchen.assets.asset import Asset, AssetWithNameAndType, AssetWithOracles, CryptoAsset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.assets.utils import IgnoredAssetsHandling
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.bitcoin.bch.utils import validate_bch_address_input
from rotkehlchen.chain.bitcoin.hdkey import HDKey, XpubType
from rotkehlchen.chain.bitcoin.utils import is_valid_btc_address, scriptpubkey_to_btc_address
from rotkehlchen.chain.constants import NON_BITCOIN_CHAINS
from rotkehlchen.chain.ethereum.constants import ETHEREUM_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.evm.types import EvmAccount
from rotkehlchen.chain.optimism.constants import OPTIMISM_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.substrate.types import SubstrateAddress, SubstratePublicKey
from rotkehlchen.chain.substrate.utils import (
    get_substrate_address_from_public_key,
    is_valid_substrate_address,
)
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import EVM_CHAIN_DIRECTIVE
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    AssetsFilterQuery,
    CustomAssetsFilterQuery,
    Eth2DailyStatsFilterQuery,
    EthStakingEventFilterQuery,
    EvmEventFilterQuery,
    EvmTransactionsFilterQuery,
    HistoryEventFilterQuery,
    LedgerActionsFilterQuery,
    LevenshteinFilterQuery,
    NFTFilterQuery,
    ReportDataFilterQuery,
    TradesFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.misc import InputError, RemoteError, XPUBError
from rotkehlchen.errors.serialization import DeserializationError, EncodingError
from rotkehlchen.exchanges.constants import ALL_SUPPORTED_EXCHANGES, SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.icons import ALLOWED_ICON_EXTENSIONS
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    DEFAULT_ADDRESS_NAME_PRIORITY,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_LOCATIONS,
    NON_EVM_CHAINS,
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_SUBSTRATE_CHAINS,
    AddressbookEntry,
    AddressbookType,
    AssetMovementCategory,
    BTCAddress,
    ChecksumEvmAddress,
    CostBasisMethod,
    ExchangeLocationID,
    ExternalService,
    ExternalServiceApiCredentials,
    HistoryEventQueryType,
    Location,
    OptionalChainAddress,
    SupportedBlockchain,
    Timestamp,
    TradeType,
    UserNote,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import create_order_by_rules_list, ts_now

from .fields import (
    AmountField,
    ApiKeyField,
    ApiSecretField,
    AssetConflictsField,
    AssetField,
    BlockchainField,
    ColorField,
    CurrentPriceOracleField,
    DelimitedOrNormalList,
    DerivationPathField,
    DirectoryField,
    EvmAddressField,
    EvmChainNameField,
    EVMTransactionHashField,
    FeeField,
    FileField,
    FloatingPercentageField,
    HistoricalPriceOracleField,
    IncludeExcludeListField,
    LocationField,
    MaybeAssetField,
    NonEmptyList,
    PositiveAmountField,
    PriceField,
    SerializableEnumField,
    TaxFreeAfterPeriodField,
    TimestampField,
    TimestampUntilNowField,
    XpubField,
)
from .types import (
    EvmPendingTransactionDecodingApiData,
    IncludeExcludeFilterData,
    ModuleWithBalances,
    ModuleWithStats,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncQueryArgumentSchema(Schema):
    """A schema for getters that only have one argument enabling async query"""
    async_query = fields.Boolean(load_default=False)


class AsyncIgnoreCacheQueryArgumentSchema(AsyncQueryArgumentSchema):
    ignore_cache = fields.Boolean(load_default=False)


class TimestampRangeSchema(Schema):
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


class AsyncHistoricalQuerySchema(AsyncQueryArgumentSchema, TimestampRangeSchema):
    """A schema for getters that have 2 arguments.
    One to enable async querying and another to force reset DB data by querying everytying again"""
    reset_db_data = fields.Boolean(load_default=False)


class BalanceSchema(Schema):
    amount = AmountField(required=True)
    usd_value = AmountField(required=True)

    @post_load
    def make_balance_entry(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Balance:
        """Create a Balance struct. This should not raise since it's checked by Marshmallow"""
        return Balance(amount=data['amount'], usd_value=data['usd_value'])


class AsyncTasksQuerySchema(Schema):
    task_id = fields.Integer(strict=True, load_default=None)


class OnlyCacheQuerySchema(Schema):
    only_cache = fields.Boolean(load_default=False)


class DBPaginationSchema(Schema):
    limit = fields.Integer(load_default=None)
    offset = fields.Integer(load_default=None)


class DBOrderBySchema(Schema):
    order_by_attributes = DelimitedOrNormalList(fields.String(), load_default=None)
    ascending = DelimitedOrNormalList(fields.Boolean(), load_default=None)  # noqa: E501 most recent first by default

    @validates_schema
    def validate_order_by_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if (data['order_by_attributes'] is None) ^ (data['ascending'] is None):
            raise ValidationError(
                message='order_by_attributes and ascending have to be both null or have a value',
                field_name='order_by_attributes',
            )
        if (
            data['order_by_attributes'] is not None and
            len(data['order_by_attributes']) != len(data['ascending'])
        ):
            raise ValidationError(
                message="order_by_attributes and ascending don't have the same length",
                field_name='order_by_attributes',
            )


class RequiredEvmAddressOptionalChainSchema(Schema):
    address = EvmAddressField(required=True)
    evm_chain = EvmChainNameField(
        required=False,
        limit_to=get_args(SUPPORTED_CHAIN_IDS),  # type: ignore
        load_default=None,
    )

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        return EvmAccount(data['address'], chain_id=data['evm_chain'])


class EvmTransactionPurgingSchema(Schema):
    evm_chain = EvmChainNameField(required=False, load_default=None)


class EvmTransactionQuerySchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    accounts = fields.List(
        fields.Nested(RequiredEvmAddressOptionalChainSchema),
        load_default=None,
        validate=lambda data: len(data) != 0,
    )
    evm_chain = EvmChainNameField(required=False, load_default=None)

    @validates_schema
    def validate_evmtx_query_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        valid_ordering_attr = {None, 'timestamp'}
        if (
            data['order_by_attributes'] is not None and
            not set(data['order_by_attributes']).issubset(valid_ordering_attr)
        ):
            error_msg = (
                f'order_by_attributes for transactions can not be '
                f'{",".join(set(data["order_by_attributes"]) - valid_ordering_attr)}'
            )
            raise ValidationError(
                message=error_msg,
                field_name='order_by_attributes',
            )

        if (
            data['evm_chain'] is not None and
            data['evm_chain'] not in get_args(SUPPORTED_CHAIN_IDS)
        ):
            raise ValidationError(
                message=f'rotki does not support evm transactions for {data["evm_chain"]}',
                field_name='evm_chain',
            )

    @post_load
    def make_evm_transaction_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = EvmTransactionsFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,  # by default, descending order of time
                default_order_by_fields=['timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            accounts=data['accounts'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            chain_id=data['evm_chain'],
        )

        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
        }


class SingleEVMTransactionDecodingSchema(Schema):
    evm_chain = EvmChainNameField(required=True)
    tx_hashes = fields.List(EVMTransactionHashField(), load_default=None)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        tx_hashes = data.get('tx_hashes')
        if tx_hashes is not None and len(tx_hashes) == 0:
            raise ValidationError(
                message='Empty list of hashes is a noop. Did you mean to omit the list?',
                field_name='tx_hashes',
            )


class EventsOnlineQuerySchema(AsyncQueryArgumentSchema):
    query_type = SerializableEnumField(enum_class=HistoryEventQueryType, required=True)


class EvmTransactionDecodingSchema(AsyncIgnoreCacheQueryArgumentSchema):
    data = NonEmptyList(fields.Nested(SingleEVMTransactionDecodingSchema), required=True)


class SingleEvmPendingTransactionDecodingSchema(Schema):
    evm_chain = EvmChainNameField(required=True)
    addresses = fields.List(EvmAddressField(), load_default=None)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        addresses = data.get('addresses')
        if addresses is not None and len(addresses) == 0:
            raise ValidationError(
                message='Empty list of addresses is a noop. Did you mean to omit the list?',
                field_name='addresses',
            )


class EvmPendingTransactionDecodingSchema(AsyncQueryArgumentSchema):
    data = fields.List(fields.Nested(SingleEvmPendingTransactionDecodingSchema), required=True)

    @validates_schema
    def validate_schema(
            self,
            data: list[EvmPendingTransactionDecodingApiData],
            **_kwargs: Any,
    ) -> None:

        if len(data) == 0:
            raise ValidationError(
                message='The list of data should not be empty',
                field_name='data',
            )


class TradesQuerySchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    base_asset = AssetField(expected_type=Asset, load_default=None)
    quote_asset = AssetField(expected_type=Asset, load_default=None)
    trade_type = SerializableEnumField(enum_class=TradeType, load_default=None)
    location = LocationField(load_default=None)
    include_ignored_trades = fields.Boolean(load_default=True)

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__()
        self.db = db

    @validates_schema
    def validate_trades_query_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        valid_ordering_attr = {
            None,
            'timestamp',
            'location',
            'type',
            'amount',
            'rate',
            'fee',
        }
        if (
            data['order_by_attributes'] is not None and
            not set(data['order_by_attributes']).issubset(valid_ordering_attr)
        ):
            error_msg = (
                f'order_by_attributes for trades can not be '
                f'{",".join(set(data["order_by_attributes"]) - valid_ordering_attr)}'
            )
            raise ValidationError(
                message=error_msg,
                field_name='order_by_attributes',
            )

    @post_load
    def make_trades_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        base_assets: Optional[tuple[Asset, ...]] = None
        quote_assets: Optional[tuple[Asset, ...]] = None
        trades_idx_to_ignore = None
        with self.db.conn.read_ctx() as cursor:
            treat_eth2_as_eth = self.db.get_settings(cursor).treat_eth2_as_eth
            if data['include_ignored_trades'] is not True:
                ignored_action_ids = self.db.get_ignored_action_ids(cursor, ActionType.TRADE)
                trades_idx_to_ignore = ignored_action_ids[ActionType.TRADE]

        if data['base_asset'] is not None:
            base_assets = (data['base_asset'],)
        if data['quote_asset'] is not None:
            quote_assets = (data['quote_asset'],)

        if treat_eth2_as_eth is True and data['base_asset'] == A_ETH:
            base_assets = (A_ETH, A_ETH2)
        elif treat_eth2_as_eth is True and data['quote_asset'] == A_ETH:
            quote_assets = (A_ETH, A_ETH2)

        filter_query = TradesFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            base_assets=base_assets,
            quote_assets=quote_assets,
            trade_type=[data['trade_type']] if data['trade_type'] is not None else None,
            location=data['location'],
            trades_idx_to_ignore=trades_idx_to_ignore,
        )

        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
            'include_ignored_trades': data['include_ignored_trades'],
        }


class BaseStakingQuerySchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    asset = AssetField(expected_type=AssetWithOracles, load_default=None)

    def _get_assets_list(
            self,
            data: dict[str, Any],
    ) -> Optional[tuple['AssetWithOracles', ...]]:
        return (data['asset'],) if data['asset'] is not None else None

    def _make_query(
            self,
            location: Location,
            data: dict[str, Any],
            event_types: list[HistoryEventType],
            value_event_subtypes: list[HistoryEventSubType],
            query_event_subtypes: Optional[list[HistoryEventSubType]] = None,
            exclude_event_subtypes: Optional[list[HistoryEventSubType]] = None,
    ) -> dict[str, Any]:
        if data['order_by_attributes'] is not None:
            attributes = []
            for order_by_attribute in data['order_by_attributes']:
                if order_by_attribute == 'event_type':
                    attributes.append('subtype')
                else:
                    attributes.append(order_by_attribute)
            data['order_by_attributes'] = attributes

        asset_list = self._get_assets_list(data)
        query_filter = HistoryEventFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            location=location,
            event_types=event_types,
            event_subtypes=query_event_subtypes,
            exclude_subtypes=exclude_event_subtypes,
            assets=asset_list,
            entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]),
        )

        value_filter = HistoryEventFilterQuery.make(
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            location=location,
            event_types=event_types,
            event_subtypes=value_event_subtypes,
            order_by_rules=None,
            assets=asset_list,
            entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.HISTORY_EVENT]),
        )

        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'query_filter': query_filter,
            'value_filter': value_filter,
        }


class StakingQuerySchema(BaseStakingQuerySchema):
    event_subtypes = fields.List(
        SerializableEnumField(enum_class=HistoryEventSubType),
        load_default=None,
    )

    def __init__(
            self,
            treat_eth2_as_eth: bool,
    ) -> None:
        super().__init__()
        self.treat_eth2_as_eth = treat_eth2_as_eth

    def _get_assets_list(
            self,
            data: dict[str, Any],
    ) -> Optional[tuple['AssetWithOracles', ...]]:
        asset_list = super()._get_assets_list(data)
        if self.treat_eth2_as_eth is True and data['asset'] == A_ETH:
            asset_list = (
                A_ETH.resolve_to_asset_with_oracles(),
                A_ETH2.resolve_to_asset_with_oracles(),
            )
        return asset_list

    @post_load
    def make_staking_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        return self._make_query(
            data=data,
            location=Location.KRAKEN,
            event_types=[HistoryEventType.STAKING],
            query_event_subtypes=data['event_subtypes'],
            value_event_subtypes=[HistoryEventSubType.REWARD],
            exclude_event_subtypes=[
                HistoryEventSubType.RECEIVE_WRAPPED,
                HistoryEventSubType.RETURN_WRAPPED,
            ],
        )


class HistoryEventSchema(TimestampRangeSchema, DBPaginationSchema, DBOrderBySchema):
    """Schema for quering history events"""
    exclude_ignored_assets = fields.Boolean(load_default=True)
    group_by_event_ids = fields.Boolean(load_default=False)
    event_identifiers = DelimitedOrNormalList(fields.String(), load_default=None)
    event_types = DelimitedOrNormalList(
        SerializableEnumField(enum_class=HistoryEventType),
        load_default=None,
    )
    event_subtypes = DelimitedOrNormalList(
        SerializableEnumField(enum_class=HistoryEventSubType),
        load_default=None,
    )
    location = SerializableEnumField(Location, load_default=None)
    location_labels = DelimitedOrNormalList(fields.String(), load_default=None)
    asset = AssetField(expected_type=CryptoAsset, load_default=None)
    entry_types = IncludeExcludeListField(
        SerializableEnumField(enum_class=HistoryBaseEntryType),
        load_default=None,
    )

    # EvmEvent only
    tx_hashes = DelimitedOrNormalList(EVMTransactionHashField(), load_default=None)
    counterparties = DelimitedOrNormalList(fields.String(), load_default=None)
    products = DelimitedOrNormalList(SerializableEnumField(enum_class=EvmProduct), load_default=None)  # noqa: E501
    addresses = DelimitedOrNormalList(EvmAddressField(), load_default=None)

    # EthStakingEvent only
    validator_indices = DelimitedOrNormalList(fields.Integer(), load_default=None)

    @validates_schema
    def validate_history_event_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        valid_ordering_attr = {None, 'timestamp'}
        if (
            data['order_by_attributes'] is not None and
            not set(data['order_by_attributes']).issubset(valid_ordering_attr)
        ):
            error_msg = (
                f'order_by_attributes for history event data can not be '
                f'{",".join(set(data["order_by_attributes"]) - valid_ordering_attr)}'
            )
            raise ValidationError(
                message=error_msg,
                field_name='order_by_attributes',
            )

    @post_load
    def make_history_event_filter(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        should_query_eth_staking_event = data['validator_indices'] is not None
        should_query_evm_event = any(data[x] is not None for x in ('products', 'counterparties', 'tx_hashes', 'addresses'))  # noqa: E501
        counterparties = data['counterparties']
        entry_types = data['entry_types']
        if counterparties is not None and CPT_ETH2 in counterparties:
            if len(counterparties) != 1:
                raise ValidationError(
                    message='Filtering by counterparty ETH2 does not work in combination with other counterparties',  # noqa: E501
                    field_name='counterparties',
                )
            if entry_types is not None:
                raise ValidationError(
                    message='Filtering by counterparty ETH2 does not work in combination with entry type',  # noqa: E501
                    field_name='counterparties',
                )
            for x in ('products', 'tx_hashes'):
                if data[x] is not None:
                    raise ValidationError(
                        message=f'Filtering by counterparty ETH2 does not work in combination with filtering by {x}',  # noqa: E501
                        field_name='counterparties',
                    )

            counterparties = None
            entry_type_values = [
                HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT,
                HistoryBaseEntryType.ETH_BLOCK_EVENT,
                HistoryBaseEntryType.ETH_DEPOSIT_EVENT,
            ]
            entry_types = IncludeExcludeFilterData(
                values=entry_type_values,
                operator='IN',
            )
            should_query_eth_staking_event = True
            should_query_evm_event = False

        common_arguments = self.make_extra_filtering_arguments(data) | {
            'order_by_rules': create_order_by_rules_list(
                data=data,  # descending timestamp and ascending sequence index
                default_order_by_fields=['timestamp', 'sequence_index'],
                default_ascending=[False, True],
            ),
            'entry_types': entry_types,
            'from_ts': data['from_timestamp'],
            'to_ts': data['to_timestamp'],
            'exclude_ignored_assets': data['exclude_ignored_assets'],
            'event_identifiers': data['event_identifiers'],
            'location_labels': data['location_labels'],
            'assets': [data['asset']] if data['asset'] is not None else None,
            'event_types': data['event_types'],
            'event_subtypes': data['event_subtypes'],
            'location': data['location'],
        }

        filter_query: Union[HistoryEventFilterQuery, EvmEventFilterQuery, EthStakingEventFilterQuery]  # noqa: E501
        if should_query_evm_event:
            filter_query = EvmEventFilterQuery.make(
                **common_arguments,
                tx_hashes=data['tx_hashes'],
                products=data['products'],
                addresses=data['addresses'],
                counterparties=counterparties,
            )
        elif should_query_eth_staking_event:
            filter_query = EthStakingEventFilterQuery.make(
                **common_arguments,
                validator_indices=data['validator_indices'],
            )
        else:
            filter_query = HistoryEventFilterQuery.make(**common_arguments)

        return self.generate_fields_post_validation(data) | {
            'filter_query': filter_query,
        }

    def make_extra_filtering_arguments(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generates the extra fields to be included in the filter_query dictionary"""
        return {
            'limit': data['limit'],
            'offset': data['offset'],
        }

    def generate_fields_post_validation(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generates extra fields that will be returned after validation"""
        return {'group_by_event_ids': data['group_by_event_ids']}


class EvmEventSchema(Schema):
    """Schema used when adding a new event in the EVM transactions view"""
    tx_hash = EVMTransactionHashField(required=True)
    sequence_index = fields.Integer(required=True)
    # Timestamp coming in from the API is in seconds, in contrast to what we save in the struct
    timestamp = TimestampField(ts_multiplier=1000, required=True)
    location = LocationField(required=True)
    event_type = SerializableEnumField(enum_class=HistoryEventType, required=True)
    asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)
    balance = fields.Nested(BalanceSchema, required=True)
    location_label = fields.String(required=False)
    notes = fields.String(required=False)
    event_subtype = SerializableEnumField(
        enum_class=HistoryEventSubType,
        required=False,
        load_default=HistoryEventSubType.NONE,
        allow_none=True,
    )
    counterparty = fields.String(load_default=None)
    product = SerializableEnumField(enum_class=EvmProduct, load_default=None)
    address = EvmAddressField(load_default=None)

    @post_load
    def make_history_base_entry(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        if data.get('event_subtype', None) is None:
            data['event_subtype'] = HistoryEventSubType.NONE

        if data['location'] not in EVM_LOCATIONS:
            raise ValidationError(
                message=f'EVM event location needs to be one of {EVM_LOCATIONS}',
                field_name='location',
            )

        return {'event': EvmEvent(**data)}


class EditEvmEventSchema(EvmEventSchema):
    """Schema used when editing an existing event in the EVM transactions view"""
    identifier = fields.Integer(required=True)


class AssetMovementsQuerySchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    asset = AssetField(expected_type=Asset, load_default=None)
    action = SerializableEnumField(enum_class=AssetMovementCategory, load_default=None)
    location = LocationField(load_default=None)

    def __init__(
            self,
            treat_eth2_as_eth: bool,
    ) -> None:
        super().__init__()
        self.treat_eth2_as_eth = treat_eth2_as_eth

    @validates_schema
    def validate_asset_movements_query_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        valid_ordering_attr = {
            None,
            'timestamp',
            'location',
            'category',
            'amount',
            'fee',
        }
        if (
            data['order_by_attributes'] is not None and
            not set(data['order_by_attributes']).issubset(valid_ordering_attr)
        ):
            error_msg = (
                f'order_by_attributes for asset movements can not be '
                f'{",".join(set(data["order_by_attributes"]) - valid_ordering_attr)}'
            )
            raise ValidationError(
                message=error_msg,
                field_name='order_by_attributes',
            )

    @post_load
    def make_asset_movements_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        asset_list: Optional[tuple[Asset, ...]] = None
        if data['asset'] is not None:
            asset_list = (data['asset'],)
        if self.treat_eth2_as_eth is True and data['asset'] == A_ETH:
            asset_list = (A_ETH, A_ETH2)

        filter_query = AssetMovementsFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            assets=asset_list,
            action=[data['action']] if data['action'] is not None else None,
            location=data['location'],
        )
        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
        }


class LedgerActionsQuerySchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    asset = AssetField(expected_type=Asset, load_default=None)
    type = SerializableEnumField(enum_class=LedgerActionType, load_default=None)
    location = LocationField(load_default=None)

    def __init__(
            self,
            treat_eth2_as_eth: bool,
    ) -> None:
        super().__init__()
        self.treat_eth2_as_eth = treat_eth2_as_eth

    @validates_schema
    def validate_ledger_action_query_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        valid_ordering_attr = {
            None,
            'timestamp',
            'type',
            'location',
            'amount',
            'rate',
        }
        if (
            data['order_by_attributes'] is not None and
            not set(data['order_by_attributes']).issubset(valid_ordering_attr)
        ):
            error_msg = (
                f'order_by_attributes for ledger actions can not be '
                f'{",".join(set(data["order_by_attributes"]) - valid_ordering_attr)}'
            )
            raise ValidationError(
                message=error_msg,
                field_name='order_by_attributes',
            )

    @post_load
    def make_ledger_actions_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        asset_list: Optional[tuple[Asset, ...]] = None
        if data['asset'] is not None:
            asset_list = (data['asset'],)
        if self.treat_eth2_as_eth is True and data['asset'] == A_ETH:
            asset_list = (A_ETH, A_ETH2)

        filter_query = LedgerActionsFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            assets=asset_list,
            action_type=[data['type']] if data['type'] is not None else None,
            location=data['location'],
        )
        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
        }


class TradeSchema(Schema):
    timestamp = TimestampUntilNowField(required=True)
    location = LocationField(required=True)
    base_asset = AssetField(expected_type=Asset, required=True)
    quote_asset = AssetField(expected_type=Asset, required=True)
    trade_type = SerializableEnumField(enum_class=TradeType, required=True)
    amount = PositiveAmountField(required=True)
    rate = PriceField(required=True)
    fee = FeeField(load_default=None)
    fee_currency = AssetField(expected_type=Asset, load_default=None)
    link = fields.String(load_default=None)
    notes = fields.String(load_default=None)

    @validates_schema
    def validate_trade(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        """This validation checks that fee_currency is provided whenever fee is given and
        vice versa. It also checks that fee is not a zero value when both fee and
        fee_currency are provided. Also checks that the trade rate is not zero.
        Negative rate is checked by price field.
        """
        fee = data.get('fee')
        fee_currency = data.get('fee_currency')

        if not all([fee, fee_currency]) and any([fee, fee_currency]):
            raise ValidationError('fee and fee_currency must be provided', field_name='fee')

        if fee is not None and fee == ZERO:
            raise ValidationError('fee cannot be zero', field_name='fee')

        if data['rate'] == ZERO:
            raise ValidationError('A zero rate is not allowed', field_name='rate')


class LedgerActionSchema(Schema):
    identifier = fields.Integer(load_default=None, required=False)
    timestamp = TimestampUntilNowField(required=True)
    action_type = SerializableEnumField(enum_class=LedgerActionType, required=True)
    location = LocationField(required=True)
    amount = AmountField(required=True)
    asset = AssetField(expected_type=Asset, required=True)
    rate = PriceField(load_default=None)
    rate_asset = AssetField(expected_type=Asset, load_default=None)
    link = fields.String(load_default=None)
    notes = fields.String(load_default=None)

    def __init__(self, identifier_required: bool):
        super().__init__()
        self.identifier_required = identifier_required

    @validates_schema
    def validate_ledger_action_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.identifier_required is True and data['identifier'] is None:
            raise ValidationError(
                message='Ledger action identifier should be given',
                field_name='identifier',
            )

    @post_load(pass_many=True)
    def make_ledger_action(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, LedgerAction]:
        return {'action': LedgerAction(**data)}


class IntegerIdentifierListSchema(Schema):
    identifiers = DelimitedOrNormalList(fields.Integer(required=True), required=True)


class IntegerIdentifierSchema(Schema):
    identifier = fields.Integer(required=True)


class StringIdentifierSchema(Schema):
    identifier = fields.String(required=True)


class TagsSettingSchema(Schema):
    tags = fields.List(fields.String(), load_default=None)

    @validates_schema
    def validate_tags(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if isinstance(data['tags'], list) and len(data['tags']) == 0:
            raise ValidationError(
                message='Provided empty list for tags. Use null.',
                field_name='tags',
            )


class ManuallyTrackedBalanceAddSchema(TagsSettingSchema):
    asset = AssetField(expected_type=Asset, required=True)
    label = fields.String(required=True)
    amount = PositiveAmountField(required=True)
    location = LocationField(required=True)
    balance_type = SerializableEnumField(enum_class=BalanceType, load_default=BalanceType.ASSET)

    @post_load
    def make_manually_tracked_balances(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> ManuallyTrackedBalance:
        data['id'] = -1  # can be any value because id will be set automatically
        return ManuallyTrackedBalance(**data)


class ManuallyTrackedBalanceEditSchema(ManuallyTrackedBalanceAddSchema):
    id = fields.Integer(required=True)

    @post_load
    def make_manually_tracked_balances(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> ManuallyTrackedBalance:
        return ManuallyTrackedBalance(**data)


class ManuallyTrackedBalancesAddSchema(AsyncQueryArgumentSchema):
    balances = fields.List(fields.Nested(ManuallyTrackedBalanceAddSchema), required=True)


class ManuallyTrackedBalancesEditSchema(AsyncQueryArgumentSchema):
    balances = fields.List(fields.Nested(ManuallyTrackedBalanceEditSchema), required=True)


class ManuallyTrackedBalancesDeleteSchema(AsyncQueryArgumentSchema):
    ids = fields.List(fields.Integer(required=True), required=True)


class TradePatchSchema(TradeSchema):
    trade_id = fields.String(required=True)


class TradeDeleteSchema(Schema):
    trades_ids = DelimitedOrNormalList(fields.String(required=True), required=True)


class TagSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(load_default=None)
    background_color = ColorField(required=False, load_default=None)
    foreground_color = ColorField(required=False, load_default=None)

    def __init__(self, color_required: bool):
        super().__init__()
        self.color_required = color_required

    @validates_schema
    def validate_tag_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.color_required is True and None in (data['background_color'], data['foreground_color']):  # noqa: E501
            raise ValidationError(
                message='Background and foreground color should be given for the tag',
                field_name='background_color',
            )


class NameDeleteSchema(Schema):
    name = fields.String(required=True)


def _validate_current_price_oracles(
        current_price_oracles: list[CurrentPriceOracle],
) -> None:
    """Prevents repeated oracle names and empty list"""
    if (
        len(current_price_oracles) == 0 or
        len(current_price_oracles) != len(set(current_price_oracles))
    ):
        oracle_names = [str(oracle) for oracle in current_price_oracles]
        supported_oracle_names = [str(oracle) for oracle in CurrentPriceOracle]
        raise ValidationError(
            f'Invalid current price oracles in: {", ".join(oracle_names)}. '
            f'Supported oracles are: {", ".join(supported_oracle_names)}. '
            f'Check there are no repeated ones.',
        )


def _validate_historical_price_oracles(
        historical_price_oracles: list[HistoricalPriceOracle],
) -> None:
    """Prevents repeated oracle names and empty list"""
    if (
        len(historical_price_oracles) == 0 or
        len(historical_price_oracles) != len(set(historical_price_oracles))
    ):
        oracle_names = [str(oracle) for oracle in historical_price_oracles]
        supported_oracle_names = [str(oracle) for oracle in HistoricalPriceOracle]
        raise ValidationError(
            f'Invalid historical price oracles in: {", ".join(oracle_names)}. '
            f'Supported oracles are: {", ".join(supported_oracle_names)}. '
            f'Check there are no repeated ones.',
        )


class ExchangeLocationIDSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(required=True)

    @post_load()
    def make_exchange_location_id(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> ExchangeLocationID:
        return ExchangeLocationID(name=data['name'], location=data['location'])


class ModifiableSettingsSchema(Schema):
    """This is the Schema for the settings that can be modified via the API"""
    premium_should_sync = fields.Bool(load_default=None)
    include_crypto2crypto = fields.Bool(load_default=None)
    submit_usage_analytics = fields.Bool(load_default=None)
    treat_eth2_as_eth = fields.Bool(load_default=None)
    ui_floating_precision = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            max=8,
            error='Floating numbers precision in the UI must be between 0 and 8',
        ),
        load_default=None,
    )
    taxfree_after_period = TaxFreeAfterPeriodField(load_default=None)
    balance_save_frequency = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=1,
            error='The number of hours after which balances should be saved should be >= 1',
        ),
        load_default=None,
    )
    include_gas_costs = fields.Bool(load_default=None)
    # TODO: Add some validation to this field
    # even though it gets validated since we try to connect to it
    ksm_rpc_endpoint = fields.String(load_default=None)
    dot_rpc_endpoint = fields.String(load_default=None)
    main_currency = AssetField(expected_type=AssetWithOracles, load_default=None)
    # TODO: Add some validation to this field
    date_display_format = fields.String(load_default=None)
    active_modules = fields.List(fields.String(), load_default=None)
    frontend_settings = fields.String(load_default=None)
    account_for_assets_movements = fields.Bool(load_default=None)
    btc_derivation_gap_limit = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=1,
            error='The bitcoin address derivation gap limit should be >= 1',
        ),
        load_default=None,
    )
    calculate_past_cost_basis = fields.Bool(load_default=None)
    display_date_in_localtime = fields.Bool(load_default=None)
    current_price_oracles = fields.List(
        CurrentPriceOracleField,
        validate=_validate_current_price_oracles,
        load_default=None,
    )
    historical_price_oracles = fields.List(
        HistoricalPriceOracleField,
        validate=_validate_historical_price_oracles,
        load_default=None,
    )
    taxable_ledger_actions = fields.List(
        SerializableEnumField(enum_class=LedgerActionType),
        load_default=None,
    )
    pnl_csv_with_formulas = fields.Bool(load_default=None)
    pnl_csv_have_summary = fields.Bool(load_default=None)
    ssf_graph_multiplier = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            error='The snapshot saving frequency zero graph multiplier should be >= 0',
        ),
        load_default=None,
    )
    non_syncing_exchanges = fields.List(
        fields.Nested(ExchangeLocationIDSchema),
        load_default=None,
        # Check that all values are unique
        validate=lambda data: len(data) == len(set(data)),
    )
    cost_basis_method = SerializableEnumField(enum_class=CostBasisMethod, load_default=None)
    eth_staking_taxable_after_withdrawal_enabled = fields.Boolean(load_default=None)
    address_name_priority = fields.List(fields.String(
        validate=webargs.validate.OneOf(choices=DEFAULT_ADDRESS_NAME_PRIORITY),
    ), load_default=DEFAULT_ADDRESS_NAME_PRIORITY)
    include_fees_in_cost_basis = fields.Boolean(load_default=None)
    infer_zero_timed_balances = fields.Boolean(load_default=None)
    query_retry_limit = fields.Integer(
        validate=webargs.validate.Range(
            min=1,
            error='The query retry limit should be > 0 retries',
        ),
        load_default=None,
    )
    connect_timeout = fields.Integer(
        validate=webargs.validate.Range(
            min=1,
            error='The connect timeout should be > 0 seconds',
        ),
        load_default=None,
    )
    read_timeout = fields.Integer(
        validate=webargs.validate.Range(
            min=1,
            error='The read timeout should be > 0 seconds',
        ),
        load_default=None,
    )

    @validates_schema
    def validate_settings_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['active_modules'] is not None:
            for module in data['active_modules']:
                if module not in AVAILABLE_MODULES_MAP:
                    raise ValidationError(
                        message=f'{module} is not a valid module',
                        field_name='active_modules',
                    )

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        return ModifiableDBSettings(
            premium_should_sync=data['premium_should_sync'],
            include_crypto2crypto=data['include_crypto2crypto'],
            ui_floating_precision=data['ui_floating_precision'],
            taxfree_after_period=data['taxfree_after_period'],
            balance_save_frequency=data['balance_save_frequency'],
            include_gas_costs=data['include_gas_costs'],
            ksm_rpc_endpoint=data['ksm_rpc_endpoint'],
            dot_rpc_endpoint=data['dot_rpc_endpoint'],
            main_currency=data['main_currency'],
            date_display_format=data['date_display_format'],
            submit_usage_analytics=data['submit_usage_analytics'],
            active_modules=data['active_modules'],
            frontend_settings=data['frontend_settings'],
            account_for_assets_movements=data['account_for_assets_movements'],
            btc_derivation_gap_limit=data['btc_derivation_gap_limit'],
            calculate_past_cost_basis=data['calculate_past_cost_basis'],
            display_date_in_localtime=data['display_date_in_localtime'],
            historical_price_oracles=data['historical_price_oracles'],
            current_price_oracles=data['current_price_oracles'],
            taxable_ledger_actions=data['taxable_ledger_actions'],
            pnl_csv_with_formulas=data['pnl_csv_with_formulas'],
            pnl_csv_have_summary=data['pnl_csv_have_summary'],
            ssf_graph_multiplier=data['ssf_graph_multiplier'],
            non_syncing_exchanges=data['non_syncing_exchanges'],
            cost_basis_method=data['cost_basis_method'],
            treat_eth2_as_eth=data['treat_eth2_as_eth'],
            eth_staking_taxable_after_withdrawal_enabled=data['eth_staking_taxable_after_withdrawal_enabled'],  # noqa: E501
            address_name_priority=data['address_name_priority'],
            include_fees_in_cost_basis=data['include_fees_in_cost_basis'],
            infer_zero_timed_balances=data['infer_zero_timed_balances'],
            query_retry_limit=data['query_retry_limit'],
            connect_timeout=data['connect_timeout'],
            read_timeout=data['read_timeout'],
        )


class EditSettingsSchema(Schema):
    settings = fields.Nested(ModifiableSettingsSchema, required=True)


class BaseUserSchema(Schema):
    name = fields.String(required=True)
    password = fields.String(required=True)


class UserActionSchema(Schema):
    name = fields.String(required=True)
    action = fields.String(
        validate=webargs.validate.Equal('logout'),
        load_default=None,
    )
    premium_api_key = fields.String(load_default='')
    premium_api_secret = fields.String(load_default='')

    @validates_schema
    def validate_user_action_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['action'] is None and (data['premium_api_key'] == '' or data['premium_api_secret'] == ''):  # noqa: E501
            raise ValidationError(
                'Without an action premium api key and secret must be provided',
            )


class UserActionLoginSchema(AsyncQueryArgumentSchema):
    name = fields.String(required=True)
    password = fields.String(required=True)
    sync_approval = fields.String(
        load_default='unknown',
        validate=webargs.validate.OneOf(choices=('unknown', 'yes', 'no')),
    )
    resume_from_backup = fields.Boolean(load_default=False)


class UserPasswordChangeSchema(Schema):
    name = fields.String(required=True)
    current_password = fields.String(required=True)
    new_password = fields.String(required=True)


class UserPremiumSyncSchema(AsyncQueryArgumentSchema):
    action = fields.String(
        validate=webargs.validate.OneOf(choices=('upload', 'download')),
        required=True,
    )


class NewUserSchema(BaseUserSchema, AsyncQueryArgumentSchema):
    premium_api_key = fields.String(load_default='')
    premium_api_secret = fields.String(load_default='')
    sync_database = fields.Boolean(load_default=True)
    initial_settings = fields.Nested(ModifiableSettingsSchema, load_default=None)


class AllBalancesQuerySchema(AsyncQueryArgumentSchema):
    save_data = fields.Boolean(load_default=False)
    ignore_errors = fields.Boolean(load_default=False)
    ignore_cache = fields.Boolean(load_default=False)


class ExternalServiceSchema(Schema):
    name = SerializableEnumField(enum_class=ExternalService, required=True)
    api_key = fields.String(required=True)

    @post_load
    def make_external_service(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> ExternalServiceApiCredentials:
        """Used when encoding an external resource given in via the API"""
        return ExternalServiceApiCredentials(service=data['name'], api_key=data['api_key'])


class ExternalServicesResourceAddSchema(Schema):
    services = fields.List(fields.Nested(ExternalServiceSchema), required=True)


class ExternalServicesResourceDeleteSchema(Schema):
    services = fields.List(SerializableEnumField(enum_class=ExternalService), required=True)


class ExchangesResourceEditSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)
    new_name = fields.String(load_default=None)
    api_key = ApiKeyField(load_default=None)
    api_secret = ApiSecretField(load_default=None)
    passphrase = fields.String(load_default=None)
    kraken_account_type = SerializableEnumField(enum_class=KrakenAccountType, load_default=None)
    binance_markets = fields.List(fields.String(), load_default=None)


class ExchangesResourceAddSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)
    api_key = ApiKeyField(required=True)
    api_secret = ApiSecretField(required=True)
    passphrase = fields.String(load_default=None)
    kraken_account_type = SerializableEnumField(enum_class=KrakenAccountType, load_default=None)
    binance_markets = fields.List(fields.String(), load_default=None)


class ExchangesDataResourceSchema(Schema):
    location = LocationField(limit_to=ALL_SUPPORTED_EXCHANGES, load_default=None)


class ExchangesResourceRemoveSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)


class ExchangeBalanceQuerySchema(AsyncQueryArgumentSchema):
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, load_default=None)
    ignore_cache = fields.Boolean(load_default=False)


class BlockchainBalanceQuerySchema(AsyncQueryArgumentSchema):
    blockchain = BlockchainField(load_default=None)
    ignore_cache = fields.Boolean(load_default=False)


class StatisticsAssetBalanceSchema(TimestampRangeSchema):
    asset = AssetField(expected_type=Asset, load_default=None)
    collection_id = fields.Integer(load_default=None)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        asset = data.get('asset')
        collection_id = data.get('collection_id')

        if asset is None and collection_id is None:
            raise ValidationError(
                message='Need to either provide an asset or a collection_id',
                field_name='asset',
            )

        if asset is not None and collection_id is not None:
            raise ValidationError(
                message="Can't provide both an asset and a collection_id",
                field_name='collection_id',
            )


class StatisticsValueDistributionSchema(Schema):
    distribution_by = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=('location', 'asset')),
    )


class HistoryProcessingSchema(AsyncQueryArgumentSchema, TimestampRangeSchema):
    """Schema for history processing"""


class ModuleBalanceProcessingSchema(AsyncQueryArgumentSchema):
    module = SerializableEnumField(enum_class=ModuleWithBalances, required=True)


class ModuleBalanceWithVersionProcessingSchema(ModuleBalanceProcessingSchema):
    version = fields.Integer()


class ModuleHistoryProcessingSchema(HistoryProcessingSchema):
    module = SerializableEnumField(enum_class=ModuleWithStats, required=True)


class HistoryProcessingExportSchema(HistoryProcessingSchema):
    directory_path = DirectoryField(load_default=None)


class HistoryProcessingDebugImportSchema(AsyncQueryArgumentSchema):
    filepath = FileField(required=True, allowed_extensions=['.json'])


class AccountingReportsSchema(Schema):
    report_id = fields.Integer(load_default=None)

    def __init__(self, required_report_id: bool):
        super().__init__()
        self.required_report_id = required_report_id

    @validates_schema
    def validate_accounting_reports_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.required_report_id and data['report_id'] is None:
            raise ValidationError('A report id should be given')


class AccountingReportDataSchema(TimestampRangeSchema, DBPaginationSchema, DBOrderBySchema):
    report_id = fields.Integer(load_default=None)
    event_type = SerializableEnumField(enum_class=SchemaEventType, load_default=None)

    @validates_schema
    def validate_report_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        valid_ordering_attr = {None, 'timestamp'}
        if (
            data['order_by_attributes'] is not None and
            not set(data['order_by_attributes']).issubset(valid_ordering_attr)
        ):
            error_msg = (
                f'order_by_attributes for accounting report data can not be '
                f'{",".join(set(data["order_by_attributes"]) - valid_ordering_attr)}'
            )
            raise ValidationError(
                message=error_msg,
                field_name='order_by_attributes',
            )

    @post_load
    def make_report_data_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        report_id = data.get('report_id')
        event_type = data.get('event_type')
        filter_query = ReportDataFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            report_id=report_id,
            event_type=event_type,
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
        )
        return {
            'filter_query': filter_query,
        }


class HistoryExportingSchema(Schema):
    directory_path = DirectoryField(required=True)


class BlockchainAccountDataSchema(TagsSettingSchema):
    address = fields.String(required=True)
    label = fields.String(load_default=None)

    @validates_schema
    def validate_blockchain_account_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        label = data.get('label', None)
        if label == '':
            raise ValidationError("Blockchain account's label cannot be empty string. Use null instead.")  # noqa: E501


class BaseXpubSchema(AsyncQueryArgumentSchema):
    xpub = XpubField(required=True)
    blockchain = BlockchainField(
        required=True,
        exclude_types=NON_BITCOIN_CHAINS,
    )
    derivation_path = DerivationPathField(load_default=None)


class XpubAddSchema(AsyncQueryArgumentSchema, TagsSettingSchema):
    xpub = fields.String(required=True)
    derivation_path = DerivationPathField(load_default=None)
    label = fields.String(load_default=None)
    blockchain = BlockchainField(
        required=True,
        exclude_types=NON_BITCOIN_CHAINS,
    )
    xpub_type = SerializableEnumField(XpubType, load_default=None)

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        xpub_type = data.pop('xpub_type', None)
        try:
            derivation_path = 'm' if data['derivation_path'] is None else data['derivation_path']
            xpub_hdkey = HDKey.from_xpub(data['xpub'], xpub_type=xpub_type, path=derivation_path)
        except XPUBError as e:
            raise ValidationError(
                f'Failed to initialize an xpub due to {e!s}',
                field_name='xpub',
            ) from e

        data['xpub'] = xpub_hdkey
        return data


class XpubPatchSchema(TagsSettingSchema):
    xpub = XpubField(required=True)
    derivation_path = DerivationPathField(load_default=None)
    label = fields.String(load_default=None)
    blockchain = BlockchainField(
        required=True,
        exclude_types=NON_BITCOIN_CHAINS,
    )


class BlockchainAccountsGetSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501


def _validate_blockchain_account_schemas(
        data: dict[str, Any],
        address_getter: Callable,
) -> None:
    """Validates schema input for the PUT/PATCH/DELETE on blockchain account data"""
    # Make sure no duplicates addresses are given
    given_addresses = set()
    chain = data['blockchain']
    # Make sure EVM based addresses are checksummed
    if chain.is_evm():
        for account_data in data['accounts']:
            address_string = address_getter(account_data)
            if not address_string.endswith('.eth'):
                # Make sure that given value is an ethereum address
                try:
                    address = to_checksum_address(address_string)
                except (ValueError, TypeError) as e:
                    raise ValidationError(
                        f'Given value {address_string} is not an evm address',
                        field_name='address',
                    ) from e
            else:
                # else it's ENS name and will be checked in the transformation step and not here
                address = address_string

            if address in given_addresses:
                raise ValidationError(
                    f'Address {address} appears multiple times in the request data',
                    field_name='address',
                )
            given_addresses.add(address)

    # Make sure bitcoin addresses are valid
    elif chain == SupportedBlockchain.BITCOIN:
        for account_data in data['accounts']:
            address = address_getter(account_data)
            # ENS domain will be checked in the transformation step
            if not address.endswith('.eth') and not is_valid_btc_address(address):
                raise ValidationError(
                    f'Given value {address} is not a valid bitcoin address',
                    field_name='address',
                )
            if address in given_addresses:
                raise ValidationError(
                    f'Address {address} appears multiple times in the request data',
                    field_name='address',
                )
            given_addresses.add(address)

    # Make sure bitcoin cash addresses are valid
    elif chain == SupportedBlockchain.BITCOIN_CASH:
        for account_data in data['accounts']:
            address = address_getter(account_data)
            validate_bch_address_input(address, given_addresses)
            given_addresses.add(address)

    # Make sure substrate addresses are valid (either ss58 format or ENS domain)
    elif chain.is_substrate():
        for account_data in data['accounts']:
            address = address_getter(account_data)
            # ENS domain will be checked in the transformation step
            if not address.endswith('.eth') and not is_valid_substrate_address(chain, address):
                raise ValidationError(
                    f'Given value {address} is not a valid {chain} address',
                    field_name='address',
                )
            if address in given_addresses:
                raise ValidationError(
                    f'Address {address} appears multiple times in the request data',
                    field_name='address',
                )
            given_addresses.add(address)


def _transform_btc_or_bch_address(
        ethereum_inquirer: EthereumInquirer,
        given_address: str,
        blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
) -> BTCAddress:
    """Returns a SegWit/P2PKH/P2SH address (if existing) given an ENS domain.

    NB: ENS domains for BTC store the scriptpubkey. Check EIP-2304.
    """
    if not given_address.endswith('.eth'):
        return BTCAddress(given_address)

    try:
        resolved_address = ethereum_inquirer.ens_lookup(
            given_address,
            blockchain=blockchain,
        )
    except (RemoteError, InputError) as e:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved '
            f'for {blockchain!s} due to: {e!s}',
            field_name='address',
        ) from None

    if resolved_address is None:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved for {blockchain.value}',
            field_name='address',
        ) from None

    try:
        address = scriptpubkey_to_btc_address(bytes.fromhex(resolved_address))
    except EncodingError as e:
        raise ValidationError(
            f'Given ENS address {given_address} does not contain a valid {blockchain!s} '
            f"scriptpubkey: {resolved_address}. {blockchain!s} address can't be obtained.",
            field_name='address',
        ) from e

    log.debug(f'Resolved {blockchain!s} ENS {given_address} to {address}')

    return address


def _transform_evm_address(
        ethereum_inquirer: EthereumInquirer,
        given_address: str,
) -> ChecksumEvmAddress:
    try:
        address = to_checksum_address(given_address)
    except ValueError:
        # Validation will only let .eth names come here.
        # So let's see if it resolves to anything
        try:
            resolved_address = ethereum_inquirer.ens_lookup(given_address)
        except (RemoteError, InputError) as e:
            raise ValidationError(
                f'Given ENS address {given_address} could not be resolved for Ethereum'
                f' due to: {e!s}',
                field_name='address',
            ) from None

        if resolved_address is None:
            raise ValidationError(
                f'Given ENS address {given_address} could not be resolved for Ethereum',
                field_name='address',
            ) from None

        address = to_checksum_address(resolved_address)
        log.info(f'Resolved ENS {given_address} to {address}')

    return address


def _transform_substrate_address(
        ethereum_inquirer: EthereumInquirer,
        given_address: str,
        chain: SUPPORTED_SUBSTRATE_CHAINS,
) -> SubstrateAddress:
    """Returns a DOT or KSM address (if exists) given an ENS domain. At this point any
    given address has been already validated either as an ENS name or as a
    valid Substrate address (ss58 format).

    NB: ENS domains for Substrate chains (e.g. KSM, DOT) store the Substrate
    public key. It requires to encode it with a specific ss58 format for
    obtaining the specific chain address.

    Polkadot/Polkadot ENS domain accounts:
    https://guide.kusama.network/docs/en/mirror-ens

    ENS domain substrate public key encoding:
    https://github.com/ensdomains/address-encoder/blob/master/src/index.ts
    """
    if not given_address.endswith('.eth'):
        return SubstrateAddress(given_address)

    try:
        resolved_address = ethereum_inquirer.ens_lookup(
            given_address,
            blockchain=chain,
        )
    except (RemoteError, InputError) as e:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved '
            f'for {chain} due to: {e!s}',
            field_name='address',
        ) from None

    if resolved_address is None:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved for {chain}',
            field_name='address',
        ) from None

    try:
        address = get_substrate_address_from_public_key(
            chain=chain,
            public_key=SubstratePublicKey(resolved_address),
        )
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f'Given ENS address {given_address} does not contain a valid '
            f'Substrate public key: {resolved_address}. {chain} address cannot be obtained.',
            field_name='address',
        ) from e
    else:
        log.debug(f'Resolved {chain} ENS {given_address} to {address}')
        return address


def _transform_evm_addresses(data: dict[str, Any], ethereum_inquirer: 'EthereumInquirer') -> None:
    for idx, account in enumerate(data['accounts']):
        data['accounts'][idx]['address'] = _transform_evm_address(
            ethereum_inquirer=ethereum_inquirer,
            given_address=account['address'],
        )


class EvmAccountsPutSchema(AsyncQueryArgumentSchema):
    accounts = fields.List(fields.Nested(BlockchainAccountDataSchema), required=True)

    def __init__(self, ethereum_inquirer: EthereumInquirer):
        super().__init__()
        self.ethereum_inquirer = ethereum_inquirer

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        data['blockchain'] = SupportedBlockchain.ETHEREUM  # any evm chain
        _validate_blockchain_account_schemas(data, lambda x: x['address'])
        data.pop('blockchain')

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        _transform_evm_addresses(data=data, ethereum_inquirer=self.ethereum_inquirer)
        return data


class BlockchainAccountsPatchSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    accounts = fields.List(fields.Nested(BlockchainAccountDataSchema), required=True)

    def __init__(self, ethereum_inquirer: EthereumInquirer):
        super().__init__()
        self.ethereum_inquirer = ethereum_inquirer

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        _validate_blockchain_account_schemas(data, lambda x: x['address'])

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        if data['blockchain'].is_bitcoin():
            for idx, account in enumerate(data['accounts']):
                data['accounts'][idx]['address'] = _transform_btc_or_bch_address(
                    ethereum_inquirer=self.ethereum_inquirer,
                    given_address=account['address'],
                    blockchain=data['blockchain'],
                )
        elif data['blockchain'].is_evm():
            _transform_evm_addresses(data=data, ethereum_inquirer=self.ethereum_inquirer)
        elif data['blockchain'].is_substrate():
            for idx, account in enumerate(data['accounts']):
                data['accounts'][idx]['address'] = _transform_substrate_address(
                    ethereum_inquirer=self.ethereum_inquirer,
                    given_address=account['address'],
                    chain=data['blockchain'],
                )

        return data


class BlockchainAccountsPutSchema(AsyncQueryArgumentSchema, BlockchainAccountsPatchSchema):
    ...


class BlockchainAccountsDeleteSchema(AsyncQueryArgumentSchema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    accounts = fields.List(fields.String(), required=True)

    def __init__(self, ethereum_inquirer: EthereumInquirer):
        super().__init__()
        self.ethereum_inquirer = ethereum_inquirer

    @validates_schema
    def validate_blockchain_accounts_delete_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        _validate_blockchain_account_schemas(data, lambda x: x)

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        if data['blockchain'].is_bitcoin():
            data['accounts'] = [
                _transform_btc_or_bch_address(self.ethereum_inquirer, x, data['blockchain'])
                for x in data['accounts']
            ]
        if data['blockchain'].is_evm():
            data['accounts'] = [
                _transform_evm_address(self.ethereum_inquirer, x) for x in data['accounts']
            ]
        if data['blockchain'].is_substrate():
            data['accounts'] = [
                _transform_substrate_address(
                    self.ethereum_inquirer, x, data['blockchain']) for x in data['accounts']
            ]

        return data


class IgnoredAssetsSchema(Schema):
    assets = fields.List(AssetField(expected_type=Asset), required=True)


class IgnoredActionsModifySchema(Schema):
    action_type = SerializableEnumField(enum_class=ActionType, required=True)
    data = fields.List(fields.Raw(), required=True)

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        given_data = data['data']
        new_data = []
        action_type = data['action_type']
        if action_type == ActionType.EVM_TRANSACTION:
            for entry in given_data:
                try:
                    chain_id = EvmChainNameField()._deserialize(entry['evm_chain'], None, None)
                    tx_hash = EVMTransactionHashField()._deserialize(entry['tx_hash'], None, None)
                except KeyError as e:
                    raise ValidationError(f'Did not find {e!s} at the given data') from e
                new_data.append(f'{chain_id.value}{tx_hash.hex()}')  # pylint: disable=no-member
        else:
            if not all(isinstance(x, str) for x in given_data):
                raise ValidationError(
                    f'The ignored action data for {action_type.serialize()} need to be a list of strings',  # noqa: E501
                )
            new_data = given_data

        data['data'] = new_data
        return data


class AssetsPostSchema(DBPaginationSchema, DBOrderBySchema):
    name = fields.String(load_default=None)
    symbol = fields.String(load_default=None)
    asset_type = SerializableEnumField(enum_class=AssetType, load_default=None)
    address = EvmAddressField(load_default=None)
    evm_chain = EvmChainNameField(load_default=None)
    ignored_assets_handling = SerializableEnumField(enum_class=IgnoredAssetsHandling, load_default=IgnoredAssetsHandling.NONE)  # noqa: E501
    show_user_owned_assets_only = fields.Boolean(load_default=False)
    identifiers = DelimitedOrNormalList(fields.String(required=True), load_default=None)

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__()
        self.db = db

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        # the length of `order_by_attributes` and `ascending` are the same. So check only one.
        if data['order_by_attributes'] is not None and len(data['order_by_attributes']) > 1:
            raise ValidationError(
                message='Multiple fields ordering is not allowed.',
                field_name='order_by_attributes',
            )

        if (
            data['evm_chain'] is not None and
            data['asset_type'] not in (None, AssetType.EVM_TOKEN)
        ):
            raise ValidationError(
                message='Filtering by evm_chain is only supported for evm tokens',
                field_name='evm_chain',
            )

    @post_load
    def make_assets_post_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = AssetsFilterQuery.make(
            and_op=True,
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['name'],
            ),
            limit=data['limit'],
            offset=data['offset'],
            name=data['name'],
            symbol=data['symbol'],
            asset_type=data['asset_type'],
            chain_id=data['evm_chain'],
            address=data['address'],
            identifiers=data['identifiers'],
            show_user_owned_assets_only=data['show_user_owned_assets_only'],
            ignored_assets_handling=data['ignored_assets_handling'],
        )
        return {'filter_query': filter_query}


class AssetsSearchLevenshteinSchema(Schema):
    value = fields.String(required=True)
    evm_chain = EvmChainNameField(load_default=None)
    limit = fields.Integer(required=True)
    search_nfts = fields.Boolean(load_default=False)

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__()
        self.db = db

    @post_load
    def make_levenshtein_search_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = LevenshteinFilterQuery.make(
            and_op=True,
            substring_search=data['value'].strip().casefold(),
            chain_id=data['evm_chain'],
            ignored_assets_handling=IgnoredAssetsHandling.EXCLUDE,  # do not check ignored asssets at search  # noqa: E501
        )
        return {
            'filter_query': filter_query,
            'limit': data['limit'],
            'search_nfts': data['search_nfts'],
        }


class AssetsSearchByColumnSchema(DBOrderBySchema, DBPaginationSchema):
    search_column = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=('name', 'symbol')),
    )
    value = fields.String(required=True)
    evm_chain = EvmChainNameField(load_default=None)
    return_exact_matches = fields.Boolean(load_default=False)

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__()
        self.db = db

    @post_load
    def make_assets_search_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = AssetsFilterQuery.make(
            and_op=True,
            order_by_rules=create_order_by_rules_list(data=data, default_order_by_fields=['name']),
            limit=data['limit'],
            offset=0,  # this is needed for the `limit` argument to work.
            substring_search=data['value'].strip(),
            search_column=data['search_column'],
            return_exact_matches=data['return_exact_matches'],
            chain_id=data['evm_chain'],
            identifier_column_name='assets.identifier',
            ignored_assets_handling=IgnoredAssetsHandling.EXCLUDE,  # do not check ignored asssets at search  # noqa: E501
        )
        return {'filter_query': filter_query}


class AssetsMappingSchema(Schema):
    identifiers = DelimitedOrNormalList(fields.String(required=True), required=True)


class AssetsReplaceSchema(Schema):
    source_identifier = fields.String(required=True)
    target_asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['source_identifier'].startswith(EVM_CHAIN_DIRECTIVE):
            raise ValidationError(
                message="Can't merge two evm tokens",
                field_name='source_identifier',
            )


class QueriedAddressesSchema(Schema):
    module = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=list(AVAILABLE_MODULES_MAP.keys())),
    )
    address = EvmAddressField(required=True)


class DataImportSchema(AsyncQueryArgumentSchema):
    source = SerializableEnumField(enum_class=DataImportSource, required=True)
    file = FileField(required=True, allowed_extensions=('.csv',))
    timestamp_format = fields.String(load_default=None)

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        if data['timestamp_format'] is None:
            # We need to pop it in order to use default parameters further down the line
            data.pop('timestamp_format')
        return data


class AssetIconUploadSchema(Schema):
    asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)
    file = FileField(required=True, allowed_extensions=ALLOWED_ICON_EXTENSIONS)


class ExchangeRatesSchema(AsyncQueryArgumentSchema):
    currencies = DelimitedOrNormalList(
        MaybeAssetField(expected_type=AssetWithOracles),
        required=True,
    )


class WatcherSchema(Schema):
    type = fields.String(required=True)
    args = fields.Dict(required=True)


class WatchersAddSchema(Schema):
    """The schema for adding a watcher.

    No validation here since it happens server side and no need to duplicate code
    TODO: When we have common libraries perhaps do validation here too to
    avoid potential server roundtrip for nothing
    """
    watchers = fields.List(fields.Nested(WatcherSchema), required=True)


class WatcherForEditingSchema(WatcherSchema):
    identifier = fields.String(required=True)


class WatchersEditSchema(WatchersAddSchema):
    """The schema for editing a watcher.

    No validation here since it happens server side and no need to duplicate code
    TODO: When we have common libraries perhaps do validation here too to
    avoid potential server roundtrip for nothing
    """
    watchers = fields.List(fields.Nested(WatcherForEditingSchema), required=True)


class WatchersDeleteSchema(Schema):
    """The schema for deleting watchers.

    No validation here since it happens server side and no need to duplicate code
    TODO: When we have common libraries perhaps do validation here too to
    avoid potential server roundtrip for nothing
    """
    watchers = fields.List(fields.String(required=True), required=True)


class SingleAssetIdentifierSchema(Schema):
    asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)


class SingleAssetWithOraclesIdentifierSchema(Schema):
    asset = AssetField(
        required=True,
        expected_type=AssetWithOracles,
        form_with_incomplete_data=True,
    )


class CurrentAssetsPriceSchema(AsyncQueryArgumentSchema):
    assets = DelimitedOrNormalList(
        AssetField(expected_type=AssetWithNameAndType, required=True),
        required=True,
        validate=webargs.validate.Length(min=1),
    )
    target_asset = AssetField(expected_type=Asset, required=True)
    ignore_cache = fields.Boolean(load_default=False)


class HistoricalAssetsPriceSchema(AsyncQueryArgumentSchema):
    assets_timestamp = fields.List(
        fields.Tuple(  # type: ignore # Tuple is not annotated
            (AssetField(expected_type=Asset, required=True), TimestampField(required=True)),
            required=True,
        ),
        required=True,
        validate=webargs.validate.Length(min=1),
    )
    target_asset = AssetField(expected_type=Asset, required=True)


class AssetUpdatesRequestSchema(AsyncQueryArgumentSchema):
    up_to_version = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            error='Asset update target version should be >= 0',
        ),
        load_default=None,
    )
    conflicts = AssetConflictsField(load_default=None)


class AssetResetRequestSchema(Schema):
    reset = fields.String(required=True)
    ignore_warnings = fields.Boolean(load_default=False)


class NamedEthereumModuleDataSchema(Schema):
    module_name = fields.String(
        validate=webargs.validate.OneOf(choices=list(AVAILABLE_MODULES_MAP.keys())),
    )


class NamedOracleCacheSchema(Schema):
    oracle = HistoricalPriceOracleField(required=True)
    from_asset = AssetField(expected_type=AssetWithOracles, required=True)
    to_asset = AssetField(expected_type=AssetWithOracles, required=True)


class NamedOracleCacheCreateSchema(AsyncQueryArgumentSchema, NamedOracleCacheSchema):
    purge_old = fields.Boolean(load_default=False)


class NamedOracleCacheGetSchema(AsyncQueryArgumentSchema):
    oracle = HistoricalPriceOracleField(required=True)


class ERC20InfoSchema(AsyncQueryArgumentSchema):
    address = EvmAddressField(required=True)
    evm_chain = EvmChainNameField(required=True, limit_to=list(EVM_CHAIN_IDS_WITH_TRANSACTIONS))


class BinanceMarketsUserSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=(Location.BINANCEUS, Location.BINANCE), required=True)


class ManualPriceSchema(Schema):
    from_asset = AssetField(expected_type=Asset, required=True)
    to_asset = AssetField(expected_type=Asset, required=True)
    price = PriceField(required=True)


class TimedManualPriceSchema(ManualPriceSchema):
    timestamp = TimestampField(required=True)


class SnapshotTimestampQuerySchema(Schema):
    timestamp = TimestampField(required=True)


class ManualPriceRegisteredSchema(Schema):
    from_asset = AssetField(expected_type=Asset, load_default=None)
    to_asset = AssetField(expected_type=Asset, load_default=None)


class ManualPriceDeleteSchema(Schema):
    from_asset = AssetField(expected_type=Asset, required=True)
    to_asset = AssetField(expected_type=Asset, required=True)
    timestamp = TimestampField(required=True)


class AvalancheTransactionQuerySchema(TimestampRangeSchema, AsyncQueryArgumentSchema):
    address = EvmAddressField(required=True)


class SingleFileSchema(Schema):
    file = FileField(required=True)


class FileListSchema(Schema):
    files = fields.List(FileField(), required=True)


class Eth2ValidatorSchema(Schema):
    validator_index = fields.Integer(
        load_default=None,
        validate=webargs.validate.Range(
            min=0,
            error='Validator index must be an integer >= 0',
        ),
    )
    public_key = fields.String(load_default=None)
    ownership_percentage = FloatingPercentageField(load_default=ONE)

    @validates_schema
    def validate_eth2_validator_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        validator_index = data.get('validator_index')
        public_key = data.get('public_key')
        if validator_index is None and public_key is None:
            raise ValidationError(
                'Need to provide either a validator index or a public key for an eth2 validator',
            )

        if public_key is not None:
            try:
                pubkey_bytes = hexstring_to_bytes(public_key)
            except DeserializationError as e:
                raise ValidationError(f'The given eth2 public key {public_key} is not valid hex') from e  # noqa: E501

            bytes_length = len(pubkey_bytes)
            if bytes_length != 48:
                raise ValidationError(
                    f'The given eth2 public key {public_key} has {bytes_length} '
                    f'bytes. Expected 48.',
                )

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        public_key = data.get('public_key')
        if public_key is not None and not public_key.startswith('0x'):
            # since we started storing eth2 pubkey with '0x' in eth2_deposits let's keep the format
            data['public_key'] = '0x' + public_key

        return data


class Eth2ValidatorPutSchema(AsyncQueryArgumentSchema, Eth2ValidatorSchema):
    ...


class Eth2ValidatorDeleteSchema(Schema):
    validators = DelimitedOrNormalList(fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            error='Validator index must be an integer >= 0',
        ),
    ), required=True)


class Eth2ValidatorPatchSchema(Schema):
    validator_index = fields.Integer(
        validate=webargs.validate.Range(
            min=0,
            error='Validator index must be an integer >= 0',
        ),
        required=True,
    )
    ownership_percentage = FloatingPercentageField(required=True)


class Eth2DailyStatsSchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    validators = fields.List(fields.Integer(), load_default=None)

    @validates_schema
    def validate_eth2_daily_stats_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        valid_ordering_attr = {
            None,
            'timestamp',
            'validator_index',
            'pnl',
        }
        if (
            data['order_by_attributes'] is not None and
            not set(data['order_by_attributes']).issubset(valid_ordering_attr)
        ):
            error_msg = (
                f'order_by_attributes for eth2 daily stats can not be '
                f'{",".join(set(data["order_by_attributes"]) - valid_ordering_attr)}'
            )
            raise ValidationError(
                message=error_msg,
                field_name='order_by_attributes',
            )

    @post_load
    def make_eth2_daily_stats_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = Eth2DailyStatsFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            validators=data['validators'],
        )
        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
        }


class StatisticsNetValueSchema(Schema):
    include_nfts = fields.Boolean(load_default=True)


class BinanceMarketsSchema(Schema):
    location = LocationField(
        limit_to=(Location.BINANCEUS, Location.BINANCE),
        load_default=Location.BINANCE,
    )


class AppInfoSchema(Schema):
    check_for_updates = fields.Boolean(load_default=False)


class IdentifiersListSchema(Schema):
    identifiers = fields.List(fields.Integer(), required=True)


class HistoryEventsDeletionSchema(IdentifiersListSchema):
    force_delete = fields.Boolean(load_default=False)


class AssetsImportingSchema(Schema):
    file = FileField(allowed_extensions=['.zip', '.json'], load_default=None)
    destination = DirectoryField(load_default=None)
    action = fields.String(
        validate=webargs.validate.OneOf(choices=('upload', 'download')),
        required=True,
    )

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        file = data.get('file')
        action = data.get('action')
        if action == 'upload' and file is None:
            raise ValidationError(
                message='A file has to be provided when action is upload',
                field_name='action',
            )


class AssetsImportingFromFormSchema(Schema):
    file = FileField(allowed_extensions=['.zip', '.json'], required=True)


class ReverseEnsSchema(AsyncIgnoreCacheQueryArgumentSchema):
    ethereum_addresses = fields.List(EvmAddressField(), required=True)


class OptionalAddressesListSchema(Schema):
    addresses = fields.List(EvmAddressField(required=True), load_default=None)


class AddressWithOptionalBlockchainSchema(Schema):
    address = EvmAddressField(required=True)
    blockchain = BlockchainField(load_default=None)

    @post_load()
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        return OptionalChainAddress(
            address=data['address'],
            blockchain=data['blockchain'],
        )


class OptionalAddressesWithBlockchainsListSchema(Schema):
    addresses = fields.List(fields.Nested(AddressWithOptionalBlockchainSchema), load_default=None)


class BaseAddressbookSchema(Schema):
    book_type = SerializableEnumField(enum_class=AddressbookType, required=True)


class AddressbookAddressesSchema(
    BaseAddressbookSchema,
    OptionalAddressesWithBlockchainsListSchema,
):
    ...


class AddressbookEntrySchema(Schema):
    address = EvmAddressField(required=True)
    name = fields.String(required=True)
    # Need None option here in case the user wants to update all the entries for the address.
    blockchain = BlockchainField(load_default=None)

    @post_load()
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        return AddressbookEntry(
            address=data['address'],
            name=data['name'],
            blockchain=data['blockchain'],
        )


class AddressbookUpdateSchema(BaseAddressbookSchema):
    entries = NonEmptyList(fields.Nested(AddressbookEntrySchema), required=True)


class SnapshotImportingSchema(Schema):
    balances_snapshot_file = FileField(allowed_extensions=['.csv'], required=True)
    location_data_snapshot_file = FileField(allowed_extensions=['.csv'], required=True)


class SnapshotQuerySchema(SnapshotTimestampQuerySchema):
    action = fields.String(
        validate=webargs.validate.OneOf(choices=('export', 'download')),
        load_default=None,
    )
    path = DirectoryField(load_default=None)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        path = data.get('path')
        action = data.get('action')
        if action == 'export' and path is None:
            raise ValidationError(
                message='A path has to be provided when action is export',
                field_name='action',
            )


class BalanceSnapshotSchema(Schema):
    timestamp = TimestampField(required=True)
    category = SerializableEnumField(enum_class=BalanceType, required=True)
    asset_identifier = AssetField(
        expected_type=Asset,
        required=True,
        form_with_incomplete_data=True,
    )
    amount = AmountField(required=True)
    usd_value = AmountField(required=True)

    @post_load
    def make_balance(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> DBAssetBalance:
        return DBAssetBalance(
            category=data['category'],
            time=data['timestamp'],
            asset=data['asset_identifier'],
            amount=data['amount'],
            usd_value=data['usd_value'],
        )


class LocationDataSnapshotSchema(Schema):
    timestamp = TimestampField(required=True)
    location = LocationField(required=True)
    usd_value = AmountField(required=True)

    @post_load
    def make_location_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> LocationData:
        return LocationData(
            time=data['timestamp'],
            location=data['location'].serialize_for_db(),
            usd_value=str(data['usd_value']),
        )


class SnapshotEditingSchema(Schema):
    timestamp = TimestampField(required=True)
    balances_snapshot = fields.List(
        fields.Nested(BalanceSnapshotSchema),
        required=True,
        validate=webargs.validate.Length(min=1),
    )
    location_data_snapshot = fields.List(
        fields.Nested(LocationDataSnapshotSchema),
        required=True,
        validate=webargs.validate.Length(min=1),
    )

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if not data['timestamp'] == data['balances_snapshot'][0].time == data['location_data_snapshot'][0].time:  # noqa: E501
            raise ValidationError(
                f'timestamp provided {data["timestamp"]} is not the same as the '
                f'one for the entries provided.',
            )


class RpcNodeSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501


class RpcAddNodeSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    name = fields.String(
        required=True,
        validate=webargs.validate.NoneOf(
            iterable=['', ETHEREUM_ETHERSCAN_NODE_NAME],
            error=f"Name can't be empty or {ETHEREUM_ETHERSCAN_NODE_NAME}",
        ),
    )
    endpoint = fields.String(required=True)
    owned = fields.Boolean(load_default=False)
    weight = FloatingPercentageField(required=True)
    active = fields.Boolean(load_default=False)


class RpcNodeEditSchema(RpcAddNodeSchema):
    def __init__(self, dbhandler: 'DBHandler') -> None:
        super().__init__()
        self.dbhandler = dbhandler

    name = fields.String(
        required=True,
        validate=webargs.validate.NoneOf(
            iterable=[''],
            error="Name can't be empty",
        ),
    )
    identifier = fields.Integer(required=True)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        endpoint_is_given = len(data['endpoint'].strip()) != 0
        if self.dbhandler.is_etherscan_node(data['identifier']):
            if endpoint_is_given:
                raise ValidationError(
                    field_name='endpoint',
                    message='It is not allowed to modify the etherscan node endpoint',
                )
            if data['name'] not in (
                ETHEREUM_ETHERSCAN_NODE_NAME,
                OPTIMISM_ETHERSCAN_NODE_NAME,
                POLYGON_POS_ETHERSCAN_NODE_NAME,
                ARBITRUM_ONE_ETHERSCAN_NODE_NAME,
            ):
                raise ValidationError(
                    message="Can't change the etherscan node name",
                    field_name='name',
                )
        elif endpoint_is_given is False:
            raise ValidationError(
                field_name='endpoint',
                message='endpoint can be empty only for etherscan',
            )


class RpcNodeListDeleteSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    identifier = fields.Integer(required=True)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['identifier'] == 1:
            raise ValidationError(
                message="Can't delete the etherscan node",
                field_name='identifier',
            )


class DetectTokensSchema(
    AsyncQueryArgumentSchema,
    OnlyCacheQuerySchema,
    OptionalAddressesListSchema,
):
    blockchain = BlockchainField(required=True, exclude_types=list(NON_EVM_CHAINS))


class UserNotesPutSchema(Schema):
    title = fields.String(required=True)
    content = fields.String(required=True)
    location = fields.String(required=True)
    is_pinned = fields.Boolean(required=True)


class UserNotesPatchSchema(UserNotesPutSchema, IntegerIdentifierSchema):
    last_update_timestamp = TimestampField(required=True)

    @post_load
    def make_user_note(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, UserNote]:
        return {'user_note': UserNote.deserialize(data)}


class UserNotesGetSchema(TimestampRangeSchema, DBPaginationSchema, DBOrderBySchema):
    title_substring = fields.String(load_default=None)
    location = fields.String(load_default=None)

    @post_load
    def make_user_notes_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = UserNotesFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data,
                default_order_by_fields=['last_update_timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            location=data['location'],
            substring_search=data['title_substring'],
        )
        return {
            'filter_query': filter_query,
        }


class CustomAssetsQuerySchema(DBPaginationSchema, DBOrderBySchema):
    name = fields.String(load_default=None)
    identifier = fields.String(load_default=None)
    custom_asset_type = fields.String(load_default=None)

    @post_load
    def make_custom_assets_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = CustomAssetsFilterQuery.make(
            limit=data['limit'],
            offset=data['offset'],
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['name'],
                is_ascending_by_default=True,
            ),
            name=data['name'],
            identifier=data['identifier'],
            custom_asset_type=data['custom_asset_type'],
        )
        return {'filter_query': filter_query}


class NFTLpFilterSchema(Schema):
    lps_handling = SerializableEnumField(
        enum_class=NftLpHandling,
        load_default=NftLpHandling.ALL_NFTS,
    )


class NFTFilterQuerySchema(
        NFTLpFilterSchema,
        AsyncIgnoreCacheQueryArgumentSchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    owner_addresses = fields.List(EvmAddressField(required=True), load_default=None)
    name = fields.String(load_default=None)
    collection_name = fields.String(load_default=None)
    ignored_assets_handling = SerializableEnumField(enum_class=IgnoredAssetsHandling, load_default=IgnoredAssetsHandling.NONE)  # noqa: E501

    def __init__(self, chains_aggregator: 'ChainsAggregator') -> None:
        super().__init__()
        self.chains_aggregator = chains_aggregator
        self.db = chains_aggregator.database

    @post_load
    def make_nft_filter_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        owner_addresses = self.chains_aggregator.queried_addresses_for_module('nfts') if data['owner_addresses'] is None else data['owner_addresses']  # noqa: E501
        filter_query = NFTFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['name'],
            ),
            limit=data['limit'],
            offset=data['offset'],
            owner_addresses=owner_addresses,
            name=data['name'],
            collection_name=data['collection_name'],
            ignored_assets_handling=data['ignored_assets_handling'],
            lps_handling=data['lps_handling'],
        )
        return {
            'async_query': data['async_query'],
            'ignore_cache': data['ignore_cache'],
            'filter_query': filter_query,
        }


class EventDetailsQuerySchema(Schema):
    identifier = fields.Integer(required=True)


class EvmTransactionHashAdditionSchema(AsyncQueryArgumentSchema):
    evm_chain = EvmChainNameField(required=True, limit_to=list(EVM_CHAIN_IDS_WITH_TRANSACTIONS))
    tx_hash = EVMTransactionHashField(required=True)
    associated_address = EvmAddressField(required=True)

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__()
        self.db = db

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        """This validation does the following:
        - Checks that the `tx_hash` is not present in the db for the specified `evm_chain`.
        - Checks that the `associated_address` is tracked by rotki.
        """
        with self.db.conn.read_ctx() as cursor:
            tx_count = cursor.execute(
                'SELECT COUNT(*) FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
                (data['tx_hash'], data['evm_chain'].serialize_for_db()),
            ).fetchone()[0]
            if tx_count > 0:
                raise ValidationError(
                    message=f'tx_hash {data["tx_hash"].hex()} for {data["evm_chain"]} already present in the database',  # noqa: E501
                    field_name='tx_hash',
                )

            accounts_count = cursor.execute(
                'SELECT COUNT(*) FROM blockchain_accounts WHERE blockchain=? AND account=?',
                (data['evm_chain'].to_blockchain().value, data['associated_address']),
            ).fetchone()[0]
            if accounts_count == 0:
                raise ValidationError(
                    message=f'address {data["associated_address"]} provided is not tracked by rotki for {data["evm_chain"]}',  # noqa: E501
                    field_name='associated_address',
                )


class BinanceSavingsSchema(BaseStakingQuerySchema):
    location = LocationField(
        required=True,
        limit_to=(Location.BINANCE, Location.BINANCEUS),
    )

    @post_load
    def make_binance_savings_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        location = data['location']
        query_dict = self._make_query(
            location=location,
            data=data,
            event_types=[HistoryEventType.RECEIVE],
            query_event_subtypes=[HistoryEventSubType.INTEREST_PAYMENT],
            value_event_subtypes=[HistoryEventSubType.INTEREST_PAYMENT],
            exclude_event_subtypes=None,
        )
        query_dict.update({'location': location})
        return query_dict


class EnsAvatarsSchema(Schema):
    ens_name = fields.String(required=True, validate=lambda x: x.endswith('.eth'))


class ClearCacheSchema(Schema):
    cache_type = fields.String(
        required=True,
        validate=[validate.OneOf({'icons', 'avatars'})],
    )

    class Meta:
        # this is to allow further validation depending on cache_type
        unknown = marshmallow.EXCLUDE


class ClearIconsCacheSchema(Schema):
    entries = fields.List(
        AssetField(
            required=True,
            expected_type=Asset,
            form_with_incomplete_data=True,
        ),
        load_default=None,
    )


class ClearAvatarsCacheSchema(Schema):
    entries = fields.List(
        fields.String(required=True, validate=lambda x: x.endswith('.eth')),
        load_default=None,
    )


class EthStakingHistoryStats(Schema):
    """Schema for querying ethereum staking history stats"""
    addresses = DelimitedOrNormalList(EvmAddressField, load_default=None)
    validator_indices = DelimitedOrNormalList(fields.Integer(), load_default=None)


class EthStakingHistoryStatsProfit(EthStakingHistoryStats, TimestampRangeSchema):
    """Schema for querying ethereum staking history stats"""

    def __init__(self, chains_aggregator: 'ChainsAggregator') -> None:
        super().__init__()
        self.chains_aggregator = chains_aggregator

    @post_load
    def make_history_event_filter(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        if (addresses := data['addresses']) is None:
            addresses = self.chains_aggregator.queried_addresses_for_module('eth2')

        common_arguments = {
            'from_ts': data['from_timestamp'],
            'to_ts': data['to_timestamp'],
            'location_labels': addresses,
            'validator_indices': data['validator_indices'],
        }

        withdrawals_filter_query = EthStakingEventFilterQuery.make(
            **common_arguments,
            event_types=[HistoryEventType.STAKING],
            event_subtypes=[HistoryEventSubType.REMOVE_ASSET],
            entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT]),  # noqa: E501
        )
        execution_filter_query = EthStakingEventFilterQuery.make(
            **common_arguments,
            event_types=[HistoryEventType.STAKING],
            event_subtypes=[HistoryEventSubType.BLOCK_PRODUCTION, HistoryEventSubType.MEV_REWARD],
            entry_types=IncludeExcludeFilterData(values=[HistoryBaseEntryType.ETH_BLOCK_EVENT]),
        )

        return {
            'withdrawals_filter_query': withdrawals_filter_query,
            'execution_filter_query': execution_filter_query,
        }


class EthStakingHistoryStatsDetails(EthStakingHistoryStats, AsyncIgnoreCacheQueryArgumentSchema):
    """Schema for querying ethereum staking history details"""


class SkippedExternalEventsExportSchema(Schema):
    filepath = FileField(required=True, allowed_extensions=['.csv'])


class ExportHistoryEventSchema(HistoryEventSchema):
    """Schema for quering history events"""
    directory_path = DirectoryField(required=True)

    def make_extra_filtering_arguments(self, data: dict[str, Any]) -> dict[str, Any]:
        return {}

    def generate_fields_post_validation(self, data: dict[str, Any]) -> dict[str, Any]:
        extra_fields = {}
        if (directory_path := data.get('directory_path')) is not None:
            extra_fields['directory_path'] = directory_path
        return extra_fields
