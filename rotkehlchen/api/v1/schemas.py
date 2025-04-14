import logging
import operator
import tempfile
import typing
from collections.abc import Callable
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal, cast, get_args

import marshmallow
import webargs
from eth_utils import to_checksum_address
from marshmallow import INCLUDE, Schema, fields, post_load, validate, validates_schema
from marshmallow.exceptions import ValidationError
from werkzeug.datastructures import FileStorage

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.accounting.types import SchemaEventType
from rotkehlchen.assets.asset import Asset, AssetWithNameAndType, AssetWithOracles, EvmToken
from rotkehlchen.assets.ignored_assets_handling import IgnoredAssetsHandling
from rotkehlchen.assets.types import AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.base.constants import BASE_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.binance_sc.constants import BINANCE_SC_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.bitcoin.bch.utils import (
    is_valid_bitcoin_cash_address,
    validate_bch_address_input,
)
from rotkehlchen.chain.bitcoin.hdkey import HDKey, XpubType
from rotkehlchen.chain.bitcoin.utils import is_valid_btc_address, scriptpubkey_to_btc_address
from rotkehlchen.chain.constants import NON_BITCOIN_CHAINS
from rotkehlchen.chain.ethereum.constants import ETHEREUM_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2
from rotkehlchen.chain.ethereum.modules.eth2.structures import PerformanceStatusFilter
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.chain.evm.decoding.ens.utils import is_potential_ens_name
from rotkehlchen.chain.evm.types import EvmAccount, EvmlikeAccount
from rotkehlchen.chain.gnosis.constants import GNOSIS_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.optimism.constants import OPTIMISM_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.scroll.constants import SCROLL_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.substrate.types import SubstrateAddress, SubstratePublicKey
from rotkehlchen.chain.substrate.utils import (
    get_substrate_address_from_public_key,
    is_valid_substrate_address,
)
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import EVM_CHAIN_DIRECTIVE
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.calendar import CalendarEntry, CalendarFilterQuery, ReminderEntry
from rotkehlchen.db.constants import (
    LINKABLE_ACCOUNTING_PROPERTIES,
    LINKABLE_ACCOUNTING_SETTINGS_NAME,
)
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import (
    AccountingRulesFilterQuery,
    AddressbookFilterQuery,
    AssetsFilterQuery,
    CounterpartyAssetMappingsFilterQuery,
    CustomAssetsFilterQuery,
    Eth2DailyStatsFilterQuery,
    EthStakingEventFilterQuery,
    EvmEventFilterQuery,
    EvmTransactionsFilterQuery,
    HistoryEventFilterQuery,
    LevenshteinFilterQuery,
    LocationAssetMappingsFilterQuery,
    NFTFilterQuery,
    PaginatedFilterQuery,
    ReportDataFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.misc import InputError, RemoteError, XPUBError
from rotkehlchen.errors.serialization import DeserializationError, EncodingError
from rotkehlchen.exchanges.constants import (
    ALL_SUPPORTED_EXCHANGES,
    EXCHANGES_WITH_PASSPHRASE,
    EXCHANGES_WITHOUT_API_SECRET,
    SUPPORTED_EXCHANGES,
)
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    AssetMovementExtraData,
    create_asset_movement_with_fee,
)
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType, HistoryEvent
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.swap import SwapEventExtraData, create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.icons import ALLOWED_ICON_EXTENSIONS
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.oracles.structures import SETTABLE_CURRENT_PRICE_ORACLES
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    DEFAULT_ADDRESS_NAME_PRIORITY,
    EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    EVM_EVMLIKE_LOCATIONS,
    NON_EVM_CHAINS,
    SUPPORTED_BITCOIN_CHAINS,
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_EVMLIKE_CHAINS,
    SUPPORTED_SUBSTRATE_CHAINS,
    AddressbookEntry,
    AddressbookType,
    BlockchainAddress,
    BTCAddress,
    ChainID,
    ChainType,
    ChecksumEvmAddress,
    CostBasisMethod,
    CounterpartyAssetMappingDeleteEntry,
    CounterpartyAssetMappingUpdateEntry,
    EvmlikeChain,
    ExchangeLocationID,
    ExternalService,
    ExternalServiceApiCredentials,
    HistoryEventQueryType,
    Location,
    LocationAssetMappingDeleteEntry,
    LocationAssetMappingUpdateEntry,
    ModuleName,
    OnlyPurgeableModuleName,
    OptionalBlockchainAddress,
    OptionalChainAddress,
    ProtocolsWithCache,
    SupportedBlockchain,
    Timestamp,
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
    EvmChainLikeNameField,
    EvmChainNameField,
    EvmCounterpartyField,
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
    StrEnumField,
    TaxFreeAfterPeriodField,
    TimestampField,
    TimestampMSField,
    XpubField,
)
from .types import IncludeExcludeFilterData, ModuleWithBalances, ModuleWithStats

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AssetValueThresholdSchema(Schema):
    usd_value_threshold = AmountField(load_default=None)


class AsyncQueryArgumentSchema(Schema):
    """A schema for getters that only have one argument enabling async query"""
    async_query = fields.Boolean(load_default=False)


class AsyncIgnoreCacheQueryArgumentSchema(AsyncQueryArgumentSchema):
    ignore_cache = fields.Boolean(load_default=False)


class TimestampRangeSchema(Schema):
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


class AsyncTaskSchema(Schema):
    task_id = fields.Integer(strict=True, load_default=None)

    def __init__(self, is_required: bool = False) -> None:
        super().__init__()
        self.is_required = is_required

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.is_required and data['task_id'] is None:
            raise ValidationError(
                message='task_id is required for this endpoint',
                field_name='task_id',
            )


class OnlyCacheQuerySchema(Schema):
    only_cache = fields.Boolean(load_default=False)


class DBPaginationSchema(Schema):
    limit = fields.Integer(load_default=None)
    offset = fields.Integer(load_default=None)


class DBOrderBySchema(Schema):
    order_by_attributes = DelimitedOrNormalList(fields.String(), load_default=None)
    ascending = DelimitedOrNormalList(fields.Boolean(), load_default=None)  # most recent first by default  # noqa: E501

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


class RequiredEvmlikeAddressOptionalChainSchema(Schema):
    address = EvmAddressField(required=True)
    chain = EvmChainLikeNameField(
        required=False,
        limit_to=SUPPORTED_EVM_EVMLIKE_CHAINS,  # type: ignore
        load_default=None,
    )

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        return EvmlikeAccount(data['address'], chain=data['chain'])


class BlockchainTransactionDeletionSchema(Schema):
    chain = BlockchainField(
        exclude_types=(
            SupportedBlockchain.ETHEREUM_BEACONCHAIN,
            SupportedBlockchain.AVALANCHE,
            *typing.get_args(SUPPORTED_BITCOIN_CHAINS),
            *typing.get_args(SUPPORTED_SUBSTRATE_CHAINS),
        ),
        required=False,
        load_default=None,
    )
    tx_hash = EVMTransactionHashField(required=False, load_default=None)

    @validates_schema
    def validate_tx_deletion_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['tx_hash'] is not None and data['chain'] is None:
            raise ValidationError(
                message='Deleting a specific transaction needs both tx_hash and chain',
                field_name='tx_hash',
            )


class EvmTransactionQuerySchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
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
            accounts=data['accounts'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            chain_id=data['evm_chain'],
        )

        return {
            'async_query': data['async_query'],
            'filter_query': filter_query,
        }


class EvmlikeTransactionQuerySchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
):
    accounts = fields.List(
        fields.Nested(RequiredEvmlikeAddressOptionalChainSchema),
        load_default=None,
        validate=lambda data: len(data) != 0,
    )
    chain = StrEnumField(enum_class=EvmlikeChain, load_default=None)


class EventsOnlineQuerySchema(AsyncQueryArgumentSchema):
    query_type = SerializableEnumField(enum_class=HistoryEventQueryType, required=True)


class EvmTransactionSchema(Schema):
    evm_chain = EvmChainNameField(required=True)
    tx_hash = EVMTransactionHashField(required=True)


class EvmTransactionDecodingSchema(AsyncQueryArgumentSchema):
    transactions = fields.List(
        fields.Nested(EvmTransactionSchema),
        validate=lambda data: len(data) != 0,
    )
    delete_custom = fields.Boolean(load_default=False)


class EvmLikeTransactionSchema(Schema):
    chain = StrEnumField(enum_class=EvmlikeChain, required=True)
    tx_hash = EVMTransactionHashField(required=True)


class EvmlikeTransactionDecodingSchema(AsyncQueryArgumentSchema):
    transactions = fields.List(
        fields.Nested(EvmLikeTransactionSchema),
        validate=lambda data: len(data) != 0,
    )


class EvmPendingTransactionDecodingSchema(AsyncIgnoreCacheQueryArgumentSchema):
    chains = fields.List(
        EvmChainNameField(limit_to=list(EVM_CHAIN_IDS_WITH_TRANSACTIONS)),
        load_default=EVM_CHAIN_IDS_WITH_TRANSACTIONS,
    )

    @validates_schema
    def validate_schema(
            self,
            chains: list[ChainID],
            **_kwargs: Any,
    ) -> None:

        if len(chains) == 0:
            raise ValidationError(
                message='The list of chains should not be empty',
                field_name='chains',
            )


class EvmlikePendingTransactionDecodingSchema(AsyncIgnoreCacheQueryArgumentSchema):
    chains = fields.List(
        StrEnumField(enum_class=EvmlikeChain),
        load_default=[EvmlikeChain.ZKSYNC_LITE],
    )

    @validates_schema
    def validate_schema(
            self,
            chains: list[ChainID],
            **_kwargs: Any,
    ) -> None:

        if len(chains) == 0:
            raise ValidationError(
                message='The list of chains should not be empty',
                field_name='chains',
            )


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
    ) -> tuple['AssetWithOracles', ...] | None:
        return (data['asset'],) if data['asset'] is not None else None

    def _make_query(
            self,
            location: Location,
            data: dict[str, Any],
            event_types: list[HistoryEventType],
            value_event_subtypes: list[HistoryEventSubType],
            query_event_subtypes: list[HistoryEventSubType] | None = None,
            exclude_event_subtypes: list[HistoryEventSubType] | None = None,
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
    ) -> tuple['AssetWithOracles', ...] | None:
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


class TypesAndCounterpatiesFiltersSchema(Schema):
    event_types = DelimitedOrNormalList(
        SerializableEnumField(enum_class=HistoryEventType),
        load_default=None,
    )
    event_subtypes = DelimitedOrNormalList(
        SerializableEnumField(enum_class=HistoryEventSubType),
        load_default=None,
    )
    counterparties = DelimitedOrNormalList(fields.String(load_default=None), load_default=None)


class HistoryEventSchema(
    TypesAndCounterpatiesFiltersSchema,
    TimestampRangeSchema,
    DBPaginationSchema,
    DBOrderBySchema,
):
    """Schema for querying history events"""
    exclude_ignored_assets = fields.Boolean(load_default=True)
    group_by_event_ids = fields.Boolean(load_default=False)
    event_identifiers = DelimitedOrNormalList(fields.String(), load_default=None)
    location = SerializableEnumField(Location, load_default=None)
    location_labels = DelimitedOrNormalList(fields.String(), load_default=None)
    asset = AssetField(expected_type=Asset, load_default=None)
    entry_types = IncludeExcludeListField(
        SerializableEnumField(enum_class=HistoryBaseEntryType),
        load_default=None,
    )
    customized_events_only = fields.Boolean(load_default=False)
    identifiers = DelimitedOrNormalList(fields.Integer(
        validate=webargs.validate.Range(
                min=0,
                error='Identifier must be an integer >= 0',
            ),
        ),
        load_default=None,
    )

    # EvmEvent only
    tx_hashes = DelimitedOrNormalList(EVMTransactionHashField(), load_default=None)
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
            'customized_events_only': data['customized_events_only'],
            'identifiers': data['identifiers'],
        }

        filter_query: HistoryEventFilterQuery | (EvmEventFilterQuery | EthStakingEventFilterQuery)
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


class CreateHistoryEventSchema(Schema):
    """Schema used when adding a new event in the EVM transactions view"""
    include_identifier: bool = False
    entry_type = SerializableEnumField(enum_class=HistoryBaseEntryType, required=True)
    history_event_context: ContextVar = ContextVar('history_event_context')

    def __init__(self, dbhandler: 'DBHandler') -> None:
        super().__init__()
        self.database = dbhandler

    class BaseSchema(Schema):
        timestamp = TimestampMSField(required=True)
        amount = AmountField(required=True)
        identifier = fields.Integer(required=True)

    class BaseEventSchema(BaseSchema):
        event_type = SerializableEnumField(enum_class=HistoryEventType, required=True)
        event_subtype = SerializableEnumField(
            enum_class=HistoryEventSubType,
            required=True,
        )
        asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)
        user_notes = fields.String(load_default=None)
        sequence_index = fields.Integer(required=True)
        location_label = fields.String(load_default=None)

    class CreateBaseHistoryEventSchema(BaseEventSchema):
        event_identifier = fields.String(required=True)
        location = LocationField(required=True)

        @post_load
        def make_history_base_entry(
                self,
                data: dict[str, Any],
                **_kwargs: Any,
        ) -> dict[str, Any]:
            data['notes'] = data.pop('user_notes')
            return {'events': [HistoryEvent(**data)]}

    class CreateEvmEventSchema(BaseEventSchema):
        """Schema used when adding a new event in the EVM transactions view"""
        tx_hash = EVMTransactionHashField(required=True)
        event_identifier = fields.String(required=False, load_default=None)
        counterparty = fields.String(load_default=None)
        product = SerializableEnumField(enum_class=EvmProduct, load_default=None)
        address = EvmAddressField(load_default=None)
        extra_data = fields.Dict(load_default=None)
        location = LocationField(required=True, limit_to=EVM_EVMLIKE_LOCATIONS)

        @post_load
        def make_history_base_entry(
                self,
                data: dict[str, Any],
                **_kwargs: Any,
        ) -> dict[str, Any]:
            data['notes'] = data.pop('user_notes')
            return {'events': [EvmEvent(**data)]}

    class CreateEthBlockEventEventSchema(BaseSchema):
        is_mev_reward = fields.Boolean(required=True)
        event_identifier = fields.String(required=False, load_default=None)
        fee_recipient = EvmAddressField(required=True)
        block_number = fields.Integer(
            required=True,
            validate=webargs.validate.Range(
                min=0,
                error='Block number must be an integer >= 0',
            ),
        )
        validator_index = fields.Integer(
            required=True,
            validate=webargs.validate.Range(
                min=0,
                error='Validator index must be an integer >= 0',
            ),
        )

        @post_load
        def make_history_base_entry(
                self,
                data: dict[str, Any],
                **_kwargs: Any,
        ) -> dict[str, Any]:
            database = CreateHistoryEventSchema.history_event_context.get()['schema'].database
            with database.conn.read_ctx() as cursor:
                tracked_accounts = database.get_blockchain_accounts(cursor)
            data['fee_recipient_tracked'] = data['fee_recipient'] in tracked_accounts.get(SupportedBlockchain.ETHEREUM)  # noqa: E501
            return {'events': [EthBlockEvent(**data)]}

    class CreateEthDepositEventEventSchema(BaseSchema):
        tx_hash = EVMTransactionHashField(required=True)
        depositor = EvmAddressField(required=True)
        event_identifier = fields.String(required=False, load_default=None)
        sequence_index = fields.Integer(required=True)
        validator_index = fields.Integer(
            required=True,
            validate=webargs.validate.Range(
                min=0,
                error='Validator index must be an integer >= 0',
            ),
        )
        extra_data = fields.Dict(load_default=None)

        @post_load
        def make_history_base_entry(
                self,
                data: dict[str, Any],
                **_kwargs: Any,
        ) -> dict[str, Any]:
            return {'events': [EthDepositEvent(**data)]}

    class CreateEthWithdrawalEventEventSchema(BaseSchema):
        is_exit = fields.Boolean(required=True)
        event_identifier = fields.String(required=False, load_default=None)
        withdrawal_address = EvmAddressField(required=True)
        validator_index = fields.Integer(
            required=True,
            validate=webargs.validate.Range(
                min=0,
                error='Validator index must be an integer >= 0',
            ),
        )

        @post_load
        def make_history_base_entry(
                self,
                data: dict[str, Any],
                **_kwargs: Any,
        ) -> dict[str, Any]:
            return {'events': [EthWithdrawalEvent(**data)]}

    class CreateAssetMovementEventSchema(BaseSchema):
        event_type = SerializableEnumField(
            enum_class=HistoryEventType,
            allow_only=[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
            required=True,
        )
        fee = FeeField(load_default=None, validate=validate.Range(min=ZERO, min_inclusive=False))
        location = LocationField(required=True)
        location_label = fields.String(load_default=None)
        blockchain = fields.String(load_default=None)
        unique_id = fields.String(required=False, load_default=None)
        address = fields.String(required=False, load_default=None)  # It can be an address for any chain not only the supported ones so we validate it as string.  # noqa: E501
        transaction_id = fields.String(required=False, load_default=None)  # It can be a transaction from any chain. We don't do any special validation on it.  # noqa: E501
        event_identifier = fields.String(required=False, load_default=None)
        asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)
        fee_asset = AssetField(load_default=None, required=False, expected_type=Asset, form_with_incomplete_data=True)  # noqa: E501
        user_notes = fields.List(fields.String(), required=False, validate=validate.Length(min=1, max=2))  # noqa: E501

        @post_load
        def make_history_base_entry(
                self,
                data: dict[str, Any],
                **_kwargs: Any,
        ) -> dict[str, Any]:
            if (notes := data.get('user_notes')) is None:
                movement_notes, fee_notes = None, None
            elif len(notes) == 1:
                movement_notes, fee_notes = notes[0], None
            else:  # len == 2, enforced by validate.Length above
                movement_notes, fee_notes = notes

            if ((fee := data['fee']) is None) ^ (data['fee_asset'] is None):
                raise ValidationError(
                    message='fee and fee_asset must be provided together',
                    field_name='fee',
                )
            elif fee is None and fee_notes is not None:
                raise ValidationError(
                    message='fee_notes may only be provided when fee_amount is present',
                    field_name='fee_notes',
                )

            extra_data: AssetMovementExtraData = {}
            if (address := data['address']) is not None:
                extra_data['address'] = address

            if (tx_id := data['transaction_id']) is not None:
                extra_data['transaction_id'] = tx_id

            if (blockchain := data['blockchain']) is not None:
                extra_data['blockchain'] = blockchain

            if (unique_id := data['unique_id']) is not None:
                extra_data['reference'] = unique_id

            events = create_asset_movement_with_fee(
                fee=fee,
                asset=data['asset'],
                location=data['location'],
                unique_id=unique_id,
                timestamp=data['timestamp'],
                fee_asset=data['fee_asset'],
                event_type=data['event_type'],
                identifier=data.get('identifier'),
                event_identifier=data['event_identifier'],
                amount=data['amount'],
                extra_data=extra_data,
                fee_identifier=CreateHistoryEventSchema.history_event_context.get()['schema'].get_grouped_event_identifier(
                    data=data,
                    subtype=HistoryEventSubType.FEE,
                ),
                location_label=data['location_label'],
                movement_notes=movement_notes,
                fee_notes=fee_notes,
            ) if fee is not None else [AssetMovement(
                is_fee=False,
                asset=data['asset'],
                amount=data['amount'],
                location=data['location'],
                unique_id=unique_id,
                timestamp=data['timestamp'],
                identifier=data.get('identifier'),
                event_type=data['event_type'],
                extra_data=extra_data,
                event_identifier=data['event_identifier'],
                location_label=data['location_label'],
                notes=movement_notes,
            )]

            return {'events': events}

    class CreateSwapEventSchema(Schema):
        identifier = fields.Integer(required=True)
        timestamp = TimestampMSField(required=True)
        location = LocationField(required=True)
        spend_amount = AmountField(required=True, validate=validate.Range(min=ZERO, min_inclusive=False))  # noqa: E501
        spend_asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)  # noqa: E501
        receive_amount = AmountField(required=True, validate=validate.Range(min=ZERO, min_inclusive=False))  # noqa: E501
        receive_asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)  # noqa: E501
        fee_amount = FeeField(required=False, load_default=None, validate=validate.Range(min=ZERO, min_inclusive=False))  # noqa: E501
        fee_asset = AssetField(required=False, load_default=None, expected_type=Asset, form_with_incomplete_data=True)  # noqa: E501
        location_label = fields.String(required=False, load_default=None)
        unique_id = fields.String(required=False, load_default=None)
        user_notes = fields.List(fields.String(), required=False, validate=validate.Length(min=2, max=3))  # noqa: E501
        event_identifier = fields.String(required=False, load_default=None)

        @post_load
        def make_history_base_entry(self, data: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
            if (notes := data.get('user_notes')) is None:
                spend_notes, receive_notes, fee_notes = None, None, None
            elif len(notes) == 2:
                spend_notes, receive_notes = notes
                fee_notes = None
            else:  # len == 3, enforced by validate.Length above
                spend_notes, receive_notes, fee_notes = notes

            if ((fee_amount := data['fee_amount']) is None) ^ (data['fee_asset'] is None):
                raise ValidationError(
                    message='fee_amount and fee_asset must be provided together',
                    field_name='fee_amount',
                )
            elif fee_amount is None and fee_notes is not None:
                raise ValidationError(
                    message='fee_notes may only be provided when fee_amount is present',
                    field_name='fee_notes',
                )

            extra_data: SwapEventExtraData = {}
            if (unique_id := data['unique_id']) is not None:
                extra_data['reference'] = unique_id

            context_schema = CreateHistoryEventSchema.history_event_context.get()['schema']
            events = create_swap_events(
                timestamp=data['timestamp'],
                location=data['location'],
                spend_asset=data['spend_asset'],
                spend_amount=data['spend_amount'],
                receive_asset=data['receive_asset'],
                receive_amount=data['receive_amount'],
                fee_amount=fee_amount or ZERO,
                fee_asset=data['fee_asset'],
                location_label=data['location_label'],
                unique_id=data['unique_id'],
                spend_notes=spend_notes,
                receive_notes=receive_notes,
                fee_notes=fee_notes,
                identifier=data.get('identifier'),
                event_identifier=data['event_identifier'],
                receive_identifier=context_schema.get_grouped_event_identifier(
                    data=data,
                    subtype=HistoryEventSubType.RECEIVE,
                ),
                fee_identifier=context_schema.get_grouped_event_identifier(
                    data=data,
                    subtype=HistoryEventSubType.FEE,
                ),
                extra_data=extra_data,
            )
            return {'events': events}

    ENTRY_TO_SCHEMA: Final[dict[HistoryBaseEntryType, type[Schema]]] = {
        HistoryBaseEntryType.HISTORY_EVENT: CreateBaseHistoryEventSchema,
        HistoryBaseEntryType.ETH_BLOCK_EVENT: CreateEthBlockEventEventSchema,
        HistoryBaseEntryType.ETH_DEPOSIT_EVENT: CreateEthDepositEventEventSchema,
        HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT: CreateEthWithdrawalEventEventSchema,
        HistoryBaseEntryType.EVM_EVENT: CreateEvmEventSchema,
        HistoryBaseEntryType.ASSET_MOVEMENT_EVENT: CreateAssetMovementEventSchema,
        HistoryBaseEntryType.SWAP_EVENT: CreateSwapEventSchema,
    }

    def get_grouped_event_identifier(
            self,
            data: dict[str, Any],
            subtype: Literal[HistoryEventSubType.RECEIVE, HistoryEventSubType.FEE],
    ) -> int | None:
        """Retrieve grouped event's identifier, returns None for create."""
        return None

    @post_load
    def make_history_base_entry(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        entry_type = data.pop('entry_type')  # already used to decide schema
        exclude = () if self.include_identifier else ('identifier',)
        self.history_event_context.set({'schema': self})
        return self.ENTRY_TO_SCHEMA[entry_type](exclude=exclude).load(data)

    class Meta:  # need it to validate extra fields in make_history_base_entry
        unknown = INCLUDE


class EditHistoryEventSchema(CreateHistoryEventSchema):
    """Schema used when editing an existing event in the EVM transactions view"""
    include_identifier = True

    def get_grouped_event_identifier(
            self,
            data: dict[str, Any],
            subtype: Literal[HistoryEventSubType.RECEIVE, HistoryEventSubType.FEE],
    ) -> int | None:
        """Retrieve grouped event's identifier, returns None for create."""
        with self.database.conn.read_ctx() as cursor:
            result = cursor.execute("""
                SELECT identifier
                FROM history_events
                WHERE event_identifier = (
                    SELECT event_identifier
                    FROM history_events
                    WHERE identifier = ?
                )
                AND subtype = ?
            """, (data['identifier'], subtype.serialize())).fetchone()

            return result[0] if result else None


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
        data['identifier'] = -1  # can be any value because id will be set automatically
        return ManuallyTrackedBalance(**data)


class ManuallyTrackedBalanceEditSchema(ManuallyTrackedBalanceAddSchema):
    identifier = fields.Integer(required=True)

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
    """Prevents repeated oracle names, empty list and illegal values"""
    if (
        len(current_price_oracles) == 0 or
        len(current_price_oracles) != len(given_set := set(current_price_oracles))):
        raise ValidationError(
            'Current price oracles list should not be empty and should have no repeated entries',
        )

    if (invalid_oracles := given_set - SETTABLE_CURRENT_PRICE_ORACLES) != set():
        raise ValidationError(
            f'Invalid current price oracles given: {", ".join([str(x) for x in invalid_oracles])}. ',  # noqa: E501

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
    beacon_rpc_endpoint = fields.String(load_default=None)
    main_currency = AssetField(expected_type=AssetWithOracles, load_default=None)
    # TODO: Add some validation to this field
    date_display_format = fields.String(load_default=None)
    active_modules = fields.List(fields.String(), load_default=None)
    frontend_settings = fields.String(load_default=None)
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
    evmchains_to_skip_detection = fields.List(
        EvmChainLikeNameField,
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
    oracle_penalty_threshold_count = fields.Integer(
        load_default=None,
        validate=webargs.validate.Range(
            min=1,
            error='The count should be >= 1',
        ),
    )
    oracle_penalty_duration = fields.Integer(
        load_default=None,
        validate=webargs.validate.Range(
            min=1,
            error='The penalty should be >= 1 seconds',
        ),
    )
    auto_delete_calendar_entries = fields.Boolean(load_default=None)
    auto_create_calendar_reminders = fields.Boolean(load_default=None)
    ask_user_upon_size_discrepancy = fields.Boolean(load_default=None)
    auto_detect_tokens = fields.Boolean(load_default=None)
    csv_export_delimiter = fields.String(load_default=None)
    use_unified_etherscan_api = fields.Boolean(load_default=None)

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
            beacon_rpc_endpoint=data['beacon_rpc_endpoint'],
            main_currency=data['main_currency'],
            date_display_format=data['date_display_format'],
            submit_usage_analytics=data['submit_usage_analytics'],
            active_modules=data['active_modules'],
            frontend_settings=data['frontend_settings'],
            btc_derivation_gap_limit=data['btc_derivation_gap_limit'],
            calculate_past_cost_basis=data['calculate_past_cost_basis'],
            display_date_in_localtime=data['display_date_in_localtime'],
            historical_price_oracles=data['historical_price_oracles'],
            current_price_oracles=data['current_price_oracles'],
            pnl_csv_with_formulas=data['pnl_csv_with_formulas'],
            pnl_csv_have_summary=data['pnl_csv_have_summary'],
            ssf_graph_multiplier=data['ssf_graph_multiplier'],
            non_syncing_exchanges=data['non_syncing_exchanges'],
            evmchains_to_skip_detection=data['evmchains_to_skip_detection'],
            cost_basis_method=data['cost_basis_method'],
            treat_eth2_as_eth=data['treat_eth2_as_eth'],
            eth_staking_taxable_after_withdrawal_enabled=data['eth_staking_taxable_after_withdrawal_enabled'],
            address_name_priority=data['address_name_priority'],
            include_fees_in_cost_basis=data['include_fees_in_cost_basis'],
            infer_zero_timed_balances=data['infer_zero_timed_balances'],
            query_retry_limit=data['query_retry_limit'],
            connect_timeout=data['connect_timeout'],
            read_timeout=data['read_timeout'],
            oracle_penalty_threshold_count=data['oracle_penalty_threshold_count'],
            oracle_penalty_duration=data['oracle_penalty_duration'],
            auto_delete_calendar_entries=data['auto_delete_calendar_entries'],
            auto_create_calendar_reminders=data['auto_create_calendar_reminders'],
            ask_user_upon_size_discrepancy=data['ask_user_upon_size_discrepancy'],
            auto_detect_tokens=data['auto_detect_tokens'],
            csv_export_delimiter=data['csv_export_delimiter'],
            use_unified_etherscan_api=data['use_unified_etherscan_api'],
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


class ManualBalanceQuerySchema(AsyncQueryArgumentSchema, AssetValueThresholdSchema):
    """Schema for querying manual balances with optional USD threshold filtering"""


class ExternalServiceSchema(Schema):
    name = SerializableEnumField(enum_class=ExternalService, required=True)
    api_key = fields.String(required=False)
    username = fields.String(required=False)
    password = fields.String(required=False)

    @validates_schema
    def validate_external_service(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data.get('api_key') is None:
            if data['name'] != ExternalService.MONERIUM:
                raise ValidationError(
                    message=f'an api key is needed for {data["name"].name.lower()}',
                    field_name='api_key',
                )

        elif None not in (data.get('username'), data.get('password')):
            raise ValidationError(
                message='username and password is only given for monerium',
                field_name='username',
            )

        if data['name'] == ExternalService.MONERIUM and None in (data.get('username'), data.get('password')):  # noqa: E501
            raise ValidationError(
                message='monerium needs a username and password',
                field_name='username',
            )

    @post_load
    def make_external_service(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> ExternalServiceApiCredentials:
        """Used when encoding an external resource given in via the API"""
        api_key = data.get('api_key')
        return ExternalServiceApiCredentials(
            service=data['name'],
            api_key=api_key if api_key is not None else data['username'],
            api_secret=data.get('password'),
        )


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
    api_secret = ApiSecretField(load_default=None)
    passphrase = fields.String(load_default=None)
    kraken_account_type = SerializableEnumField(enum_class=KrakenAccountType, load_default=None)
    binance_markets = fields.List(fields.String(), load_default=None)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        location = data['location']
        if data['api_secret'] is None and location not in EXCHANGES_WITHOUT_API_SECRET:
            raise ValidationError(
                f'{location.name.title()} requires an API secret',
                field_name='api_secret',
            )

        if location in EXCHANGES_WITH_PASSPHRASE and not data.get('passphrase'):
            raise ValidationError(
                f'{location.name.title()} requires a passphrase',
                field_name='passphrase',
            )


class ExchangesDataResourceSchema(Schema):
    location = LocationField(limit_to=ALL_SUPPORTED_EXCHANGES, load_default=None)


class ExchangeEventsQuerySchema(AsyncQueryArgumentSchema):
    name = fields.String(required=False)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)


class ExchangesResourceRemoveSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)


class ExchangeBalanceQuerySchema(AsyncQueryArgumentSchema, AssetValueThresholdSchema):
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, load_default=None)
    ignore_cache = fields.Boolean(load_default=False)


class BlockchainBalanceQuerySchema(AsyncQueryArgumentSchema, AssetValueThresholdSchema):
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


class AsyncDirectoryPathSchema(AsyncQueryArgumentSchema):
    directory_path = DirectoryField(load_default=None)


class AsyncFilePathSchema(AsyncQueryArgumentSchema):
    filepath = FileField(required=True, allowed_extensions=['.json'])

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        """
        Change multipart/form-data to a file object if it's in that form,
        so that it can be read with the same code
        """
        if isinstance(data['filepath'], FileStorage):
            # TODO cleanup: https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=65410141  # noqa: E501
            _, tmpfilepath = tempfile.mkstemp()
            data['filepath'].save(tmpfilepath)
            data['filepath'] = Path(tmpfilepath)

        return data


class HistoryProcessingExportSchema(AsyncDirectoryPathSchema, TimestampRangeSchema):
    """Schema for exporting history events"""


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
        valid_ordering_attr = {None, 'timestamp', 'pnl_taxable', 'pnl_free', 'asset'}

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
            if not is_potential_ens_name(address_string):
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
            if not (
                is_potential_ens_name(address) or
                is_valid_btc_address(address) or
                is_valid_bitcoin_cash_address(address)
            ):
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
            if not is_potential_ens_name(address) and not is_valid_substrate_address(chain, address):  # noqa: E501
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
    if not is_potential_ens_name(given_address):
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


def _resolve_ens_name(
        ethereum_inquirer: EthereumInquirer,
        name: str,
        field_name: str,
) -> ChecksumEvmAddress:
    try:
        resolved_address = ethereum_inquirer.ens_lookup(name)
    except (RemoteError, InputError) as e:
        raise ValidationError(
            f'Given ENS name {name} could not be resolved for Ethereum'
            f' due to: {e!s}',
            field_name=field_name,
        ) from None

    if resolved_address is None:
        raise ValidationError(
            f'Given ENS name {name} could not be resolved for Ethereum',
            field_name=field_name,
        ) from None

    log.info(f'Resolved ENS {name} to {(address := to_checksum_address(resolved_address))}')
    return address


def _transform_evm_address(
        ethereum_inquirer: EthereumInquirer,
        given_address: str,
) -> ChecksumEvmAddress:
    try:
        address = to_checksum_address(given_address)
    except ValueError:
        # Validation will only let .eth names come here. Let's see if it resolves to anything
        address = _resolve_ens_name(
            ethereum_inquirer=ethereum_inquirer,
            name=given_address,
            field_name='address',
        )

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
    if not is_potential_ens_name(given_address):
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


class ChainTypeSchema(AsyncQueryArgumentSchema):
    chain_type = SerializableEnumField(
        enum_class=ChainType,
        required=True,
        exclude_types=(ChainType.EVMLIKE,),
    )


class BlockchainAccountListSchema(Schema):
    accounts = fields.List(fields.Nested(BlockchainAccountDataSchema), required=True)


class ChainTypeAccountSchema(ChainTypeSchema, BlockchainAccountListSchema):
    ...


class EvmAccountsPutSchema(BlockchainAccountListSchema, AsyncQueryArgumentSchema):
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
        _validate_blockchain_account_schemas(data, operator.itemgetter('address'))
        data.pop('blockchain')

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        _transform_evm_addresses(data=data, ethereum_inquirer=self.ethereum_inquirer)
        return data


class BlockchainAccountsPatchSchema(AsyncQueryArgumentSchema):
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
        _validate_blockchain_account_schemas(data, operator.itemgetter('address'))

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
        elif data['blockchain'].is_evm_or_evmlike():
            _transform_evm_addresses(data=data, ethereum_inquirer=self.ethereum_inquirer)
        elif data['blockchain'].is_substrate():
            for idx, account in enumerate(data['accounts']):
                data['accounts'][idx]['address'] = _transform_substrate_address(
                    ethereum_inquirer=self.ethereum_inquirer,
                    given_address=account['address'],
                    chain=data['blockchain'],
                )

        return data


class BlockchainAccountsPutSchema(BlockchainAccountsPatchSchema):
    ...


class StringAccountSchema(Schema):
    accounts = fields.List(fields.String(), required=True)


class BlockchainTypeAccountsDeleteSchema(ChainTypeSchema, StringAccountSchema):
    """Used to manage accounts in different chains filtering by chain type"""


class BlockchainAccountsDeleteSchema(StringAccountSchema, AsyncQueryArgumentSchema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501

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
        if data['blockchain'].is_evm_or_evmlike():
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
    data = DelimitedOrNormalList(fields.String(required=True), required=True)


class AssetsPostSchema(DBPaginationSchema, DBOrderBySchema):
    name = fields.String(load_default=None)
    symbol = fields.String(load_default=None)
    asset_type = SerializableEnumField(enum_class=AssetType, load_default=None)
    address = EvmAddressField(load_default=None)
    evm_chain = EvmChainNameField(load_default=None)
    ignored_assets_handling = SerializableEnumField(enum_class=IgnoredAssetsHandling, load_default=IgnoredAssetsHandling.NONE)  # noqa: E501
    show_user_owned_assets_only = fields.Boolean(load_default=False)
    show_whitelisted_assets_only = fields.Boolean(load_default=False)
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
            show_whitelisted_assets_only=data['show_whitelisted_assets_only'],
            ignored_assets_handling=data['ignored_assets_handling'],
        )
        return {'filter_query': filter_query}


class AssetsSearchLevenshteinSchema(Schema):
    value = fields.String(load_default=None)
    evm_chain = EvmChainNameField(load_default=None)
    address = EvmAddressField(load_default=None)
    limit = fields.Integer(required=True)
    search_nfts = fields.Boolean(load_default=False)

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__()
        self.db = db

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['value'] is None and data['address'] is None:
            raise ValidationError('Either value or address need to be provided')

    @post_load
    def make_levenshtein_search_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = LevenshteinFilterQuery.make(
            and_op=True,
            substring_search=data['value'].strip().casefold() if data['value'] else None,
            chain_id=data['evm_chain'],
            address=data['address'],
            ignored_assets_handling=IgnoredAssetsHandling.EXCLUDE,  # do not check ignored assets at search  # noqa: E501
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
            ignored_assets_handling=IgnoredAssetsHandling.EXCLUDE,  # do not check ignored assets at search  # noqa: E501
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
                message="Can't replace an evm token",
                field_name='source_identifier',
            )

        if data['source_identifier'].lower() == data['target_asset'].identifier.lower():
            raise ValidationError(
                message="Can't merge the same asset to itself",
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


class LocationAssetMappingsBaseSchema(Schema):
    location = LocationField(limit_to=ALL_SUPPORTED_EXCHANGES, allow_none=True)


class LocationAssetMappingsPostSchema(DBPaginationSchema, LocationAssetMappingsBaseSchema):
    location_symbol = fields.String(load_default=None)

    @post_load
    def make_location_asset_mappings_post_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        """Make and return LocationAssetMappingsFilterQuery instance. `limit` and `offset` are used
        for pagination, and optional `location` to filter by location. If `location` is explicitly
        passed with `null` value (parsed as None here) then that is used to filter the common
        mappings."""
        filter_query = LocationAssetMappingsFilterQuery.make(
            location='common' if 'location' in data and data['location'] is None else data.get('location'),  # noqa: E501
            limit=data['limit'],
            location_symbol=data['location_symbol'],
            offset=data['offset'],
        )
        return {'filter_query': filter_query}


class LocationAssetMappingUpdateEntrySchema(LocationAssetMappingsBaseSchema):
    asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)
    location_symbol = fields.String(required=True)

    @post_load()
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> LocationAssetMappingUpdateEntry:
        try:
            return LocationAssetMappingUpdateEntry.deserialize(data)
        except DeserializationError as e:
            raise ValidationError(f'Could not deserialize data: {e!s}') from e


class LocationAssetMappingDeleteEntrySchema(LocationAssetMappingsBaseSchema):
    location_symbol = fields.String(required=True)

    @post_load()
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> LocationAssetMappingDeleteEntry:
        try:
            return LocationAssetMappingDeleteEntry.deserialize(data)
        except DeserializationError as e:
            raise ValidationError(f'Could not deserialize data: {e!s}') from e


class LocationAssetMappingsUpdateSchema(Schema):
    entries = NonEmptyList(fields.Nested(LocationAssetMappingUpdateEntrySchema), required=True)


class LocationAssetMappingsDeleteSchema(Schema):
    entries = NonEmptyList(fields.Nested(LocationAssetMappingDeleteEntrySchema), required=True)


class CounterpartyAssetMappingsBaseSchema(Schema):
    counterparty = EvmCounterpartyField(required=True)

    def __init__(self, chain_aggregator: 'ChainsAggregator') -> None:
        super().__init__()
        self.declared_fields['counterparty'].set_counterparties(  # type: ignore
            counterparties={x.identifier for x in chain_aggregator.get_all_counterparties()},
        )


class CounterpartyAssetMappingUpdateEntrySchema(CounterpartyAssetMappingsBaseSchema):
    asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)
    counterparty_symbol = fields.String(required=True)

    @post_load()
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> CounterpartyAssetMappingUpdateEntry:
        try:
            return CounterpartyAssetMappingUpdateEntry.deserialize(data)
        except DeserializationError as e:
            raise ValidationError(f'Could not deserialize data: {e!s}') from e


class CounterpartyAssetMappingsPostSchema(DBPaginationSchema, CounterpartyAssetMappingsBaseSchema):
    counterparty = EvmCounterpartyField(load_default=None)
    counterparty_symbol = fields.String(load_default=None)

    @post_load
    def make_counterparty_asset_mappings_post_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = CounterpartyAssetMappingsFilterQuery.make(
            limit=data['limit'],
            offset=data['offset'],
            counterparty=data['counterparty'],
            counterparty_symbol=data['counterparty_symbol'],
        )
        return {'filter_query': filter_query}


class CounterpartyAssetMappingDeleteEntrySchema(CounterpartyAssetMappingsBaseSchema):
    counterparty_symbol = fields.String(required=True)

    @post_load()
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> CounterpartyAssetMappingDeleteEntry:
        try:
            return CounterpartyAssetMappingDeleteEntry.deserialize(data)
        except DeserializationError as e:
            raise ValidationError(f'Could not deserialize data: {e!s}') from e


def create_counterparty_asset_mappings_schema(
        entry_schema_class: type[CounterpartyAssetMappingDeleteEntrySchema | CounterpartyAssetMappingUpdateEntrySchema],  # noqa: E501
        chain_aggregator: 'ChainsAggregator',
) -> Any:
    class DynamicCounterpartyAssetMappingsSchema(Schema):
        entries = NonEmptyList(
            fields.Nested(entry_schema_class(chain_aggregator=chain_aggregator)),
            required=True,
        )

    return DynamicCounterpartyAssetMappingsSchema()


class EthStakingCommonFilterSchema(Schema):
    """Schema for querying ethereum staking common filters"""
    addresses = DelimitedOrNormalList(EvmAddressField, load_default=None)
    validator_indices = DelimitedOrNormalList(fields.Integer(), load_default=None)
    status = StrEnumField(
        enum_class=PerformanceStatusFilter,
        load_default=PerformanceStatusFilter.ALL,
    )

    def __init__(self, dbhandler: 'DBHandler') -> None:
        super().__init__()
        self.database = dbhandler

    def get_filtered_indices(
            self,
            addresses: list[ChecksumEvmAddress] | None,
            given_indices: list[int] | None,
            status: PerformanceStatusFilter,
    ) -> set[int] | None:
        """Filter the indices of the validators to forward only validator indices
        further in the code. This is used only by validators endpoint and daily stats endpoint.

        The performance endpoint does not call this and does this logic inside the
        performance calculation since it's needed for the cache.

        What's more it's important to note that status Pending would only count from
        the moment they are seen by the beacon chain as that's when a validator index exists.
        """
        with self.database.conn.read_ctx() as cursor:
            all_validators = {x[0] for x in cursor.execute('SELECT validator_index FROM eth2_validators')}  # noqa: E501

        validator_indices, associated_indices, status_indices = all_validators, all_validators, all_validators  # noqa: E501
        no_filter = True
        if given_indices:
            validator_indices = set(given_indices)
            no_filter = False

        dbeth2 = DBEth2(self.database)
        if addresses:
            with self.database.conn.read_ctx() as cursor:
                associated_indices = dbeth2.get_associated_with_addresses_validator_indices(
                    cursor=cursor,
                    addresses=addresses,
                )
            no_filter = False

        if status != PerformanceStatusFilter.ALL:
            with self.database.conn.read_ctx() as cursor:
                if status == PerformanceStatusFilter.ACTIVE:
                    status_indices = dbeth2.get_active_validator_indices(cursor)
                else:  # can only be EXITED
                    status_indices = dbeth2.get_exited_validator_indices(cursor)

            no_filter = False

        return None if no_filter else validator_indices & associated_indices & status_indices


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
        fields.Tuple(
            (AssetField(expected_type=Asset, required=True), TimestampField(required=True)),
            required=True,
        ),
        required=True,
        validate=webargs.validate.Length(min=1),
    )
    only_cache_period = fields.Integer(
        load_default=None,
        validate=webargs.validate.Range(min=1, error='Cache period must be a positive integer'),
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


class AssetResetRequestSchema(AsyncQueryArgumentSchema):
    reset = fields.String(required=True)
    ignore_warnings = fields.Boolean(load_default=False)


class NamedEthereumModuleDataSchema(Schema):
    module_name = fields.String(
        validate=webargs.validate.OneOf(choices=list(typing.get_args(ModuleName) + typing.get_args(OnlyPurgeableModuleName))),  # noqa: E501
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

    @validates_schema
    def validate_manual_price_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['from_asset'] == data['to_asset']:
            raise ValidationError(
                message='The from and to assets must be different',
                field_name='from_asset',
            )


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


class Eth2ValidatorsGetSchema(EthStakingCommonFilterSchema, AsyncIgnoreCacheQueryArgumentSchema):

    @post_load
    def make_eth_validators_get_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        validator_indices = self.get_filtered_indices(
            addresses=data['addresses'],
            given_indices=data['validator_indices'],
            status=data['status'],
        )
        return {
            'async_query': data['async_query'],
            'ignore_cache': data['ignore_cache'],
            'validator_indices': validator_indices,
        }


class Eth2DailyStatsSchema(
        AsyncQueryArgumentSchema,
        TimestampRangeSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
        EthStakingCommonFilterSchema,
):

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
        validator_indices = self.get_filtered_indices(
            addresses=data['addresses'],
            given_indices=data['validator_indices'],
            status=data['status'],
        )
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
            validator_indices=validator_indices,
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


class AssetsImportingSchema(AsyncQueryArgumentSchema):
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


class AssetsImportingFromFormSchema(AsyncQueryArgumentSchema):
    file = FileField(allowed_extensions=['.zip', '.json'], required=True)


class ReverseEnsSchema(AsyncIgnoreCacheQueryArgumentSchema):
    ethereum_addresses = fields.List(EvmAddressField(), required=True)


class ResolveEnsSchema(AsyncIgnoreCacheQueryArgumentSchema):
    name = fields.String(required=True)


class OptionalAddressesListSchema(Schema):
    addresses = fields.List(EvmAddressField(required=True), load_default=None)


class AddressWithOptionalBlockchainSchema(Schema):
    address = fields.String(required=True)
    blockchain = BlockchainField(load_default=None)

    @post_load()
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> OptionalChainAddress:
        if (
            data['blockchain'] is not None and
            cast('SupportedBlockchain', data['blockchain']).get_chain_type() == ChainType.EVM
        ):
            try:
                address = to_checksum_address(data['address'])
            except ValueError as e:
                raise ValidationError(
                    f'Given value {data["address"]} is not a valid {data["blockchain"]} address',
                    field_name='address',
                ) from e
        else:
            address = data['address']

        return OptionalChainAddress(
            address=address,
            blockchain=data['blockchain'],
        )

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        """
        Check that bitcoin and polkadot addresses are correct when the blockchain
        param is provided. EVM chains are checked in the post_load logic where we checksum
        the address if it is not.
        """
        if data['blockchain'] is None:
            return

        blockchain = cast('SupportedBlockchain', data['blockchain'])
        if ((
            blockchain == SupportedBlockchain.BITCOIN and
            is_valid_btc_address(data['address']) is False
        ) or (
            blockchain == SupportedBlockchain.BITCOIN_CASH and
            is_valid_bitcoin_cash_address(data['address']) is False
        ) or (
            blockchain.get_chain_type() == ChainType.SUBSTRATE and
            is_valid_substrate_address(chain=blockchain, value=data['address']) is False  # type: ignore  # expects polkadot or kusama
        )):
            raise ValidationError(
                f'Given value {data["address"]} is not a {blockchain} address',
                field_name='address',
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


class QueryAddressbookSchema(
    BaseAddressbookSchema,
    OptionalAddressesWithBlockchainsListSchema,
    DBPaginationSchema,
    DBOrderBySchema,
):
    """Schema for querying addressbook entries"""
    name_substring = fields.String(load_default=None)
    blockchain = BlockchainField(load_default=None)

    @post_load
    def make_get_addressbook_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = AddressbookFilterQuery.make(
            limit=data['limit'],
            offset=data['offset'],
            blockchain=data['blockchain'],
            substring_search=data['name_substring'],
            optional_chain_addresses=data['addresses'],
            order_by_rules=create_order_by_rules_list(data=data),
        )
        return {
            'filter_query': filter_query,
            'book_type': data['book_type'],
        }


class AddressbookEntrySchema(AddressWithOptionalBlockchainSchema):
    name = fields.String(required=True)

    @post_load()
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        optional_chain_addresses = super().transform_data(data)
        return AddressbookEntry(
            address=optional_chain_addresses.address,
            name=data['name'],
            blockchain=optional_chain_addresses.blockchain,
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


class ConnectToRPCNodes(RpcNodeSchema):
    identifier = fields.Integer(load_default=None)


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
                BASE_ETHERSCAN_NODE_NAME,
                GNOSIS_ETHERSCAN_NODE_NAME,
                SCROLL_ETHERSCAN_NODE_NAME,
                BINANCE_SC_ETHERSCAN_NODE_NAME,
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

    def __init__(self, dbhandler: 'DBHandler') -> None:
        super().__init__()
        self.dbhandler = dbhandler

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.dbhandler.is_etherscan_node(data['identifier']):
            raise ValidationError(
                message="Can't delete an etherscan node",
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
            query_event_subtypes=[HistoryEventSubType.REWARD],
            value_event_subtypes=[HistoryEventSubType.REWARD],
            exclude_event_subtypes=None,
        )
        query_dict.update({'location': location})
        return query_dict


class EnsAvatarsSchema(Schema):
    ens_name = fields.String(required=True, validate=is_potential_ens_name)


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
        fields.String(required=True, validate=is_potential_ens_name),
        load_default=None,
    )


class Eth2StakePerformanceSchema(
        EthStakingCommonFilterSchema,
        TimestampRangeSchema,
        AsyncIgnoreCacheQueryArgumentSchema,
        DBPaginationSchema,
):
    """Schema for querying ethereum staking performance"""

    @post_load
    def make_staking_performance_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        """Just give defaults for limit and offset. Other api calls don't give defaults
        as they are checked inside the filters and skip filter creation. In this API
        call we do pagination outside the DB so this is needed."""
        if data['limit'] is None:
            data['limit'] = 10
        if data['offset'] is None:
            data['offset'] = 0

        if data['validator_indices'] is not None:
            data['validator_indices'] = set(data['validator_indices'])

        return data


class SkippedExternalEventsExportSchema(Schema):
    directory_path = DirectoryField(load_default=None)


class ExportHistoryEventSchema(HistoryEventSchema, AsyncQueryArgumentSchema):
    """Schema for querying history events"""
    directory_path = DirectoryField(required=True)

    def make_extra_filtering_arguments(self, data: dict[str, Any]) -> dict[str, Any]:
        return {}

    def generate_fields_post_validation(self, data: dict[str, Any]) -> dict[str, Any]:
        extra_fields = {}
        if (directory_path := data.get('directory_path')) is not None:
            extra_fields['directory_path'] = directory_path
        if (async_query := data.get('async_query')) is not None:
            extra_fields['async_query'] = async_query
        return extra_fields


class ExportHistoryDownloadSchema(Schema):
    """Schema for downloading history events CSVs."""
    file_path = fields.String(required=True)


class AccountingRuleIdSchema(Schema):
    event_type = SerializableEnumField(enum_class=HistoryEventType, required=True)
    event_subtype = SerializableEnumField(enum_class=HistoryEventSubType, required=True)
    counterparty = fields.String(required=False, load_default=None)


class LinkedAccountingSetting(Schema):
    """
    For some accounting rules properties we allow to link its value to an accounting settings.
    Value will be the value (true or false) given to the property by default and linked_setting
    if provided will be the name of the setting from which the rule's property will take its value
    """
    value = fields.Boolean(required=True)
    linked_setting = fields.String(
        validate=webargs.validate.OneOf(choices=get_args(LINKABLE_ACCOUNTING_SETTINGS_NAME)),
        load_default=None,
    )


class CreateAccountingRuleSchema(AccountingRuleIdSchema):
    taxable = fields.Nested(LinkedAccountingSetting)
    count_entire_amount_spend = fields.Nested(LinkedAccountingSetting)
    count_cost_basis_pnl = fields.Nested(LinkedAccountingSetting)
    accounting_treatment = SerializableEnumField(enum_class=TxAccountingTreatment, required=False, load_default=None)  # noqa: E501

    def _create_settings(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        rule = BaseEventSettings(
            taxable=data['taxable']['value'],
            count_entire_amount_spend=data['count_entire_amount_spend']['value'],
            count_cost_basis_pnl=data['count_cost_basis_pnl']['value'],
            accounting_treatment=data['accounting_treatment'],
        )
        links = {
            key: data[key]['linked_setting']
            for key in get_args(LINKABLE_ACCOUNTING_PROPERTIES)
            if data[key]['linked_setting'] is not None
        }
        return {
            'rule': rule,
            'event_type': data['event_type'],
            'event_subtype': data['event_subtype'],
            'counterparty': data['counterparty'],
            'links': links,
        }

    @post_load
    def prepare_rule_info(
            self,
            data: dict[str, Any],
            **kwargs: Any,
    ) -> dict[str, Any]:
        return self._create_settings(data, **kwargs)


class EditAccountingRuleSchema(CreateAccountingRuleSchema):
    identifier = fields.Integer(required=True)

    @post_load
    def prepare_rule_info(
            self,
            data: dict[str, Any],
            **kwargs: Any,
    ) -> dict[str, Any]:
        return {'identifier': data['identifier'], **self._create_settings(data, **kwargs)}


class AccountingRulesQuerySchema(
        TypesAndCounterpatiesFiltersSchema,
        DBPaginationSchema,
        DBOrderBySchema,
):

    @post_load
    def make_rules_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = AccountingRulesFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_fields=['identifier', 'type', 'subtype', 'counterparty'],
                default_ascending=[False, True, True, True],
            ),
            limit=data['limit'],
            offset=data['offset'],
            event_types=data['event_types'],
            event_subtypes=data['event_subtypes'],
            counterparties=data['counterparties'],
        )
        return {
            'filter_query': filter_query,
        }


class AccountingRuleConflictResolutionSchema(Schema):
    local_id = fields.Integer(required=True, validate=webargs.validate.Range(
        min=0,
        error='local_id must be an integer >= 0',
    ))
    solve_using = fields.String(
        validate=webargs.validate.OneOf(choices=('local', 'remote')),
        required=True,
    )


class MultipleAccountingRuleConflictsResolutionSchema(Schema):
    conflicts = fields.List(
        fields.Nested(AccountingRuleConflictResolutionSchema),
        required=False,
        load_default=None,
    )
    solve_all_using = fields.String(
        validate=webargs.validate.OneOf(choices=('local', 'remote')),
        required=False,
        load_default=None,
    )

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        """Check that the endpoint receives either conflicts or solve_all_using"""
        if (
            (data['conflicts'] is None and data['solve_all_using'] is None) or
            (data['conflicts'] is not None and data['solve_all_using'] is not None)
        ):
            raise ValidationError(
                message='Conflict resolution can either choose to solve all or a subset but not both or none',  # noqa: E501
                field_name='conflicts',
            )

    @post_load
    def extract_conflicts(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        processed_entries = [
            (conflict['local_id'], conflict['solve_using'])
            for conflict in data['conflicts']
        ] if data['conflicts'] is not None else []
        return {'conflicts': processed_entries, 'solve_all_using': data['solve_all_using']}


class AccountingRuleConflictsPagination(DBPaginationSchema):
    @post_load
    def make_rules_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        filter_query = PaginatedFilterQuery.make(
            limit=data['limit'],
            offset=data['offset'],
            order_by_rules=[('accounting_rules.identifier', False)],
        )
        return {'filter_query': filter_query}


class SingleTokenSchema(Schema):
    token = AssetField(expected_type=EvmToken, required=True)


class SpamTokenListSchema(Schema):
    tokens = fields.List(AssetField(expected_type=EvmToken), required=True)


def _validate_address_with_blockchain(
        address: BlockchainAddress,
        blockchain: SupportedBlockchain,
) -> None:
    """Validate the provided address using the format in the given blockchain"""
    if ((
        blockchain == SupportedBlockchain.BITCOIN and
        not is_valid_btc_address(address)
    ) or (
        blockchain == SupportedBlockchain.BITCOIN_CASH and
        not is_valid_bitcoin_cash_address(address)
    ) or (
        blockchain.get_chain_type() == ChainType.SUBSTRATE and
        not is_valid_substrate_address(chain=blockchain, value=address)  # type: ignore  # expects polkadot or kusama
    ) or (
        blockchain.is_evm_or_evmlike() and
        not to_checksum_address(address) == address
    )):
        raise ValidationError(
            f'Given value {address} is not a {blockchain} address',
            field_name='address',
        )


class AnyBlockchainAddress(Schema):
    """
    Schema for two fields, one being the address field and the other the
    blockchain where it belongs. The address can belong to any of the chains that we currently
    support and it will check if the format is correct for the blockchain.
    """
    address = fields.String(load_default=None)
    blockchain = BlockchainField(load_default=None)

    def __init__(
            self,
            *args: Any,
            allow_nullable_blockchain: bool = False,
            **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        # When allow_nullable_blockchain is True then the blockchain field is not required
        # if the address field has a non None value
        self.allow_nullable_blockchain = allow_nullable_blockchain

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        """Check that the combination of address and blockchain are correct"""
        if (data['address'] is None) ^ (data['blockchain'] is None):
            if self.allow_nullable_blockchain is True:
                return

            raise ValidationError(
                'If any of address or blockchain is provided both need to be provided',
            )

        if data['blockchain'] is None:
            return

        _validate_address_with_blockchain(
            address=data['address'],
            blockchain=data['blockchain'],
        )


class CalendarCommonEntrySchema(AnyBlockchainAddress):
    name = fields.String(required=True)
    description = fields.String(load_default=None)
    counterparty = EvmCounterpartyField(load_default=None)
    color = ColorField(load_default=None)
    auto_delete = fields.Boolean(required=True)

    def __init__(self, chain_aggregator: 'ChainsAggregator') -> None:
        super().__init__()
        self.declared_fields['counterparty'].set_counterparties(  # type: ignore
            counterparties={x.identifier for x in chain_aggregator.get_all_counterparties()},
        )


class NewCalendarEntrySchema(CalendarCommonEntrySchema):
    timestamp = TimestampField(required=True)

    @post_load
    def make_calendar_entry(self, data: dict[str, Any], **_kwargs: dict[str, Any]) -> dict[str, Any]:  # noqa: E501
        return {
            'calendar': CalendarEntry(
                identifier=data.get('identifier', 0),  # not present here but used in UpdateCalendarSchema  # noqa: E501
                name=data['name'],
                timestamp=data['timestamp'],
                description=data['description'],
                counterparty=data['counterparty'],
                address=data['address'],
                blockchain=data['blockchain'],
                color=data['color'],
                auto_delete=data['auto_delete'],
            ),
        }


class UpdateCalendarSchema(NewCalendarEntrySchema, IntegerIdentifierSchema):
    ...


class QueryCalendarSchema(
        DBPaginationSchema,
        TimestampRangeSchema,
        DBOrderBySchema,
):
    name = fields.String(load_default=None)
    description = fields.String(load_default=None)
    counterparty = EvmCounterpartyField(load_default=None)
    accounts = fields.List(
        fields.Nested(AnyBlockchainAddress(allow_nullable_blockchain=True)),
        load_default=None,
    )
    identifiers = fields.List(fields.Integer, load_default=None)
    to_timestamp = TimestampField(load_default=None)

    def __init__(self, chain_aggregator: 'ChainsAggregator') -> None:
        super().__init__()
        self.declared_fields['counterparty'].set_counterparties(  # type: ignore
            counterparties={x.identifier for x in chain_aggregator.get_all_counterparties()},
        )

    @post_load
    def make_calendar_query(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        accounts = None
        if data['accounts'] is not None:
            accounts = [
                OptionalBlockchainAddress(
                    address=account['address'],
                    blockchain=account['blockchain'],
                ) for account in data['accounts']
            ]

        filter_query = CalendarFilterQuery.make(
            order_by_rules=create_order_by_rules_list(
                data,
                default_order_by_fields=['timestamp'],
                default_ascending=[False],
            ),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            name=data['name'],
            description=data['description'],
            counterparty=data['counterparty'],
            addresses=accounts,
            identifiers=data['identifiers'],
        )
        return {'filter_query': filter_query}


class CalendarReminderCommonEntrySchema(Schema):
    event_id = fields.Integer(required=True)
    secs_before = fields.Integer(
        required=True,
        validate=webargs.validate.Range(min=0, error='secs_before has to be >= 0'),
    )


class NewCalendarReminderSchema(CalendarReminderCommonEntrySchema):

    @staticmethod
    def _process_reminder(data: dict[str, Any]) -> ReminderEntry:
        return ReminderEntry(
            identifier=data.get('identifier', 0),  # not present when creating a new reminder but used in UpdateCalendarReminderSchema. Using default 0 since it is ignored when doing the creation  # noqa: E501
            secs_before=data['secs_before'],
            event_id=data['event_id'],
        )

    @post_load
    def make_calendar_entry(self, data: dict[str, Any], **_kwargs: dict[str, Any]) -> ReminderEntry:  # noqa: E501
        return self._process_reminder(data)


class NewCalendarReminderListSchema(Schema):
    reminders = fields.List(fields.Nested(NewCalendarReminderSchema))


class UpdateCalendarReminderSchema(NewCalendarReminderSchema, IntegerIdentifierSchema):
    @post_load
    def make_calendar_entry(self, data: dict[str, Any], **_kwargs: dict[str, Any]) -> dict[str, Any]:  # noqa: E501
        return {'reminder': self._process_reminder(data)}


class HistoricalPerAssetBalanceSchema(SnapshotTimestampQuerySchema, AsyncQueryArgumentSchema):
    asset = AssetField(expected_type=Asset, load_default=None)


class HistoricalPricesPerAssetSchema(AsyncQueryArgumentSchema, TimestampRangeSchema):
    interval = fields.Integer(
        strict=True,
        required=True,
        validate=webargs.validate.Range(min=0, error='interval has to be a positive integer'),
    )
    only_cache_period = fields.Integer(
        load_default=None,
        validate=webargs.validate.Range(min=1, error='Cache period must be a positive integer'),
    )
    exclude_timestamps = fields.List(TimestampField(), load_default=list)
    asset = AssetField(expected_type=Asset, required=True)

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['to_timestamp'] <= data['from_timestamp']:
            raise ValidationError(
                message='from_timestamp must be smaller than to_timestamp',
                field_name='from_timestamp',
            )

    @post_load
    def transform_data(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> dict[str, Any]:
        """Align timestamps to interval boundaries.

        - Rounds down `from_timestamp` to nearest multiple of interval
        - Rounds up `to_timestamp` to nearest multiple of interval but also makes
        sure it's not in the future
        """
        interval = data['interval']
        data['exclude_timestamps'] = set(data['exclude_timestamps'])
        data['from_timestamp'] = (data['from_timestamp'] // interval) * interval
        data['to_timestamp'] = min(((data['to_timestamp'] + interval - 1) // interval) * interval, ts_now())  # noqa: E501
        return data


class RefreshProtocolDataSchema(AsyncQueryArgumentSchema):
    cache_protocol = SerializableEnumField(
        enum_class=ProtocolsWithCache,
        required=True,
    )


class RefetchEvmTransactionsSchema(AsyncQueryArgumentSchema, TimestampRangeSchema):
    address = EvmAddressField(load_default=None)
    evm_chain = EvmChainNameField(
        load_default=None,
        limit_to=list(EVM_CHAIN_IDS_WITH_TRANSACTIONS),
    )

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__()
        self.db = db

    @validates_schema
    def validate_schema(
            self,
            data: dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['to_timestamp'] <= data['from_timestamp']:
            raise ValidationError(
                message='from_timestamp must be smaller than to_timestamp',
                field_name='from_timestamp',
            )

        if (address := data['address']) is not None:
            with self.db.conn.read_ctx() as cursor:
                query, bindings = 'SELECT COUNT(*) FROM blockchain_accounts WHERE account=?', [address]  # noqa: E501
                if (evm_chain := data['evm_chain']) is not None:
                    query += ' AND blockchain=?'
                    bindings.append(evm_chain.to_blockchain().value)

                if cursor.execute(query, bindings).fetchone()[0] == 0:
                    raise ValidationError(
                        message=f'Account {address} with chain {evm_chain.to_name()} is not tracked by rotki',  # noqa: E501
                        field_name='address',
                    )


class AddressesInteraction(Schema):
    from_address = EvmAddressField(required=True)
    to_address = EvmAddressField(required=True)


class AssetTransferSchema(AddressesInteraction):
    amount = PositiveAmountField(required=True)


class TokenTransfer(AssetTransferSchema):
    token = AssetField(required=True, expected_type=EvmToken)


class NativeAssetTransfer(AssetTransferSchema):
    chain = EvmChainNameField(required=True, limit_to=list(EVM_CHAIN_IDS_WITH_TRANSACTIONS))
