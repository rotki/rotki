import logging
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Union,
    overload,
)

import marshmallow
import webargs
from eth_utils import to_checksum_address
from marshmallow import Schema, fields, post_load, validates_schema
from marshmallow.exceptions import ValidationError
from typing_extensions import Literal
from werkzeug.datastructures import FileStorage

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.accounting.structures import ActionType, BalanceType
from rotkehlchen.accounting.typing import SchemaEventType
from rotkehlchen.assets.asset import Asset, EthereumToken, UnderlyingToken
from rotkehlchen.assets.typing import AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.bitcoin.hdkey import HDKey, XpubType
from rotkehlchen.chain.bitcoin.utils import (
    is_valid_btc_address,
    is_valid_derivation_path,
    scriptpubkey_to_btc_address,
)
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.substrate.typing import (
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
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    Eth2DailyStatsFilterQuery,
    ETHTransactionsFilterQuery,
    LedgerActionsFilterQuery,
    ReportDataFilterQuery,
    TradesFilterQuery,
)
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors import (
    DeserializationError,
    EncodingError,
    InputError,
    RemoteError,
    UnknownAsset,
    XPUBError,
)
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.exchanges.manager import ALL_SUPPORTED_EXCHANGES, SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.typing import HistoricalPriceOracle
from rotkehlchen.icons import ALLOWED_ICON_EXTENSIONS
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_hex_color_code,
    deserialize_timestamp,
)
from rotkehlchen.typing import (
    AVAILABLE_MODULES_MAP,
    ApiKey,
    ApiSecret,
    AssetAmount,
    AssetMovementCategory,
    BTCAddress,
    ChecksumEthAddress,
    ExternalService,
    ExternalServiceApiCredentials,
    Fee,
    HexColorCode,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import hexstring_to_bytes, ts_now

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DelimitedOrNormalList(webargs.fields.DelimitedList):
    """This is equal to DelimitedList in webargs v5.6.0

    Essentially accepting either a delimited string or a list-like object

    We introduce it due to them implementing https://github.com/marshmallow-code/webargs/issues/423
    """

    def __init__(
            self,
            cls_or_instance: Any,
            *,
            _delimiter: Optional[str] = None,
            **kwargs: Any,
    ) -> None:
        super().__init__(cls_or_instance, **kwargs)

    def _deserialize(  # type: ignore  # we may get a list in value
            self,
            value: Union[List[str], str],
            attr: str,
            data: Dict[str, Any],
            **kwargs: Any,
    ) -> List[Any]:
        """Adjusting code for _deserialize so that it also works for list-like objects

        Adjusting code from
        https://github.com/marshmallow-code/webargs/blob/dev/src/webargs/fields.py#L71
        so that it uses the list-like detection seen in
        https://github.com/marshmallow-code/webargs/blob/f1ae764973b6492e3c69109060c95240b7cc3d41/src/webargs/fields.py#L69
        which was removed as part of https://github.com/marshmallow-code/webargs/issues/423
        """
        try:
            ret = (
                value
                if marshmallow.utils.is_iterable_but_not_string(value)
                else value.split(self.delimiter)  # type: ignore
            )
        except AttributeError as e:
            raise self.make_error("invalid") from e
        # purposefully skip the superclass here
        return marshmallow.fields.List._deserialize(self, ret, attr, data, **kwargs)  # pylint: disable=bad-super-call  # noqa: E501


class TimestampField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Timestamp:
        try:
            timestamp = deserialize_timestamp(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return timestamp


class ColorField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> HexColorCode:
        try:
            color_code = deserialize_hex_color_code(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return color_code


class TaxFreeAfterPeriodField(fields.Field):

    def _deserialize(
            self,
            value: int,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> int:
        try:
            value = int(value)
        except ValueError:
            raise ValidationError(f'{value} is not a valid integer') from None

        if value < -1:
            raise ValidationError(
                'The taxfree_after_period value can not be negative, except for '
                'the value of -1 to disable the setting',
            )
        if value == 0:
            raise ValidationError('The taxfree_after_period value can not be set to zero')

        return value


class KrakenAccountTypeField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> KrakenAccountType:
        try:
            acc_type = KrakenAccountType.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(f'{value} is not a valid kraken account type') from e

        return acc_type


class AmountField(fields.Field):

    @staticmethod
    def _serialize(
            value: AssetAmount,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: Union[str, int],
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> AssetAmount:
        try:
            amount = deserialize_asset_amount(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return amount


class PositiveAmountField(AmountField):

    def _deserialize(
            self,
            value: Union[str, int],
            attr: Optional[str],
            data: Optional[Mapping[str, Any]],
            **kwargs: Any,
    ) -> AssetAmount:
        amount = super()._deserialize(value, attr, data, **kwargs)
        if amount <= ZERO:
            raise ValidationError(f'Non-positive amount {value} given. Amount should be > 0')

        return amount


class PriceField(fields.Field):

    @staticmethod
    def _serialize(
            value: FVal,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Price:
        try:
            price = deserialize_price(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        if price == ZERO:
            raise ValidationError('A zero rate is not allowed')

        return price


class FeeField(fields.Field):

    @staticmethod
    def _serialize(
            value: Fee,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Optional[str]:
        # Fee can be missing so we need to handle None when serializing from schema
        return str(value) if value else None

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Fee:
        try:
            fee = deserialize_fee(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return fee


class FloatingPercentageField(fields.Field):

    @staticmethod
    def _serialize(
            value: FVal,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> FVal:
        try:
            percentage = FVal(value)
        except ValueError as e:
            raise ValidationError(str(e)) from e

        if percentage < ZERO:
            raise ValidationError('Percentage field can not be negative')
        if percentage > FVal(100):
            raise ValidationError('Percentage field can not be greater than 100')

        return percentage / FVal(100)


class BlockchainField(fields.Field):

    def __init__(self, *, exclude_types: Optional[Sequence[SupportedBlockchain]] = None, **kwargs: Any) -> None:  # noqa: E501
        self.exclude_types = exclude_types
        super().__init__(**kwargs)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> SupportedBlockchain:
        if value in ('btc', 'BTC'):
            chain_type = SupportedBlockchain.BITCOIN
        elif value in ('eth', 'ETH'):
            chain_type = SupportedBlockchain.ETHEREUM
        elif value in ('eth2', 'ETH2'):
            chain_type = SupportedBlockchain.ETHEREUM_BEACONCHAIN
        elif value in ('ksm', 'KSM'):
            chain_type = SupportedBlockchain.KUSAMA
        elif value in ('dot', 'DOT'):
            chain_type = SupportedBlockchain.POLKADOT
        elif value in ('avax', 'AVAX'):
            chain_type = SupportedBlockchain.AVALANCHE
        else:
            raise ValidationError(f'Unrecognized value {value} given for blockchain name')

        if self.exclude_types and chain_type in self.exclude_types:
            raise ValidationError(f'Blockchain name {str(value)} is not allowed in this endpoint')
        return chain_type


class BalanceTypeField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> BalanceType:
        if value == 'asset':
            return BalanceType.ASSET
        if value == 'liability':
            return BalanceType.LIABILITY
        raise ValidationError(f'Unrecognized value {value} given for balance type')


class AssetMovementCategoryField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> AssetMovementCategory:
        try:
            result = AssetMovementCategory.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return result


class AssetField(fields.Field):

    def __init__(self, *, form_with_incomplete_data: bool = False, **kwargs: Any) -> None:  # noqa: E501
        self.form_with_incomplete_data = form_with_incomplete_data
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: Asset,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Optional[str]:
        # Asset can be missing so we need to handle None when serializing from schema
        return str(value.identifier) if value else None

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Asset:
        try:
            asset = Asset(value, form_with_incomplete_data=self.form_with_incomplete_data)
        except (DeserializationError, UnknownAsset) as e:
            raise ValidationError(str(e)) from e

        return asset


class MaybeAssetField(fields.Field):

    def __init__(self, *, form_with_incomplete_data: bool = False, **kwargs: Any) -> None:  # noqa: E501
        self.form_with_incomplete_data = form_with_incomplete_data
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: Asset,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Optional[str]:
        # Asset can be missing so we need to handle None when serializing from schema
        return str(value.identifier) if value else None

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Optional[Asset]:
        try:
            asset = Asset(value, form_with_incomplete_data=self.form_with_incomplete_data)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e
        except UnknownAsset:
            log.error(f'Failed to deserialize asset {value}')
            return None
        return asset


class EthereumAddressField(fields.Field):

    @staticmethod
    def _serialize(
            value: ChecksumEthAddress,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> ChecksumEthAddress:
        # Make sure that given value is an ethereum address
        try:
            address = to_checksum_address(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f'Given value {value} is not an ethereum address',
                field_name='address',
            ) from e

        return address


class SchemaEventTypeField(fields.Field):

    @staticmethod
    def _serialize(
            value: SchemaEventType,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> SchemaEventType:
        # Make sure that given value is an AccountingEvent
        try:
            event_type = SchemaEventType.deserialize_from_db(value)
        except DeserializationError as e:
            raise ValidationError(
                f'Given value {value} is not an SchemaEventType',
                field_name='event_type',
            ) from e

        return event_type


class TradeTypeField(fields.Field):

    @staticmethod
    def _serialize(
            value: TradeType,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> TradeType:
        try:
            trade_type = TradeType.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return trade_type


class AssetTypeField(fields.Field):

    def __init__(self, *, exclude_types: Optional[Sequence[AssetType]] = None, **kwargs: Any) -> None:  # noqa: E501
        self.exclude_types = exclude_types
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: AssetType,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> AssetType:
        try:
            asset_type = AssetType.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        if self.exclude_types and asset_type in self.exclude_types:
            raise ValidationError(f'Asset type {str(asset_type)} is not allowed in this endpoint')

        return asset_type


class LedgerActionTypeField(fields.Field):

    @staticmethod
    def _serialize(
            value: LedgerActionType,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> LedgerActionType:
        try:
            action_type = LedgerActionType.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return action_type


class ActionTypeField(fields.Field):

    @staticmethod
    def _serialize(
            value: ActionType,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> ActionType:
        try:
            action_type = ActionType.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return action_type


class LocationField(fields.Field):

    def __init__(self, *, limit_to: Optional[List[Location]] = None, **kwargs: Any) -> None:  # noqa: E501
        self.limit_to = limit_to
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: Location,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Location:
        try:
            location = Location.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        if self.limit_to is not None and location not in self.limit_to:
            raise ValidationError(
                f'Given location {value} is not one of '
                f'{",".join([str(x) for x in self.limit_to])} as needed by the endpoint',
            )

        return location


class ExternalServiceNameField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> ExternalService:
        if not isinstance(value, str):
            raise ValidationError('External service name should be a string')
        try:
            service = ExternalService.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(f'External service {value} is not known') from e

        return service


class ApiKeyField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> ApiKey:
        if not isinstance(value, str):
            raise ValidationError('Given API Key should be a string')
        return ApiKey(value)


class ApiSecretField(fields.Field):

    @staticmethod
    def _serialize(
            value: ApiSecret,
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        return str(value.decode())

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> ApiSecret:
        if not isinstance(value, str):
            raise ValidationError('Given API Secret should be a string')
        return ApiSecret(value.encode())


class DirectoryField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Path:
        path = Path(value)
        if not path.exists():
            raise ValidationError(f'Given path {value} does not exist')

        if not path.is_dir():
            raise ValidationError(f'Given path {value} is not a directory')

        return path


class AssetConflictsField(fields.Field):

    @staticmethod
    def _serialize(
            value: Dict[str, Any],
            attr: str,  # pylint: disable=unused-argument
            obj: Any,  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        # TODO: If this ever gets used we probably need to change
        # the dict keys to identifiers from assets
        return value

    def _deserialize(
            self,
            value: Dict[str, str],
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Dict[Asset, Literal['remote', 'local']]:
        if not isinstance(value, dict):
            raise ValidationError('A dict object should be given for the conflictss')

        if len(value) == 0:
            raise ValidationError('An empty dict object should not be given. Provide null instead')

        deserialized_dict = {}
        for asset_id, choice in value.items():
            try:
                asset = Asset(asset_id)
            except UnknownAsset as e:
                raise ValidationError(f'Unknown asset identifier {asset_id}') from e

            if choice not in ('remote', 'local'):
                raise ValidationError(
                    f'Unknown asset update choice: {choice}. Valid values '
                    f'are "remote" or "local"',
                )

            deserialized_dict[asset] = choice

        return deserialized_dict  # type: ignore


class FileField(fields.Field):

    def __init__(self, *, allowed_extensions: Optional[Sequence[str]] = None, **kwargs: Any) -> None:  # noqa: E501
        self.allowed_extensions = allowed_extensions
        super().__init__(**kwargs)

    def _deserialize(
            self,
            value: Union[str, FileStorage],
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> Union[Path, FileStorage]:
        if isinstance(value, FileStorage):
            if self.allowed_extensions is not None and value.filename:
                if not any(value.filename.endswith(x) for x in self.allowed_extensions):
                    raise ValidationError(
                        f'Given file {value.filename} does not end in any of '
                        f'{",".join(self.allowed_extensions)}',
                    )

            return value

        if not isinstance(value, str):
            raise ValidationError('Provided non string or file type for file')

        path = Path(value)
        if not path.exists():
            raise ValidationError(f'Given path {value} does not exist')

        if not path.is_file():
            raise ValidationError(f'Given path {value} is not a file')

        if self.allowed_extensions is not None:
            if not any(path.suffix == x for x in self.allowed_extensions):
                raise ValidationError(
                    f'Given file {path} does not end in any of '
                    f'{",".join(self.allowed_extensions)}',
                )

        return path


class XpubField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> HDKey:
        if not isinstance(value, str):
            raise ValidationError('Xpub should be a string')

        try:
            hdkey = HDKey.from_xpub(value, path='m')
        except XPUBError as e:
            raise ValidationError(str(e)) from e

        return hdkey


class DerivationPathField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> str:
        valid, msg = is_valid_derivation_path(value)
        if not valid:
            raise ValidationError(msg)

        return value


class CurrentPriceOracleField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> CurrentPriceOracle:
        try:
            current_price_oracle = CurrentPriceOracle.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(f'Invalid current price oracle: {value}') from e

        return current_price_oracle


class HistoricalPriceOracleField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],  # pylint: disable=unused-argument
            **_kwargs: Any,
    ) -> HistoricalPriceOracle:
        try:
            historical_price_oracle = HistoricalPriceOracle.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(f'Invalid historical price oracle: {value}') from e

        return historical_price_oracle


class AsyncQueryArgumentSchema(Schema):
    """A schema for getters that only have one argument enabling async query"""
    async_query = fields.Boolean(load_default=False)


class AsyncIgnoreCacheQueryArgumentSchema(Schema):
    async_query = fields.Boolean(load_default=False)
    ignore_cache = fields.Boolean(load_default=False)


class AsyncHistoricalQuerySchema(AsyncQueryArgumentSchema):
    """A schema for getters that have 2 arguments.
    One to enable async querying and another to force reset DB data by querying everytying again"""
    reset_db_data = fields.Boolean(load_default=False)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


class AsyncTasksQuerySchema(Schema):
    task_id = fields.Integer(strict=True, load_default=None)


class OnlyCacheQuerySchema(Schema):
    only_cache = fields.Boolean(load_default=False)


class DBPaginationSchema(Schema):
    limit = fields.Integer(load_default=None)
    offset = fields.Integer(load_default=None)


class DBOrderBySchema(Schema):
    order_by_attribute = fields.String(load_default=None)
    ascending = fields.Boolean(load_default=False)  # most recent first by default


class EthereumTransactionQuerySchema(
        AsyncQueryArgumentSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    address = EthereumAddressField(load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)

    @validates_schema
    def validate_ethtx_query_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        value = data['order_by_attribute']
        if data['order_by_attribute'] not in (None, 'timestamp'):
            raise ValidationError(
                message=f'order_by_attribute for transactions can not be {value}',
                field_name='order_by_attribute',
            )

    @post_load
    def make_ethereum_transaction_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        address = data.get('address')
        order_by_attribute = data['order_by_attribute'] if data['order_by_attribute'] is not None else 'timestamp'  # noqa: E501
        filter_query = ETHTransactionsFilterQuery.make(
            order_by_attribute=order_by_attribute,
            order_ascending=data['ascending'],
            limit=data['limit'],
            offset=data['offset'],
            addresses=[address] if address is not None else None,
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
        )

        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
        }


class TradesQuerySchema(
        AsyncQueryArgumentSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    base_asset = AssetField(load_default=None)
    quote_asset = AssetField(load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    trade_type = TradeTypeField(load_default=None)
    location = LocationField(load_default=None)

    @validates_schema
    def validate_trades_query_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        value = data['order_by_attribute']
        if data['order_by_attribute'] not in (
                None,
                'time',
                'location',
                'type',
                'amount',
                'rate',
                'fee',
        ):
            raise ValidationError(
                message=f'order_by_attribute for trades can not be {value}',
                field_name='order_by_attribute',
            )

    @post_load
    def make_trades_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        order_by_attribute = data['order_by_attribute'] if data['order_by_attribute'] is not None else 'time'  # noqa: E501
        filter_query = TradesFilterQuery.make(
            order_by_attribute=order_by_attribute,
            order_ascending=data['ascending'],
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            base_asset=data['base_asset'],
            quote_asset=data['quote_asset'],
            trade_type=[data['trade_type']] if data['trade_type'] is not None else None,
            location=data['location'],
        )
        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
        }


class AssetMovementsQuerySchema(
        AsyncQueryArgumentSchema,
        OnlyCacheQuerySchema,
        DBPaginationSchema,
        DBOrderBySchema,
):
    asset = AssetField(load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    action = AssetMovementCategoryField(load_default=None)
    location = LocationField(load_default=None)

    @validates_schema
    def validate_asset_movements_query_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        value = data['order_by_attribute']
        if data['order_by_attribute'] not in (
                None,
                'time',
                'location',
                'category',
                'amount',
                'fee',
        ):
            raise ValidationError(
                message=f'order_by_attribute for asset movements can not be {value}',
                field_name='order_by_attribute',
            )

    @post_load
    def make_asset_movements_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        order_by_attribute = data['order_by_attribute'] if data['order_by_attribute'] is not None else 'time'  # noqa: E501
        filter_query = AssetMovementsFilterQuery.make(
            order_by_attribute=order_by_attribute,
            order_ascending=data['ascending'],
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            asset=data['asset'],
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
    asset = AssetField(load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    type = LedgerActionTypeField(load_default=None)
    location = LocationField(load_default=None)

    @validates_schema
    def validate_asset_movements_query_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        value = data['order_by_attribute']
        if data['order_by_attribute'] not in (
                None,
                'timestamp',
                'type',
                'location',
                'amount',
                'rate',
        ):
            raise ValidationError(
                message=f'order_by_attribute for ledger actions can not be {value}',
                field_name='order_by_attribute',
            )

    @post_load
    def make_asset_movements_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        order_by_attribute = data['order_by_attribute'] if data['order_by_attribute'] is not None else 'timestamp'  # noqa: E501
        filter_query = LedgerActionsFilterQuery.make(
            order_by_attribute=order_by_attribute,
            order_ascending=data['ascending'],
            limit=data['limit'],
            offset=data['offset'],
            from_ts=data['from_timestamp'],
            to_ts=data['to_timestamp'],
            asset=data['asset'],
            action_type=[data['type']] if data['type'] is not None else None,
            location=data['location'],
        )
        return {
            'async_query': data['async_query'],
            'only_cache': data['only_cache'],
            'filter_query': filter_query,
        }


class TimerangeQuerySchema(Schema):
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    async_query = fields.Boolean(load_default=False)


class GitcoinReportSchema(TimerangeQuerySchema):
    grant_id = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=1,
            error='Gitcoin grant id must be a positive integer',
        ),
        load_default=None,
    )


class GitcoinEventsQuerySchema(GitcoinReportSchema):
    only_cache = fields.Boolean(load_default=False)


class GitcoinEventsDeleteSchema(Schema):
    grant_id = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=1,
            error='Gitcoin grant id must be a positive integer',
        ),
        load_default=None,
    )


class TradeSchema(Schema):
    timestamp = TimestampField(required=True)
    location = LocationField(required=True)
    base_asset = AssetField(required=True)
    quote_asset = AssetField(required=True)
    trade_type = TradeTypeField(required=True)
    amount = PositiveAmountField(required=True)
    rate = PriceField(required=True)
    fee = FeeField(load_default=None)
    fee_currency = AssetField(load_default=None)
    link = fields.String(load_default=None)
    notes = fields.String(load_default=None)


class LedgerActionSchema(Schema):
    timestamp = TimestampField(required=True)
    action_type = LedgerActionTypeField(required=True)
    location = LocationField(required=True)
    amount = AmountField(required=True)
    asset = AssetField(required=True)
    rate = PriceField(load_default=None)
    rate_asset = AssetField(load_default=None)
    link = fields.String(load_default=None)
    notes = fields.String(load_default=None)


class LedgerActionWithIdentifierSchema(LedgerActionSchema):
    identifier = fields.Integer(required=True)

    @post_load
    def make_ledger_action(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> LedgerAction:
        return LedgerAction(**data)


class LedgerActionEditSchema(Schema):
    action = fields.Nested(LedgerActionWithIdentifierSchema, required=True)


class IntegerIdentifierSchema(Schema):
    identifier = fields.Integer(required=True)


class StringIdentifierSchema(Schema):
    identifier = fields.String(required=True)


class ManuallyTrackedBalanceSchema(Schema):
    asset = AssetField(required=True)
    label = fields.String(required=True)
    amount = PositiveAmountField(required=True)
    location = LocationField(required=True)
    tags = fields.List(fields.String(), load_default=None)
    balance_type = BalanceTypeField(load_default=BalanceType.ASSET)

    @post_load
    def make_manually_tracked_balances(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> ManuallyTrackedBalance:
        return ManuallyTrackedBalance(**data)


class ManuallyTrackedBalancesSchema(AsyncQueryArgumentSchema):
    balances = fields.List(fields.Nested(ManuallyTrackedBalanceSchema), required=True)


class ManuallyTrackedBalancesDeleteSchema(AsyncQueryArgumentSchema):
    labels = fields.List(fields.String(required=True), required=True)


class TradePatchSchema(TradeSchema):
    trade_id = fields.String(required=True)


class TradeDeleteSchema(Schema):
    trade_id = fields.String(required=True)


class TagSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(load_default=None)
    background_color = ColorField(required=True)
    foreground_color = ColorField(required=True)


class TagEditSchema(Schema):
    name = fields.String(required=True)
    description = fields.String(load_default=None)
    background_color = ColorField(load_default=None)
    foreground_color = ColorField(load_default=None)


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


class ModifiableSettingsSchema(Schema):
    """This is the Schema for the settings that can be modified via the API"""
    premium_should_sync = fields.Bool(load_default=None)
    include_crypto2crypto = fields.Bool(load_default=None)
    submit_usage_analytics = fields.Bool(load_default=None)
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
    eth_rpc_endpoint = fields.String(load_default=None)
    ksm_rpc_endpoint = fields.String(load_default=None)
    dot_rpc_endpoint = fields.String(load_default=None)
    main_currency = AssetField(load_default=None)
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
    taxable_ledger_actions = fields.List(LedgerActionTypeField, load_default=None)
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
            eth_rpc_endpoint=data['eth_rpc_endpoint'],
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
        )


class EditSettingsSchema(Schema):
    settings = fields.Nested(ModifiableSettingsSchema, required=True)


class BaseUserSchema(Schema):
    name = fields.String(required=True)
    password = fields.String(required=True)


class UserActionSchema(Schema):
    name = fields.String(required=True)
    # All the fields below are not needed for logout/modification so are not required=True
    password = fields.String(load_default=None)
    sync_approval = fields.String(
        load_default='unknown',
        validate=webargs.validate.OneOf(choices=('unknown', 'yes', 'no')),
    )
    action = fields.String(
        validate=webargs.validate.OneOf(choices=('login', 'logout')),
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
        if data['action'] == 'login':
            if data['password'] is None:
                raise ValidationError('Missing password field for login')
        elif data['action'] is None:
            if data['premium_api_key'] == '' or data['premium_api_secret'] == '':
                raise ValidationError(
                    'Without an action premium api key and secret must be provided',
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


class AllBalancesQuerySchema(Schema):
    async_query = fields.Boolean(load_default=False)
    save_data = fields.Boolean(load_default=False)
    ignore_errors = fields.Boolean(load_default=False)
    ignore_cache = fields.Boolean(load_default=False)


class ExternalServiceSchema(Schema):
    name = ExternalServiceNameField(required=True)
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
    services = fields.List(ExternalServiceNameField(), required=True)


class ExchangesResourceEditSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)
    new_name = fields.String(load_default=None)
    api_key = ApiKeyField(load_default=None)
    api_secret = ApiSecretField(load_default=None)
    passphrase = fields.String(load_default=None)
    kraken_account_type = KrakenAccountTypeField(load_default=None)
    binance_markets = fields.List(fields.String(), load_default=None)
    ftx_subaccount = fields.String(load_default=None)


class ExchangesResourceAddSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)
    api_key = ApiKeyField(required=True)
    api_secret = ApiSecretField(required=True)
    passphrase = fields.String(load_default=None)
    kraken_account_type = KrakenAccountTypeField(load_default=None)
    binance_markets = fields.List(fields.String(), load_default=None)
    ftx_subaccount = fields.String(load_default=None)


class ExchangesDataResourceSchema(Schema):
    location = LocationField(limit_to=ALL_SUPPORTED_EXCHANGES, load_default=None)


class ExchangesResourceRemoveSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, required=True)


class ExchangeBalanceQuerySchema(Schema):
    location = LocationField(limit_to=SUPPORTED_EXCHANGES, load_default=None)
    async_query = fields.Boolean(load_default=False)
    ignore_cache = fields.Boolean(load_default=False)


class BlockchainBalanceQuerySchema(Schema):
    blockchain = BlockchainField(load_default=None)
    async_query = fields.Boolean(load_default=False)
    ignore_cache = fields.Boolean(load_default=False)


class StatisticsAssetBalanceSchema(Schema):
    asset = AssetField(required=True)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


class StatisticsValueDistributionSchema(Schema):
    distribution_by = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=('location', 'asset')),
    )


class HistoryProcessingSchema(Schema):
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)
    async_query = fields.Boolean(load_default=False)


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
    event_type = SchemaEventTypeField(load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)

    @validates_schema
    def validate_report_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        value = data['order_by_attribute']
        if data['order_by_attribute'] not in (None, 'timestamp'):
            raise ValidationError(
                message=f'order_by_attribute for accounting report data can not be {value}',
                field_name='order_by_attribute',
            )

    @post_load
    def make_report_data_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        report_id = data.get('report_id')
        event_type = data.get('event_type')
        order_by_attribute = data['order_by_attribute'] if data['order_by_attribute'] is not None else 'timestamp'  # noqa: E501
        filter_query = ReportDataFilterQuery.make(
            order_by_attribute=order_by_attribute,
            order_ascending=data['ascending'],
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


class BaseXpubSchema(Schema):
    xpub = XpubField(required=True)
    derivation_path = DerivationPathField(load_default=None)
    async_query = fields.Boolean(load_default=False)


class XpubAddSchema(Schema):
    xpub = fields.String(required=True)
    derivation_path = DerivationPathField(load_default=None)
    async_query = fields.Boolean(load_default=False)
    label = fields.String(load_default=None)
    xpub_type = fields.String(
        required=False,
        load_default=None,
        validate=webargs.validate.OneOf(choices=('p2pkh', 'p2sh_p2wpkh', 'wpkh')),
    )
    tags = fields.List(fields.String(), load_default=None)

    @post_load
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Any:
        xpub_type_str = data.pop('xpub_type', None)
        try:
            xpub_type = None if xpub_type_str is None else XpubType.deserialize(xpub_type_str)
            xpub_hdkey = HDKey.from_xpub(data['xpub'], xpub_type=xpub_type, path='m')
        except (DeserializationError, XPUBError) as e:
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


def _transform_btc_address(
        ethereum: EthereumManager,
        given_address: str,
) -> BTCAddress:
    """Returns a SegWit/P2PKH/P2SH address (if existing) given an ENS domain.

    NB: ENS domains for BTC store the scriptpubkey. Check EIP-2304.
    """
    if not given_address.endswith('.eth'):
        return BTCAddress(given_address)

    try:
        resolved_address = ethereum.ens_lookup(
            given_address,
            blockchain=SupportedBlockchain.BITCOIN,
        )
    except (RemoteError, InputError) as e:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved '
            f'for Bitcoin due to: {str(e)}',
            field_name='address',
        ) from None

    if resolved_address is None:
        raise ValidationError(
            f'Given ENS address {given_address} could not be resolved for Bitcoin',
            field_name='address',
        ) from None

    try:
        address = scriptpubkey_to_btc_address(bytes.fromhex(resolved_address))
    except EncodingError as e:
        raise ValidationError(
            f'Given ENS address {given_address} does not contain a valid Bitcoin '
            f"scriptpubkey: {resolved_address}. Bitcoin address can't be obtained.",
            field_name='address',
        ) from e

    log.debug(f'Resolved BTC ENS {given_address} to {address}')

    return address


def _transform_eth_address(
        ethereum: EthereumManager, given_address: str) -> ChecksumEthAddress:
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
        if data['blockchain'] == SupportedBlockchain.BITCOIN:
            for idx, account in enumerate(data['accounts']):
                data['accounts'][idx]['address'] = _transform_btc_address(
                    ethereum=self.ethereum_manager,
                    given_address=account['address'],
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


class BlockchainAccountsPutSchema(BlockchainAccountsPatchSchema):
    async_query = fields.Boolean(load_default=False)


class BlockchainAccountsDeleteSchema(Schema):
    blockchain = BlockchainField(required=True, exclude_types=(SupportedBlockchain.ETHEREUM_BEACONCHAIN,))  # noqa: E501
    accounts = fields.List(fields.String(), required=True)
    async_query = fields.Boolean(load_default=False)

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
        if data['blockchain'] == SupportedBlockchain.BITCOIN:
            data['accounts'] = [
                _transform_btc_address(self.ethereum_manager, x) for x in data['accounts']
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
    assets = fields.List(AssetField(), required=True)


class IgnoredActionsGetSchema(Schema):
    action_type = ActionTypeField(load_default=None)


class IgnoredActionsModifySchema(Schema):
    action_type = ActionTypeField(required=True)
    action_ids = fields.List(fields.String(required=True), required=True)


class OptionalEthereumAddressSchema(Schema):
    address = EthereumAddressField(required=False, load_default=None)


class RequiredEthereumAddressSchema(Schema):
    address = EthereumAddressField(required=True)


class UnderlyingTokenInfoSchema(Schema):
    address = EthereumAddressField(required=True)
    weight = FloatingPercentageField(required=True)


def _validate_external_ids(
        data: Dict[str, Any],
        coingecko_obj: 'Coingecko',
        cryptocompare_obj: 'Cryptocompare',
) -> None:
    coingecko = data.get('coingecko')
    if coingecko and coingecko not in coingecko_obj.all_coins():
        raise ValidationError(
            f'Given coingecko identifier {coingecko} is not valid. Make sure the identifier '
            f'is correct and in this list https://api.coingecko.com/api/v3/coins/list',
            field_name='coingecko',
        )

    cryptocompare = data.get('cryptocompare')
    if cryptocompare and cryptocompare not in cryptocompare_obj.all_coins():
        raise ValidationError(
            f'Given cryptocompare identifier {cryptocompare} isnt valid. Make sure the identifier '
            f'is correct and in this list https://min-api.cryptocompare.com/data/all/coinlist',
            field_name='cryptocompare',
        )


class AssetSchema(Schema):
    asset_type = AssetTypeField(required=True, exclude_types=(AssetType.ETHEREUM_TOKEN,))
    name = fields.String(required=True)
    symbol = fields.String(required=True)
    started = TimestampField(load_default=None)
    forked = AssetField(load_default=None)
    swapped_for = AssetField(load_default=None)
    coingecko = fields.String(load_default=None)
    cryptocompare = fields.String(load_default=None)

    def __init__(self, coingecko: 'Coingecko', cryptocompare: 'Cryptocompare'):
        super().__init__()
        self.coingecko_obj = coingecko
        self.cryptocompare_obj = cryptocompare

    @validates_schema
    def validate_schema(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> None:
        _validate_external_ids(data, self.coingecko_obj, self.cryptocompare_obj)


class AssetSchemaWithIdentifier(AssetSchema):
    identifier = fields.String(required=True)


class EthereumTokenSchema(Schema):
    address = EthereumAddressField(required=True)
    decimals = fields.Integer(
        strict=True,
        validate=webargs.validate.Range(
            min=0,
            max=18,
            error='Ethereum token decimals should range from 0 to 18',
        ),
        required=True,
    )
    name = fields.String(required=True)
    symbol = fields.String(required=True)
    started = TimestampField(load_default=None)
    swapped_for = AssetField(load_default=None)
    coingecko = fields.String(load_default=None)
    cryptocompare = fields.String(load_default=None)
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
            # most probably validation happens at ModifyEthereumTokenSchema
            # so this is not needed. Kind of an ugly way to do this but can't
            # find a way around it at the moment
            _validate_external_ids(data, self.coingecko_obj, self.cryptocompare_obj)  # type: ignore  # noqa:E501

    @post_load
    def transform_data(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> EthereumToken:
        given_underlying_tokens = data.pop('underlying_tokens', None)
        underlying_tokens = None
        if given_underlying_tokens is not None:
            underlying_tokens = []
            for entry in given_underlying_tokens:
                underlying_tokens.append(UnderlyingToken(
                    address=entry['address'],
                    weight=entry['weight'],
                ))
        return EthereumToken.initialize(**data, underlying_tokens=underlying_tokens)


class ModifyEthereumTokenSchema(Schema):
    token = fields.Nested('EthereumTokenSchema', required=True)

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
        serialized_token = data['token'].serialize_all_info()
        serialized_token.pop('identifier')
        _validate_external_ids(
            data=serialized_token,
            coingecko_obj=token.schema.coingecko_obj,
            cryptocompare_obj=token.schema.cryptocompare_obj,
        )


class AssetsReplaceSchema(Schema):
    source_identifier = fields.String(required=True)
    target_asset = AssetField(required=True, form_with_incomplete_data=True)


class QueriedAddressesSchema(Schema):
    module = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=list(AVAILABLE_MODULES_MAP.keys())),
    )
    address = EthereumAddressField(required=True)


class DataImportSchema(Schema):
    source = fields.String(
        required=True,
        validate=webargs.validate.OneOf(
            choices=(
                'cointracking.info',
                'cryptocom',
                'blockfi-transactions',
                'blockfi-trades',
                'nexo',
                'shapeshift-trades',
                'uphold',
                'bisq',
            ),
        ),
    )
    file = FileField(required=True, allowed_extensions=('.csv',))
    timestamp_format = fields.String(load_default=None)


class AssetIconUploadSchema(Schema):
    asset = AssetField(required=True, form_with_incomplete_data=True)
    file = FileField(required=True, allowed_extensions=ALLOWED_ICON_EXTENSIONS)


class ExchangeRatesSchema(Schema):
    async_query = fields.Boolean(load_default=False)
    currencies = DelimitedOrNormalList(MaybeAssetField(), required=True)


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
    asset = AssetField(required=True, form_with_incomplete_data=True)


class CurrentAssetsPriceSchema(Schema):
    assets = DelimitedOrNormalList(
        AssetField(required=True),
        required=True,
        validate=webargs.validate.Length(min=1),
    )
    target_asset = AssetField(required=True)
    ignore_cache = fields.Boolean(load_default=False)
    async_query = fields.Boolean(load_default=False)


class HistoricalAssetsPriceSchema(Schema):
    assets_timestamp = fields.List(
        fields.Tuple(  # type: ignore # Tuple is not annotated
            (AssetField(required=True), TimestampField(required=True)),
            required=True,
        ),
        required=True,
        validate=webargs.validate.Length(min=1),
    )
    target_asset = AssetField(required=True)
    async_query = fields.Boolean(load_default=False)


class AssetUpdatesRequestSchema(Schema):
    async_query = fields.Boolean(load_default=False)
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
    from_asset = AssetField(required=True)
    to_asset = AssetField(required=True)


class NamedOracleCacheCreateSchema(NamedOracleCacheSchema):
    purge_old = fields.Boolean(load_default=False)
    async_query = fields.Boolean(load_default=False)


class NamedOracleCacheGetSchema(AsyncQueryArgumentSchema):
    oracle = HistoricalPriceOracleField(required=True)


class ERC20InfoSchema(Schema):
    address = EthereumAddressField(required=True)
    async_query = fields.Boolean(load_default=False)


class BinanceMarketsUserSchema(Schema):
    name = fields.String(required=True)
    location = LocationField(limit_to=[Location.BINANCEUS, Location.BINANCE], required=True)


class ManualPriceSchema(Schema):
    from_asset = AssetField(required=True)
    to_asset = AssetField(required=True)
    price = PriceField(required=True)


class TimedManualPriceSchema(ManualPriceSchema):
    timestamp = TimestampField(required=True)


class ManualPriceRegisteredSchema(Schema):
    from_asset = AssetField(load_default=None)
    to_asset = AssetField(load_default=None)


class ManualPriceDeleteSchema(Schema):
    from_asset = AssetField(required=True)
    to_asset = AssetField(required=True)
    timestamp = TimestampField(required=True)


class AvalancheTransactionQuerySchema(Schema):
    async_query = fields.Boolean(load_default=False)
    address = EthereumAddressField(load_default=None)
    from_timestamp = TimestampField(load_default=Timestamp(0))
    to_timestamp = TimestampField(load_default=ts_now)


class LimitsCounterResetSchema(Schema):
    location = fields.String(
        required=True,
        validate=webargs.validate.OneOf(choices=('ethereum_transactions',)),
    )


class SingleFileSchema(Schema):
    file = FileField(required=True)


class Eth2ValidatorSchema(Schema):
    validator_index = fields.Integer(
        load_default=None,
        validate=webargs.validate.Range(
            min=0,
            error='Validator index must be an integer >= 0',
        ),
    )
    public_key = fields.String(load_default=None)
    ownership_percentage = FloatingPercentageField(load_default=FVal(1))

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


class Eth2ValidatorPutSchema(Eth2ValidatorSchema):
    async_query = fields.Boolean(load_default=False)


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
        value = data['order_by_attribute']
        if data['order_by_attribute'] not in (
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
        ):
            raise ValidationError(
                message=f'order_by_attribute for eth2 daily stats can not be {value}',
                field_name='order_by_attribute',
            )

    @post_load
    def make_eth2_daily_stats_query(  # pylint: disable=no-self-use
            self,
            data: Dict[str, Any],
            **_kwargs: Any,
    ) -> Dict[str, Any]:
        order_by_attribute = data['order_by_attribute'] if data['order_by_attribute'] is not None else 'timestamp'  # noqa: E501
        filter_query = Eth2DailyStatsFilterQuery.make(
            order_by_attribute=order_by_attribute,
            order_ascending=data['ascending'],
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
