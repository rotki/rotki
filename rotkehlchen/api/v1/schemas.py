import logging
from enum import auto
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    overload,
)
from uuid import uuid4

import webargs
from eth_utils import to_checksum_address
from marshmallow import Schema, fields, post_load, validates_schema
from marshmallow.exceptions import ValidationError

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import (
    ActionType,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.accounting.types import SchemaEventType
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CryptoAsset,
    CustomAsset,
    EvmToken,
    UnderlyingToken,
)
from rotkehlchen.assets.types import AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.bitcoin.bch.utils import validate_bch_address_input
from rotkehlchen.chain.bitcoin.hdkey import HDKey, XpubType
from rotkehlchen.chain.bitcoin.utils import is_valid_btc_address, scriptpubkey_to_btc_address
from rotkehlchen.chain.constants import NON_BITCOIN_CHAINS
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.types import ETHERSCAN_NODE_NAME
from rotkehlchen.chain.substrate.types import (
    KusamaAddress,
    PolkadotAddress,
    SubstrateChain,
    SubstratePublicKey,
)
from rotkehlchen.chain.substrate.utils import (
    get_substrate_address_from_public_key,
    is_valid_kusama_address,
    is_valid_polkadot_address,
)
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.data_import.manager import DataImportSource
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    AssetsFilterQuery,
    CustomAssetsFilterQuery,
    Eth2DailyStatsFilterQuery,
    ETHTransactionsFilterQuery,
    HistoryEventFilterQuery,
    LedgerActionsFilterQuery,
    ReportDataFilterQuery,
    TradesFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.db.utils import DBAssetBalance, LocationData
from rotkehlchen.errors.misc import InputError, RemoteError, XPUBError
from rotkehlchen.errors.serialization import DeserializationError, EncodingError
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.exchanges.manager import ALL_SUPPORTED_EXCHANGES, SUPPORTED_EXCHANGES
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.icons import ALLOWED_ICON_EXTENSIONS
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    AVAILABLE_MODULES_MAP,
    NON_EVM_CHAINS,
    AddressbookEntry,
    AddressbookType,
    AssetMovementCategory,
    BTCAddress,
    ChainID,
    ChecksumEvmAddress,
    CostBasisMethod,
    EvmTokenKind,
    ExchangeLocationID,
    ExternalService,
    ExternalServiceApiCredentials,
    Location,
    SupportedBlockchain,
    Timestamp,
    TradeType,
    UserNote,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import create_order_by_rules_list, ts_now
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin

from .fields import (
    AmountField,
    ApiKeyField,
    ApiSecretField,
    AssetConflictsField,
    AssetField,
    AssetTypeField,
    BlockchainField,
    ColorField,
    CurrentPriceOracleField,
    DelimitedOrNormalList,
    DerivationPathField,
    DirectoryField,
    EthereumAddressField,
    EVMTransactionHashField,
    FeeField,
    FileField,
    FloatingPercentageField,
    HistoricalPriceOracleField,
    LocationField,
    MaybeAssetField,
    PositiveAmountField,
    PriceField,
    SerializableEnumField,
    TaxFreeAfterPeriodField,
    TimestampField,
    TimestampUntilNowField,
    XpubField,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.interfaces import HistoricalPriceOracleInterface

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncQueryArgumentSchema(Schema):
    """A schema for getters that only have one argument enabling async query"""
    async_query = fields.Boolean(load_default=False)


class AsyncIgnoreCacheQueryArgumentSchema(AsyncQueryArgumentSchema):
    ignore_cache = fields.Boolean(load_default=False)


class AsyncHistoricalQuerySchema(AsyncQueryArgumentSchema):
    """A schema for getters that have 2 arguments.
    One to enable async querying and another to force reset DB data by querying everytying again"""
    reset_db_data = fields.Boolean(load_default=False)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


class BalanceSchema(Schema):
    amount = AmountField(required=True)
    usd_value = AmountField(required=True)

    @post_load
    def make_balance_entry(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def validate_order_by_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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


class EthereumTransactionQuerySchema(
        AsyncQueryArgumentSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    address = EthereumAddressField(load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    protocols = DelimitedOrNormalList(fields.String(), load_default=None)
    asset = AssetField(expected_type=CryptoAsset, load_default=None)
    exclude_ignored_assets = fields.Boolean(load_default=True)

    @validates_schema
    def validate_ethtx_query_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
        protocols = data['protocols']
        if protocols is not None and len(protocols) == 0:
            raise ValidationError(
                message='protocols have to be either not passed or contain at least one item',
                field_name='protocols',
            )

    @post_load
    def make_ethereum_transaction_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        address = data.get('address')
        protocols, asset = data['protocols'], data['asset']
        exclude_ignored_assets = data['exclude_ignored_assets']
        filter_query = ETHTransactionsFilterQuery.make(
            order_by_rules=create_order_by_rules_list(data),
            limit=data['limit'],
            offset=data['offset'],
            addresses=[address] if address is not None else None,
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            protocols=protocols,
            asset=asset,
            exclude_ignored_assets=exclude_ignored_assets,
        )
        event_params = {
            'asset': asset,
            'protocols': protocols,
            'exclude_ignored_assets': exclude_ignored_assets,
        }

        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
            'event_params': event_params,
        }


class EthereumTransactionDecodingSchema(AsyncIgnoreCacheQueryArgumentSchema):
    tx_hashes = fields.List(EVMTransactionHashField(), load_default=None)

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        tx_hashes = data.get('tx_hashes')
        if tx_hashes is not None and len(tx_hashes) == 0:
            raise ValidationError('Empty list of hashes is a noop. Did you mean to omit the list?')


class TradesQuerySchema(
        AsyncQueryArgumentSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    base_asset = AssetField(expected_type=Asset, load_default=None)
    quote_asset = AssetField(expected_type=Asset, load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    trade_type = SerializableEnumField(enum_class=TradeType, load_default=None)
    location = LocationField(load_default=None)

    def __init__(
            self,
            treat_eth2_as_eth: bool,
    ) -> None:
        super().__init__()
        self.treat_eth2_as_eth = treat_eth2_as_eth

    @validates_schema
    def validate_trades_query_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def make_trades_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        base_assets: Optional[Tuple['Asset', ...]] = None
        quote_assets: Optional[Tuple['Asset', ...]] = None
        if data['base_asset'] is not None:
            base_assets = (data['base_asset'],)
        if data['quote_asset'] is not None:
            quote_assets = (data['quote_asset'],)

        if self.treat_eth2_as_eth is True and data['base_asset'] == A_ETH:
            base_assets = (A_ETH, A_ETH2)
        elif self.treat_eth2_as_eth is True and data['quote_asset'] == A_ETH:
            quote_assets = (A_ETH, A_ETH2)

        filter_query = TradesFilterQuery.make(
            order_by_rules=create_order_by_rules_list(data),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            base_assets=base_assets,
            quote_assets=quote_assets,
            trade_type=[data['trade_type']] if data['trade_type'] is not None else None,
            location=data['location'],
        )

        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
        }


class StakingQuerySchema(
    AsyncQueryArgumentSchema,
    OnlyCacheQuerySchema,
    DBPaginationSchema,
    DBOrderBySchema,
):
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    asset = AssetField(expected_type=AssetWithOracles, load_default=None)
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

    @post_load
    def make_staking_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        if data['order_by_attributes'] is not None:
            attributes = []
            for order_by_attribute in data['order_by_attributes']:
                if order_by_attribute == 'event_type':
                    attributes.append('subtype')
                else:
                    attributes.append(order_by_attribute)
            data['order_by_attributes'] = attributes
        asset_list: Optional[Tuple['AssetWithOracles', ...]] = None
        if data['asset'] is not None:
            asset_list = (data['asset'],)
        if self.treat_eth2_as_eth is True and data['asset'] == A_ETH:
            asset_list = (
                A_ETH.resolve_to_asset_with_oracles(),
                A_ETH2.resolve_to_asset_with_oracles(),
            )

        query_filter = HistoryEventFilterQuery.make(
            order_by_rules=create_order_by_rules_list(data),
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            location=Location.KRAKEN,
            event_types=[
                HistoryEventType.STAKING,
            ],
            event_subtypes=data['event_subtypes'],
            exclude_subtypes=[
                HistoryEventSubType.RECEIVE_WRAPPED,
                HistoryEventSubType.RETURN_WRAPPED,
            ],
            assets=asset_list,
        )

        value_filter = HistoryEventFilterQuery.make(
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            location=Location.KRAKEN,
            event_types=[
                HistoryEventType.STAKING,
            ],
            event_subtypes=[
                HistoryEventSubType.REWARD,
            ],
            order_by_rules=None,
            assets=asset_list,
        )

        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'query_filter': query_filter,
            'value_filter': value_filter,
        }


class HistoryBaseEntrySchema(Schema):
    identifier = fields.Integer(load_default=None, required=False)
    event_identifier = fields.String(required=True)
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
    counterparty = fields.String(required=False)

    def __init__(self, identifier_required: bool):
        super().__init__()
        self.identifier_required = identifier_required

    @validates_schema
    def validate_history_entry_schema(
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.identifier_required is True and data['identifier'] is None:
            raise ValidationError('History event identifier should be given')
        try:
            data['event_identifier'] = HistoryBaseEntry.deserialize_event_identifier(data['event_identifier'])  # noqa: E501
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

    @post_load
    def make_history_base_entry(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        if data['event_subtype'] is None:
            data['event_subtype'] = HistoryEventSubType.NONE
        return {'event': HistoryBaseEntry(**data)}


class AssetMovementsQuerySchema(
        AsyncQueryArgumentSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    asset = AssetField(expected_type=Asset, load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    action = SerializableEnumField(enum_class=AssetMovementCategory, load_default=None)
    location = LocationField(load_default=None)

    def __init__(
            self,
            treat_eth2_as_eth: bool,
    ) -> None:
        super().__init__()
        self.treat_eth2_as_eth = treat_eth2_as_eth

    @validates_schema
    def validate_asset_movements_query_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def make_asset_movements_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        asset_list: Optional[Tuple['Asset', ...]] = None
        if data['asset'] is not None:
            asset_list = (data['asset'],)
        if self.treat_eth2_as_eth is True and data['asset'] == A_ETH:
            asset_list = (A_ETH, A_ETH2)

        filter_query = AssetMovementsFilterQuery.make(
            order_by_rules=create_order_by_rules_list(data),
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
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    asset = AssetField(expected_type=Asset, load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    type = SerializableEnumField(enum_class=LedgerActionType, load_default=None)
    location = LocationField(load_default=None)

    def __init__(
            self,
            treat_eth2_as_eth: bool,
    ) -> None:
        super().__init__()
        self.treat_eth2_as_eth = treat_eth2_as_eth

    @validates_schema
    def validate_asset_movements_query_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def make_asset_movements_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        asset_list: Optional[Tuple['Asset', ...]] = None
        if data['asset'] is not None:
            asset_list = (data['asset'],)
        if self.treat_eth2_as_eth is True and data['asset'] == A_ETH:
            asset_list = (A_ETH, A_ETH2)

        filter_query = LedgerActionsFilterQuery.make(
            order_by_rules=create_order_by_rules_list(data),
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
    def validate_trade(  # pylint: disable=no-self-use
        self,
        data: Dict[str, Any],
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
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.identifier_required is True and data['identifier'] is None:
            raise ValidationError(
                message='Ledger action identifier should be given',
                field_name='identifier',
            )

    @post_load(pass_many=True)
    def make_ledger_action(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, LedgerAction]:
        return {'action': LedgerAction(**data)}


class IntegerIdentifierListSchema(Schema):
    identifiers = DelimitedOrNormalList(fields.Integer(required=True), required=True)


class IntegerIdentifierSchema(Schema):
    identifier = fields.Integer(required=True)


class StringIdentifierSchema(Schema):
    identifier = fields.String(required=True)


class ManuallyTrackedBalanceAddSchema(Schema):
    asset = AssetField(expected_type=Asset, required=True)
    label = fields.String(required=True)
    amount = PositiveAmountField(required=True)
    location = LocationField(required=True)
    tags = fields.List(fields.String(), load_default=None)
    balance_type = SerializableEnumField(enum_class=BalanceType, load_default=BalanceType.ASSET)

    @post_load
    def make_manually_tracked_balances(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> ManuallyTrackedBalance:
        data['id'] = -1  # can be any value because id will be set automatically
        return ManuallyTrackedBalance(**data)


class ManuallyTrackedBalanceEditSchema(ManuallyTrackedBalanceAddSchema):
    id = fields.Integer(required=True)

    @post_load
    def make_manually_tracked_balances(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
            data: Dict[str, Any],
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
        current_price_oracles: List[CurrentPriceOracle],
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
        historical_price_oracles: List[HistoricalPriceOracle],
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
    def make_exchange_location_id(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    ssf_0graph_multiplier = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            error='The snapshot saving frequeny 0graph multiplier should be >= 0',
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

    @validates_schema
    def validate_settings_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
            ssf_0graph_multiplier=data['ssf_0graph_multiplier'],
            non_syncing_exchanges=data['non_syncing_exchanges'],
            cost_basis_method=data['cost_basis_method'],
            treat_eth2_as_eth=data['treat_eth2_as_eth'],
            eth_staking_taxable_after_withdrawal_enabled=data['eth_staking_taxable_after_withdrawal_enabled'],  # noqa: 501
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
    def validate_user_action_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['action'] is None and (data['premium_api_key'] == '' or data['premium_api_secret'] == ''):  # noqa: 501
            raise ValidationError(
                'Without an action premium api key and secret must be provided',
            )


class UserActionLoginSchema(Schema):
    name = fields.String(required=True)
    password = fields.String(required=True)
    sync_approval = fields.String(
        load_default='unknown',
        validate=webargs.validate.OneOf(choices=('unknown', 'yes', 'no')),
    )


class UserPasswordChangeSchema(Schema):
    name = fields.String(required=True)
    current_password = fields.String(required=True)
    new_password = fields.String(required=True)


class UserPremiumSyncSchema(AsyncQueryArgumentSchema):
    action = fields.String(
        validate=webargs.validate.OneOf(choices=('upload', 'download')),
        required=True,
    )


class NewUserSchema(BaseUserSchema):
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
    def make_external_service(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    ftx_subaccount = fields.String(load_default=None)


class ExchangesResourceAddSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)
    api_key = ApiKeyField(required=True)
    api_secret = ApiSecretField(required=True)
    passphrase = fields.String(load_default=None)
    kraken_account_type = SerializableEnumField(enum_class=KrakenAccountType, load_default=None)
    binance_markets = fields.List(fields.String(), load_default=None)
    ftx_subaccount = fields.String(load_default=None)


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


class StatisticsAssetBalanceSchema(Schema):
    asset = AssetField(expected_type=Asset, required=True)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


class StatisticsValueDistributionSchema(Schema):
    distribution_by = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=('location', 'asset')),
    )


class HistoryProcessingSchema(AsyncQueryArgumentSchema):
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


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
    def validate_accounting_reports_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.required_report_id and data['report_id'] is None:
            raise ValidationError('A report id should be given')


class AccountingReportDataSchema(DBPaginationSchema, DBOrderBySchema):
    report_id = fields.Integer(load_default=None)
    event_type = SerializableEnumField(enum_class=SchemaEventType, load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)

    @validates_schema
    def validate_report_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def make_report_data_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        report_id = data.get('report_id')
        event_type = data.get('event_type')
        filter_query = ReportDataFilterQuery.make(
            order_by_rules=create_order_by_rules_list(data),
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


class BlockchainAccountDataSchema(Schema):
    address = fields.String(required=True)
    label = fields.String(load_default=None)
    tags = fields.List(fields.String(), load_default=None)

    @validates_schema
    def validate_blockchain_account_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        label = data.get('label', None)
        if label == '':
            raise ValidationError('Blockchain account\'s label cannot be empty string. Use null instead.')  # noqa: E501


class BaseXpubSchema(AsyncQueryArgumentSchema):
    xpub = XpubField(required=True)
    blockchain = BlockchainField(
        required=True,
        exclude_types=NON_BITCOIN_CHAINS,
    )
    derivation_path = DerivationPathField(load_default=None)


class XpubAddSchema(AsyncQueryArgumentSchema):
    xpub = fields.String(required=True)
    derivation_path = DerivationPathField(load_default=None)
    label = fields.String(load_default=None)
    blockchain = BlockchainField(
        required=True,
        exclude_types=NON_BITCOIN_CHAINS,
    )
    xpub_type = SerializableEnumField(XpubType, load_default=None)
    tags = fields.List(fields.String(), load_default=None)

    @post_load
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        xpub_type = data.pop('xpub_type', None)
        try:
            derivation_path = 'm' if data['derivation_path'] is None else data['derivation_path']
            xpub_hdkey = HDKey.from_xpub(data['xpub'], xpub_type=xpub_type, path=derivation_path)
        except XPUBError as e:
            raise ValidationError(
                f'Failed to initialize an xpub due to {str(e)}',
                field_name='xpub',
            ) from e

        data['xpub'] = xpub_hdkey
        return data


class XpubPatchSchema(Schema):
    xpub = XpubField(required=True)
    derivation_path = DerivationPathField(load_default=None)
    label = fields.String(load_default=None)
    tags = fields.List(fields.String(), load_default=None)
    blockchain = BlockchainField(
        required=True,
        exclude_types=NON_BITCOIN_CHAINS,
    )


class BlockchainAccountsGetSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501


def _validate_blockchain_account_schemas(
        data: Dict[str, Any],
        address_getter: Callable,
) -> None:
    """Validates schema input for the PUT/PATCH/DELETE on blockchain account data"""
    # Make sure no duplicates addresses are given
    given_addresses = set()
    # Make sure EVM based addresses are checksummed
    if data['blockchain'] in (SupportedBlockchain.ETHEREUM, SupportedBlockchain.AVALANCHE):
        for account_data in data['accounts']:
            address_string = address_getter(account_data)
            if not address_string.endswith('.eth'):
                # Make sure that given value is an ethereum address
                try:
                    address = to_checksum_address(address_string)
                except (ValueError, TypeError) as e:
                    raise ValidationError(
                        f'Given value {address_string} is not an ethereum address',
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
    elif data['blockchain'] == SupportedBlockchain.BITCOIN:
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
    elif data['blockchain'] == SupportedBlockchain.BITCOIN_CASH:
        for account_data in data['accounts']:
            address = address_getter(account_data)
            validate_bch_address_input(address, given_addresses)
            given_addresses.add(address)

    # Make sure kusama addresses are valid (either ss58 format or ENS domain)
    elif data['blockchain'] == SupportedBlockchain.KUSAMA:
        for account_data in data['accounts']:
            address = address_getter(account_data)
            # ENS domain will be checked in the transformation step
            if not address.endswith('.eth') and not is_valid_kusama_address(address):
                raise ValidationError(
                    f'Given value {address} is not a valid kusama address',
                    field_name='address',
                )
            if address in given_addresses:
                raise ValidationError(
                    f'Address {address} appears multiple times in the request data',
                    field_name='address',
                )
            given_addresses.add(address)

    # Make sure polkadot addresses are valid (either ss58 format or ENS domain)
    elif data['blockchain'] == SupportedBlockchain.POLKADOT:
        for account_data in data['accounts']:
            address = address_getter(account_data)
            # ENS domain will be checked in the transformation step
            if not address.endswith('.eth') and not is_valid_polkadot_address(address):
                raise ValidationError(
                    f'Given value {address} is not a valid polkadot address',
                    field_name='address',
                )
            if address in given_addresses:
                raise ValidationError(
                    f'Address {address} appears multiple times in the request data',
                    field_name='address',
                )
            given_addresses.add(address)


def _transform_btc_or_bch_address(
        ethereum: EthereumManager,
        given_address: str,
        blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
) -> BTCAddress:
    """Returns a SegWit/P2PKH/P2SH address (if existing) given an ENS domain.

    NB: ENS domains for BTC store the scriptpubkey. Check EIP-2304.
    """
    if not given_address.endswith('.eth'):
        return BTCAddress(given_address)

    try:
        resolved_address = ethereum.ens_lookup(
            given_address,
            blockchain=blockchain,
        )
    except (RemoteError, InputError) as e:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved '
            f'for {blockchain.value} due to: {str(e)}',
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
            f'Given ENS address {given_address} does not contain a valid {blockchain.value} '
            f"scriptpubkey: {resolved_address}. {blockchain.value} address can't be obtained.",
            field_name='address',
        ) from e

    log.debug(f'Resolved {blockchain.value} ENS {given_address} to {address}')

    return address


def _transform_eth_address(
        ethereum: EthereumManager,
        given_address: str,
) -> ChecksumEvmAddress:
    try:
        address = to_checksum_address(given_address)
    except ValueError:
        # Validation will only let .eth names come here.
        # So let's see if it resolves to anything
        try:
            resolved_address = ethereum.ens_lookup(given_address)
        except (RemoteError, InputError) as e:
            raise ValidationError(
                f'Given ENS address {given_address} could not be resolved for Ethereum'
                f' due to: {str(e)}',
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


@overload
def _transform_substrate_address(
        ethereum: EthereumManager,
        given_address: str,
        chain: Literal['Kusama'],
) -> KusamaAddress:
    ...


@overload
def _transform_substrate_address(
        ethereum: EthereumManager,
        given_address: str,
        chain: Literal['Polkadot'],
) -> PolkadotAddress:
    ...


def _transform_substrate_address(
        ethereum: EthereumManager,
        given_address: str,
        chain: Literal['Kusama', 'Polkadot'],
) -> Union[KusamaAddress, PolkadotAddress]:
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
        if chain == 'Polkadot':
            return PolkadotAddress(given_address)
        if chain == 'Kusama':
            return KusamaAddress(given_address)

    try:
        resolved_address = ethereum.ens_lookup(
            given_address,
            blockchain=SupportedBlockchain.POLKADOT if chain == 'Polkadot' else SupportedBlockchain.KUSAMA,  # noqa: E501
        )
    except (RemoteError, InputError) as e:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved '
            f'for {chain} due to: {str(e)}',
            field_name='address',
        ) from None

    if resolved_address is None:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved for ' + chain,
            field_name='address',
        ) from None

    address: Union[PolkadotAddress, KusamaAddress]
    try:
        if chain == 'Polkadot':
            address = get_substrate_address_from_public_key(
                chain=SubstrateChain.POLKADOT,
                public_key=SubstratePublicKey(resolved_address),
            )
            log.debug(f'Resolved polkadot ENS {given_address} to {address}')
            return PolkadotAddress(address)

        # else can only be kusama
        address = get_substrate_address_from_public_key(
            chain=SubstrateChain.KUSAMA,
            public_key=SubstratePublicKey(resolved_address),
        )
        log.debug(f'Resolved kusama ENS {given_address} to {address}')
        return KusamaAddress(address)

    except (TypeError, ValueError) as e:
        raise ValidationError(
            f'Given ENS address {given_address} does not contain a valid '
            f'Substrate public key: {resolved_address}. {chain} address cannot be obtained.',
            field_name='address',
        ) from e


class BlockchainAccountsPatchSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    accounts = fields.List(fields.Nested(BlockchainAccountDataSchema), required=True)

    def __init__(self, ethereum_manager: EthereumManager):
        super().__init__()
        self.ethereum_manager = ethereum_manager

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        _validate_blockchain_account_schemas(data, lambda x: x['address'])

    @post_load
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        if data['blockchain'] in (SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH):
            for idx, account in enumerate(data['accounts']):
                data['accounts'][idx]['address'] = _transform_btc_or_bch_address(
                    ethereum=self.ethereum_manager,
                    given_address=account['address'],
                    blockchain=data['blockchain'],
                )
        if data['blockchain'] in (SupportedBlockchain.ETHEREUM, SupportedBlockchain.AVALANCHE):
            for idx, account in enumerate(data['accounts']):
                data['accounts'][idx]['address'] = _transform_eth_address(
                    ethereum=self.ethereum_manager,
                    given_address=account['address'],
                )
        if data['blockchain'] == SupportedBlockchain.KUSAMA:
            for idx, account in enumerate(data['accounts']):
                data['accounts'][idx]['address'] = _transform_substrate_address(
                    ethereum=self.ethereum_manager,
                    given_address=account['address'],
                    chain='Kusama',
                )
        if data['blockchain'] == SupportedBlockchain.POLKADOT:
            for idx, account in enumerate(data['accounts']):
                data['accounts'][idx]['address'] = _transform_substrate_address(
                    ethereum=self.ethereum_manager,
                    given_address=account['address'],
                    chain='Polkadot',
                )

        return data


class BlockchainAccountsPutSchema(AsyncQueryArgumentSchema, BlockchainAccountsPatchSchema):
    ...


class BlockchainAccountsDeleteSchema(AsyncQueryArgumentSchema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    accounts = fields.List(fields.String(), required=True)

    def __init__(self, ethereum_manager: EthereumManager):
        super().__init__()
        self.ethereum_manager = ethereum_manager

    @validates_schema
    def validate_blockchain_accounts_delete_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        _validate_blockchain_account_schemas(data, lambda x: x)

    @post_load
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        if data['blockchain'] in (SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH):
            data['accounts'] = [
                _transform_btc_or_bch_address(self.ethereum_manager, x, data['blockchain'])
                for x in data['accounts']
            ]
        if data['blockchain'] in (SupportedBlockchain.ETHEREUM, SupportedBlockchain.AVALANCHE):
            data['accounts'] = [
                _transform_eth_address(self.ethereum_manager, x) for x in data['accounts']
            ]
        if data['blockchain'] == SupportedBlockchain.KUSAMA:
            data['accounts'] = [
                _transform_substrate_address(
                    self.ethereum_manager, x, 'Kusama') for x in data['accounts']
            ]
        if data['blockchain'] == SupportedBlockchain.POLKADOT:
            data['accounts'] = [
                _transform_substrate_address(
                    self.ethereum_manager, x, 'Polkadot') for x in data['accounts']
            ]
        return data


class IgnoredAssetsSchema(Schema):
    assets = fields.List(AssetField(expected_type=Asset), required=True)


class IgnoredActionsGetSchema(Schema):
    action_type = SerializableEnumField(enum_class=ActionType, load_default=None)


class IgnoredActionsModifySchema(Schema):
    action_type = SerializableEnumField(enum_class=ActionType, required=True)
    action_ids = fields.List(fields.String(required=True), required=True)


class OptionalEthereumAddressSchema(Schema):
    address = EthereumAddressField(required=False, load_default=None)
    chain = SerializableEnumField(enum_class=ChainID, required=False, load_default=None)


class RequiredEthereumAddressSchema(Schema):
    address = EthereumAddressField(required=True)
    chain = SerializableEnumField(enum_class=ChainID, required=True)


class OptionalEvmTokenInformationSchema(Schema):
    address = EthereumAddressField(required=False)
    chain = SerializableEnumField(enum_class=ChainID, required=False)
    token_kind = SerializableEnumField(enum_class=EvmTokenKind, required=False)


class UnderlyingTokenInfoSchema(Schema):
    address = EthereumAddressField(required=True)
    token_kind = SerializableEnumField(enum_class=EvmTokenKind, required=True)
    weight = FloatingPercentageField(required=True)


def _validate_single_oracle_id(
        data: Dict[str, Any],
        oracle_name: Literal['coingecko', 'cryptocompare'],
        oracle_obj: 'HistoricalPriceOracleInterface',
) -> None:
    coin_key = data.get(oracle_name)
    if coin_key:
        try:
            all_coins = oracle_obj.all_coins()
        except RemoteError as e:
            raise ValidationError(
                f'Could not validate {oracle_name} identifer {coin_key} due to '
                f'problem communicating with {oracle_name}: {str(e)}',
            ) from e

        if coin_key not in all_coins:
            raise ValidationError(
                f'Given {oracle_name} identifier {coin_key} is not valid. Make sure the '
                f'identifier is correct and in the list of valid {oracle_name} identifiers',
                field_name=oracle_name,
            )


class BaseCryptoAssetSchema(Schema):
    name = fields.String(required=True)
    symbol = fields.String(required=True)
    started = TimestampField(load_default=None)
    swapped_for = AssetField(expected_type=CryptoAsset, load_default=None)
    coingecko = fields.String(load_default=None)
    cryptocompare = fields.String(load_default=None)


class CryptoAssetSchema(BaseCryptoAssetSchema):
    identifier = fields.String(required=False, load_default=None)
    asset_type = AssetTypeField(
        required=True,
        exclude_types=(AssetType.EVM_TOKEN, AssetType.NFT),
    )
    forked = AssetField(expected_type=CryptoAsset, load_default=None)

    def __init__(
            self,
            identifier_required: bool,
            coingecko: 'Coingecko',
            cryptocompare: 'Cryptocompare',
    ) -> None:
        super().__init__()
        self.identifier_required = identifier_required
        self.coingecko_obj = coingecko
        self.cryptocompare_obj = cryptocompare

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if self.identifier_required is True and data['identifier'] is None:
            raise ValidationError(message='Asset schema identifier should be given', field_name='identifier')  # noqa: E501
        _validate_single_oracle_id(data, 'coingecko', self.coingecko_obj)
        _validate_single_oracle_id(data, 'cryptocompare', self.cryptocompare_obj)


class IgnoredAssetsHandling(SerializableEnumMixin):
    NONE = auto()
    EXCLUDE = auto()
    SHOW_ONLY = auto()


class AssetsPostSchema(DBPaginationSchema, DBOrderBySchema):
    name = fields.String(load_default=None)
    symbol = fields.String(load_default=None)
    asset_type = SerializableEnumField(enum_class=AssetType, load_default=None)
    ignored_assets_handling = SerializableEnumField(enum_class=IgnoredAssetsHandling, load_default=IgnoredAssetsHandling.NONE)  # noqa: E501
    show_user_owned_assets_only = fields.Boolean(load_default=False)
    identifiers = DelimitedOrNormalList(fields.String(required=True), load_default=None)

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__()
        self.db = db

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        # the length of `order_by_attributes` and `ascending` are the same. So check only one.
        if data['order_by_attributes'] is not None and len(data['order_by_attributes']) > 1:
            raise ValidationError(
                message='Multiple fields ordering is not allowed.',
                field_name='order_by_attributes',
            )

    @post_load
    def make_assets_post_query(
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        with self.db.user_write() as write_cursor, GlobalDBHandler().conn.read_ctx() as globaldb_read_cursor:  # noqa: E501
            ignored_assets_filter_params: Optional[Tuple[Literal['IN', 'NOT IN'], List[str]]] = None  # noqa: E501
            if data['ignored_assets_handling'] == IgnoredAssetsHandling.EXCLUDE:
                ignored_assets_filter_params = (
                    'NOT IN',
                    [asset.identifier for asset in self.db.get_ignored_assets(write_cursor)],
                )
            elif data['ignored_assets_handling'] == IgnoredAssetsHandling.SHOW_ONLY:
                ignored_assets_filter_params = (
                    'IN',
                    [asset.identifier for asset in self.db.get_ignored_assets(write_cursor)],
                )

            if data['show_user_owned_assets_only'] is True:
                globaldb_read_cursor.execute('SELECT asset_id FROM user_owned_assets;')
                identifiers = [entry[0] for entry in globaldb_read_cursor]
            else:
                identifiers = data['identifiers']

            filter_query = AssetsFilterQuery.make(
                and_op=True,
                order_by_rules=create_order_by_rules_list(
                    data=data,
                    default_order_by_field='name',
                ),
                limit=data['limit'],
                offset=data['offset'],
                name=data['name'],
                symbol=data['symbol'],
                asset_type=data['asset_type'],
                identifiers=identifiers,
                ignored_assets_filter_params=ignored_assets_filter_params,
            )
        return {'filter_query': filter_query, 'identifiers': data['identifiers']}


class AssetsSearchLevenshteinSchema(DBOrderBySchema, DBPaginationSchema):
    value = fields.String(required=True)
    return_exact_matches = fields.Boolean(load_default=False)
    evm_chain = SerializableEnumField(enum_class=ChainID, load_default=None)

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        # the length of `order_by_attributes` and `ascending` are the same. So check only one.
        if data['order_by_attributes'] is not None and len(data['order_by_attributes']) > 1:
            raise ValidationError(
                message='Multiple fields ordering is not allowed.',
                field_name='order_by_attributes',
            )

    @post_load
    def make_assets_search_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        filter_query = AssetsFilterQuery.make(
            and_op=True,
            order_by_rules=create_order_by_rules_list(data=data, default_order_by_field='name'),
            evm_chain=data['evm_chain'],
        )
        return {
            'filter_query': filter_query,
            'substring_search': data['value'].strip().casefold(),
            'limit': data['limit'],
        }


class AssetsSearchByColumnSchema(AssetsSearchLevenshteinSchema):
    search_column = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=('name', 'symbol')),
    )

    @post_load
    def make_assets_search_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        filter_query = AssetsFilterQuery.make(
            and_op=True,
            order_by_rules=create_order_by_rules_list(data=data, default_order_by_field='name'),
            limit=data['limit'],
            offset=0,  # this is needed for the `limit` argument to work.
            substring_search=data['value'].strip(),
            search_column=data['search_column'],
            return_exact_matches=data['return_exact_matches'],
            evm_chain=data['evm_chain'],
        )
        return {'filter_query': filter_query}


class AssetsMappingSchema(Schema):
    identifiers = DelimitedOrNormalList(fields.String(required=True), required=True)


class EvmTokenSchema(BaseCryptoAssetSchema, RequiredEthereumAddressSchema):
    token_kind = SerializableEnumField(enum_class=EvmTokenKind, required=True)
    decimals = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            max=18,
            error='Ethereum token decimals should range from 0 to 18',
        ),
        required=True,
    )
    protocol = fields.String(load_default=None)
    underlying_tokens = fields.List(fields.Nested(UnderlyingTokenInfoSchema), load_default=None)

    def __init__(
            self,
            coingecko: 'Coingecko' = None,
            cryptocompare: 'Cryptocompare' = None,
            **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.coingecko_obj = coingecko
        self.cryptocompare_obj = cryptocompare

    @validates_schema
    def validate_ethereum_token_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        given_underlying_tokens = data.get('underlying_tokens', None)
        if given_underlying_tokens is not None:
            if given_underlying_tokens == []:
                raise ValidationError(
                    f'Gave an empty list for underlying tokens of {data["address"]}. '
                    f'If you need to specify no underlying tokens give a null value',
                )
            weight_sum = sum(x['weight'] for x in given_underlying_tokens)
            if weight_sum > ONE:
                raise ValidationError(
                    f'The sum of underlying token weights for {data["address"]} '
                    f'is {weight_sum * 100} and exceeds 100%',
                )
            if weight_sum < ONE:
                raise ValidationError(
                    f'The sum of underlying token weights for {data["address"]} '
                    f'is {weight_sum * 100} and does not add up to 100%',
                )

        if self.coingecko_obj is not None:
            # most probably validation happens at ModifyEvmTokenSchema
            # so this is not needed. Kind of an ugly way to do this but can't
            # find a way around it at the moment
            _validate_single_oracle_id(data, 'coingecko', self.coingecko_obj)
            _validate_single_oracle_id(data, 'cryptocompare', self.cryptocompare_obj)  # type: ignore  # noqa: E501

    @post_load
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> EvmToken:
        given_underlying_tokens = data.pop('underlying_tokens', None)
        underlying_tokens = None
        if given_underlying_tokens is not None:
            underlying_tokens = []
            for entry in given_underlying_tokens:
                underlying_tokens.append(UnderlyingToken(
                    address=entry['address'],
                    token_kind=entry['token_kind'],
                    weight=entry['weight'],
                ))
        return EvmToken.initialize(**data, underlying_tokens=underlying_tokens)


class ModifyEvmTokenSchema(Schema):
    token = fields.Nested(EvmTokenSchema, required=True)

    def __init__(
            self,
            coingecko: 'Coingecko',
            cryptocompare: 'Cryptocompare',
            **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        token: fields.Nested = self.declared_fields['token']  # type: ignore
        token.schema.coingecko_obj = coingecko
        token.schema.cryptocompare_obj = cryptocompare

    @validates_schema
    def validate_modify_ethereum_token_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        # Not the best way to do it. Need to manually validate, coingecko/cryptocompare id here
        token: fields.Nested = self.declared_fields['token']  # type: ignore
        serialized_token = data['token'].to_dict()
        serialized_token.pop('identifier')
        _validate_single_oracle_id(
            data=serialized_token,
            oracle_name='coingecko',
            oracle_obj=token.schema.coingecko_obj,
        )
        _validate_single_oracle_id(
            data=serialized_token,
            oracle_name='cryptocompare',
            oracle_obj=token.schema.cryptocompare_obj,
        )


class AssetsReplaceSchema(Schema):
    source_identifier = fields.String(required=True)
    target_asset = AssetField(required=True, expected_type=Asset, form_with_incomplete_data=True)


class QueriedAddressesSchema(Schema):
    module = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=list(AVAILABLE_MODULES_MAP.keys())),
    )
    address = EthereumAddressField(required=True)


class DataImportSchema(AsyncQueryArgumentSchema):
    source = SerializableEnumField(enum_class=DataImportSource, required=True)
    file = FileField(required=True, allowed_extensions=('.csv',))
    timestamp_format = fields.String(load_default=None)

    @post_load
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    address = EthereumAddressField(required=True)


class BinanceMarketsUserSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=[Location.BINANCEUS, Location.BINANCE], required=True)


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


class AvalancheTransactionQuerySchema(AsyncQueryArgumentSchema):
    address = EthereumAddressField(required=True)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


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
    def validate_eth2_validator_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    validators = fields.List(fields.Nested(Eth2ValidatorSchema), required=True)


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
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    validators = fields.List(fields.Integer(), load_default=None)

    @validates_schema
    def validate_eth2_daily_stats_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        valid_ordering_attr = {
            None,
            'timestamp',
            'validator_index',
            'start_usd_price',
            'end_usd_price',
            'pnl',
            'start_amount',
            'end_amount',
            'missed_attestations',
            'orphaned_attestations',
            'proposed_blocks',
            'missed_blocks',
            'orphaned_blocks',
            'included_attester_slashings',
            'proposer_attester_slashings',
            'deposits_number',
            'amount_deposited',
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
    def make_eth2_daily_stats_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        filter_query = Eth2DailyStatsFilterQuery.make(
            order_by_rules=create_order_by_rules_list(data),
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
        limit_to=[Location.BINANCEUS, Location.BINANCE],
        load_default=Location.BINANCE,
    )


class AppInfoSchema(Schema):
    check_for_updates = fields.Boolean(load_default=False)


class IdentifiersListSchema(Schema):
    identifiers = fields.List(fields.Integer(), required=True)


class AssetsImportingSchema(Schema):
    file = FileField(allowed_extensions=['.zip', '.json'], load_default=None)
    destination = DirectoryField(load_default=None)
    action = fields.String(
        validate=webargs.validate.OneOf(choices=('upload', 'download')),
        required=True,
    )

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    ethereum_addresses = fields.List(EthereumAddressField(), required=True)


class OptionalAddressesListSchema(Schema):
    addresses = fields.List(EthereumAddressField(required=True), load_default=None)


class BaseAddressbookSchema(Schema):
    book_type = SerializableEnumField(enum_class=AddressbookType, required=True)


class AddressbookAddressesSchema(
    BaseAddressbookSchema,
    OptionalAddressesListSchema,
):
    ...


class AddressbookEntrySchema(Schema):
    address = EthereumAddressField(required=True)
    name = fields.String(required=True)

    @post_load()
    def make_addressbook_entry(self, data: Dict[str, Any], **_kwargs: Any) -> AddressbookEntry:  # pylint: disable=no-self-use  # noqa: E501
        return AddressbookEntry(address=data['address'], name=data['name'])


class AddressbookUpdateSchema(BaseAddressbookSchema):
    entries = fields.List(fields.Nested(AddressbookEntrySchema), required=True)


class AllNamesSchema(Schema):
    addresses = fields.List(EthereumAddressField(required=True), required=True)


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
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def make_balance(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def make_location_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
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
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if not data['timestamp'] == data['balances_snapshot'][0].time == data['location_data_snapshot'][0].time:  # noqa: 501
            raise ValidationError(
                f'timestamp provided {data["timestamp"]} is not the same as the '
                f'one for the entries provided.',
            )


class Web3NodeSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501


class Web3AddNodeSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    name = fields.String(
        required=True,
        validate=webargs.validate.NoneOf(
            iterable=['', ETHERSCAN_NODE_NAME],
            error=f'Name can\'t be empty or {ETHERSCAN_NODE_NAME}',
        ),
    )
    endpoint = fields.String(required=True)
    owned = fields.Boolean(load_default=False)
    weight = FloatingPercentageField(required=True)
    active = fields.Boolean(load_default=False)


class Web3NodeEditSchema(Web3AddNodeSchema):
    name = fields.String(
        required=True,
        validate=webargs.validate.NoneOf(
            iterable=[''],
            error='Name can\'t be empty',
        ),
    )
    identifier = fields.Integer(required=True)

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['identifier'] == 1 and data['name'] != ETHERSCAN_NODE_NAME:
            raise ValidationError(
                message='Can\'t change the etherscan node name',
                field_name='name',
            )
        # verify that if the node is not etherscan the endpoint field has valid information
        if data['identifier'] != 1 and len(data['endpoint'].strip()) == 0:
            raise ValidationError(
                message="endpoint can't be empty",
                field_name='endpoint',
            )


class Web3NodeListDeleteSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    identifier = fields.Integer(required=True)

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        if data['identifier'] == 1:
            raise ValidationError(
                message='Can\'t delete the etherscan node',
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
    def make_user_note(self, data: Dict[str, Any], **_kwargs: Any) -> Dict[str, UserNote]:
        return {'user_note': UserNote.deserialize(data)}


class UserNotesGetSchema(DBPaginationSchema, DBOrderBySchema):
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    title_substring = fields.String(load_default=None)
    location = fields.String(load_default=None)

    @post_load
    def make_user_notes_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        filter_query = UserNotesFilterQuery.make(
            order_by_rules=create_order_by_rules_list(data, 'last_update_timestamp'),
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
    def make_custom_assets_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        filter_query = CustomAssetsFilterQuery.make(
            limit=data['limit'],
            offset=data['offset'],
            order_by_rules=create_order_by_rules_list(
                data=data,
                default_order_by_field='name',
                is_ascending_by_default=True,
            ),
            name=data['name'],
            identifier=data['identifier'],
            custom_asset_type=data['custom_asset_type'],
        )
        return {'filter_query': filter_query}


class BaseCustomAssetSchema(Schema):
    name = fields.String(required=True)
    notes = fields.String(load_default=None)
    custom_asset_type = fields.String(required=True)

    @post_load
    def make_custom_asset(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, CustomAsset]:
        custom_asset = CustomAsset.initialize(
            identifier=str(uuid4()),
            name=data['name'],
            notes=data['notes'],
            custom_asset_type=data['custom_asset_type'],
        )
        return {'custom_asset': custom_asset}


class EditCustomAssetSchema(BaseCustomAssetSchema):
    identifier = fields.UUID(required=True)

    @post_load
    def make_custom_asset(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, CustomAsset]:
        custom_asset = CustomAsset.initialize(
            identifier=str(data['identifier']),
            name=data['name'],
            notes=data['notes'],
            custom_asset_type=data['custom_asset_type'],
        )
        return {'custom_asset': custom_asset}
