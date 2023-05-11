import logging
import urllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal, Optional, Union, cast

import webargs
from eth_utils import to_checksum_address
from marshmallow import fields
from marshmallow.exceptions import ValidationError
from marshmallow.utils import is_iterable_but_not_string
from werkzeug.datastructures import FileStorage

from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.assets.asset import (
    Asset,
    AssetWithNameAndType,
    AssetWithOracles,
    CryptoAsset,
    EvmToken,
    Nft,
)
from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.utils import is_valid_derivation_path
from rotkehlchen.constants.misc import NFT_DIRECTIVE, ZERO
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.errors.misc import XPUBError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_fee,
    deserialize_hex_color_code,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ApiSecret,
    AssetAmount,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    Fee,
    HexColorCode,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.enums import (
    DBCharEnumMixIn,
    DBIntEnumMixIn,
    SerializableEnumIntValueMixin,
    SerializableEnumMixin,
    SerializableEnumNameMixin,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class IncludeExcludeListField(fields.Field):
    """ A field that accepts an object like the following and deserializes it to the proper types.
    {
        "values": [val1, val2, val3],
        "behaviour": "exclude"
    }
    Eventually, this object will be used to create a filter query to the db, to return all the db
    table entries where this field's value is not in [val1, val2, val3]. The behaviour key
    can be either "include" or "exclude" and it defaults to "include" if not present.
    """
    def __init__(
            self,
            values_field: 'SerializableEnumField',
            *args: Any,
            **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.values_field = values_field

    def _deserialize(
            self,
            value: dict[str, Union[list, str]],
            attr: Optional[str],
            data: Any,
            **kwargs: Any,
    ) -> IncludeExcludeFilterData:

        if 'behaviour' not in value:
            # If for any reason the behaviour key is not given, we use the default behaviour.
            value['behaviour'] = 'include'

        values = value['values']
        behaviour = value['behaviour']

        if behaviour not in ['include', 'exclude']:
            raise ValidationError("Behaviour must be either 'include' or 'exclude'.")

        deserialized_values = DelimitedOrNormalList(self.values_field).deserialize(values)
        deserialized_behaviour = cast(Literal['IN', 'NOT IN'], 'IN' if behaviour == 'include' else 'NOT IN')  # noqa: E501
        return IncludeExcludeFilterData(
            values=deserialized_values,
            behaviour=deserialized_behaviour,
        )


class DelimitedOrNormalList(webargs.fields.DelimitedList):
    """This is equal to DelimitedList in webargs v5.6.0

    Essentially accepting either a delimited string or a list-like object

    We introduce it due to them implementing https://github.com/marshmallow-code/webargs/issues/423

    We also enforce the len(list) != 0 rule here.
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
            value: Union[list[str], str],
            attr: Optional[str],
            data: dict[str, Any],
            **kwargs: Any,
    ) -> list[Any]:
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
                if is_iterable_but_not_string(value)
                else value.split(self.delimiter)  # type: ignore
            )
        except AttributeError as e:
            raise self.make_error('invalid') from e

        if len(value) == 0:
            raise ValidationError('List cant be empty')

        # purposefully skip the superclass here
        return fields.List._deserialize(self, ret, attr, data, **kwargs)  # pylint: disable=bad-super-call  # noqa: E501


class TimestampField(fields.Field):

    def __init__(self, ts_multiplier: int = 1, **kwargs: Any) -> None:
        self.ts_multiplier = ts_multiplier
        super().__init__(**kwargs)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> Timestamp:
        try:
            timestamp = deserialize_timestamp(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return Timestamp(timestamp * self.ts_multiplier)


class TimestampUntilNowField(TimestampField):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],
            data: Optional[Mapping[str, Any]],
            **kwargs: Any,
    ) -> Timestamp:
        timestamp = super()._deserialize(value, attr, data, **kwargs)
        if timestamp > ts_now():
            raise ValidationError('Given date cannot be in the future')

        return Timestamp(timestamp * self.ts_multiplier)


class ColorField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
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
            data: Optional[Mapping[str, Any]],
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


class AmountField(fields.Field):

    @staticmethod
    def _serialize(
            value: AssetAmount,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: Union[str, int],
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
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
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> Price:
        try:
            price = deserialize_price(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        if price < ZERO:
            raise ValidationError('A negative price is not allowed')

        return price


class FeeField(fields.Field):

    @staticmethod
    def _serialize(
            value: Fee,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> Optional[str]:
        # Fee can be missing so we need to handle None when serializing from schema
        return str(value) if value else None

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
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
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
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
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> SupportedBlockchain:
        try:
            chain_type = SupportedBlockchain.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        if self.exclude_types and chain_type in self.exclude_types:
            raise ValidationError(f'Blockchain name {str(value)} is not allowed in this endpoint')
        return chain_type


class SerializableEnumField(fields.Field):
    """A field that takes an enum following the SerializableEnumMixin interface
    """
    def __init__(self, enum_class: Union[type[SerializableEnumNameMixin], type[SerializableEnumIntValueMixin], type[DBCharEnumMixIn], type[DBIntEnumMixIn]], **kwargs: Any) -> None:  # noqa: E501
        """We give all possible types as unions instead of just type[SerializableEnumMixin]
        due to this bug https://github.com/python/mypy/issues/4717
        Normally it should have sufficed to give just the former.
        """
        self.enum_class = enum_class
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: SerializableEnumMixin,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return value.serialize()

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> Any:
        try:
            result = self.enum_class.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        return result


class EvmChainNameField(fields.Field):
    """A special case of serializing to an enum. Using the string name of an evm
    chain to serialize to chain id, so the frontend does not have to remember a
    mapping of chain id to evm chain name"""

    def __init__(self, *, limit_to: Optional[list[SUPPORTED_CHAIN_IDS]] = None, **kwargs: Any) -> None:  # noqa: E501
        self.limit_to = limit_to
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: ChainID,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> Optional[str]:
        return value.to_name() if value else None

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> ChainID:
        try:
            chain_id = ChainID.deserialize_from_name(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        if self.limit_to is not None and chain_id not in self.limit_to:
            raise ValidationError(
                f'Given chain_id {value} is not one of '
                f'{",".join([str(x) for x in self.limit_to])} as needed by the endpoint',
            )

        return chain_id


class AssetField(fields.Field):

    def __init__(
            self,
            *,
            expected_type: Union[
                type[Asset],
                type[AssetWithNameAndType],
                type[AssetWithOracles],
                type[CryptoAsset],
                type[EvmToken],
            ],
            form_with_incomplete_data: bool = False,
            **kwargs: Any,
    ) -> None:
        self.expected_type = expected_type
        self.form_with_incomplete_data = form_with_incomplete_data
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: Asset,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> Optional[str]:
        # Asset can be missing so we need to handle None when serializing from schema
        return value.identifier if value else None

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> Asset:
        if isinstance(value, str) is False:
            raise ValidationError(f'Tried to initialize an asset out of a non-string identifier {value}')  # noqa: E501
        # Since the identifier could be url encoded for evm tokens in urls we need to unquote it
        real_value: str = urllib.parse.unquote(value)
        asset: Asset
        try:
            if self.expected_type == Asset:
                if real_value.startswith(NFT_DIRECTIVE):
                    asset = Nft(identifier=real_value)
                else:
                    asset = Asset(identifier=real_value).check_existence()
            elif self.expected_type == AssetWithNameAndType:
                asset = Asset(identifier=real_value).resolve_to_asset_with_name_and_type()
            elif self.expected_type == AssetWithOracles:
                asset = Asset(identifier=real_value).resolve_to_asset_with_oracles()
            elif self.expected_type == CryptoAsset:
                asset = CryptoAsset(real_value)
            else:  # EvmToken
                asset = EvmToken(real_value)
        except (DeserializationError, UnknownAsset, WrongAssetType) as e:
            raise ValidationError(str(e)) from e

        return asset


class MaybeAssetField(fields.Field):

    def __init__(
            self,
            *,
            expected_type: type[AssetWithOracles],  # the only possible type now
            form_with_incomplete_data: bool = False,
            **kwargs: Any,
    ) -> None:
        self.form_with_incomplete_data = form_with_incomplete_data
        self.expected_type = expected_type
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: Asset,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> Optional[str]:
        # Asset can be missing so we need to handle None when serializing from schema
        return str(value.identifier) if value else None

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> Optional[Asset]:
        try:
            asset = Asset(identifier=value).resolve_to_asset_with_oracles()
        except DeserializationError as e:
            raise ValidationError(str(e)) from e
        except (UnknownAsset, WrongAssetType):
            log.error(f'Failed to deserialize asset {value}')
            return None

        return asset


class EvmAddressField(fields.Field):

    @staticmethod
    def _serialize(
            value: ChecksumEvmAddress,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> ChecksumEvmAddress:
        # Make sure that given value is an ethereum address
        try:
            address = to_checksum_address(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f'Given value {value} is not an ethereum address',
                field_name='address',
            ) from e

        return address


class EVMTransactionHashField(fields.Field):

    @staticmethod
    def _serialize(
            value: EVMTxHash,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return value.hex()

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> EVMTxHash:
        # Make sure that given value is a transaction hash
        if not isinstance(value, str):
            raise ValidationError('Transaction hash should be a string')

        try:
            txhash = bytes.fromhex(value.removeprefix('0x'))
        except ValueError as e:
            raise ValidationError(f'Could not turn transaction hash {value} to bytes') from e

        length = len(txhash)
        if length != 32:
            raise ValidationError(f'Transaction hashes should be 32 bytes in length. Given {length=}')  # noqa: E501

        return deserialize_evm_tx_hash(txhash)


class AssetTypeField(fields.Field):

    def __init__(self, *, exclude_types: Optional[Sequence[AssetType]] = None, **kwargs: Any) -> None:  # noqa: E501
        self.exclude_types = exclude_types
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: AssetType,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> AssetType:
        try:
            asset_type = AssetType.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(str(e)) from e

        if self.exclude_types and asset_type in self.exclude_types:
            raise ValidationError(f'Asset type {str(asset_type)} is not allowed in this endpoint')

        return asset_type


class LocationField(fields.Field):

    def __init__(self, *, limit_to: Optional[tuple[Location, ...]] = None, **kwargs: Any) -> None:  # noqa: E501
        self.limit_to = limit_to
        super().__init__(**kwargs)

    @staticmethod
    def _serialize(
            value: Location,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return str(value)

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
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


class ApiKeyField(fields.Field):

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> ApiKey:
        if not isinstance(value, str):
            raise ValidationError('Given API Key should be a string')
        return ApiKey(value)


class ApiSecretField(fields.Field):

    @staticmethod
    def _serialize(
            value: ApiSecret,
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> str:
        return str(value.decode())

    def _deserialize(
            self,
            value: str,
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
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
            data: Optional[Mapping[str, Any]],
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
            value: dict[str, Any],
            attr: Optional[str],  # pylint: disable=unused-argument
            obj: Any,
            **_kwargs: Any,
    ) -> dict[str, Any]:
        # TODO: If this ever gets used we probably need to change
        # the dict keys to identifiers from assets
        return value

    def _deserialize(
            self,
            value: dict[str, str],
            attr: Optional[str],  # pylint: disable=unused-argument
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> dict[Asset, Literal['remote', 'local']]:
        if not isinstance(value, dict):
            raise ValidationError('A dict object should be given for the conflictss')

        if len(value) == 0:
            raise ValidationError('An empty dict object should not be given. Provide null instead')

        deserialized_dict = {}
        for asset_id, choice in value.items():
            try:
                asset = Asset(asset_id).check_existence()
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
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> Union[Path, FileStorage]:
        if isinstance(value, FileStorage):
            if self.allowed_extensions is not None and value.filename and not any(value.filename.endswith(x) for x in self.allowed_extensions):  # noqa: E501
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

        if self.allowed_extensions is not None and not any(path.suffix == x for x in self.allowed_extensions):  # noqa: E501
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
            data: Optional[Mapping[str, Any]],
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
            data: Optional[Mapping[str, Any]],
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
            data: Optional[Mapping[str, Any]],
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
            data: Optional[Mapping[str, Any]],
            **_kwargs: Any,
    ) -> HistoricalPriceOracle:
        try:
            historical_price_oracle = HistoricalPriceOracle.deserialize(value)
        except DeserializationError as e:
            raise ValidationError(f'Invalid historical price oracle: {value}') from e

        return historical_price_oracle


class NonEmptyList(fields.List):

    def _deserialize(
            self,
            value: Any,
            attr: Optional[str],
            data: Optional[Mapping[str, Any]],
            **kwargs: Any,
    ) -> list[Any]:
        result = super()._deserialize(value=value, attr=attr, data=data, **kwargs)
        if len(result) == 0:
            raise ValidationError('List cant be empty')

        return result
