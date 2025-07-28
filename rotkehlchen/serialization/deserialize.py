import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeVar, overload

from eth_utils import to_checksum_address

from rotkehlchen.chain.evm.l2_with_l1_fees.types import (
    L2_CHAINIDS_WITH_L1_FEES,
    L2ChainIdsWithL1FeesType,
    L2WithL1FeesTransaction,
)
from rotkehlchen.chain.optimism.constants import OP_BEDROCK_UPGRADE
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.asset import UnprocessableTradePair
from rotkehlchen.errors.serialization import ConversionError, DeserializationError
from rotkehlchen.externalapis.utils import maybe_read_integer, read_hash, read_integer
from rotkehlchen.fval import AcceptableFValInitInput, FVal
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EvmTransactionAuthorization,
    EVMTxHash,
    HexColorCode,
    Timestamp,
    TimestampMS,
    TradePair,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import convert_to_int, create_timestamp, iso8601ts_to_timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.l2_with_l1_fees.node_inquirer import L2WithL1FeesInquirer
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def deserialize_timestamp(timestamp: float | (str | FVal)) -> Timestamp:
    """Deserializes a timestamp from a json entry. Given entry can either be a
    string or an int.

    Can throw DeserializationError if the data is not as expected
    """
    if timestamp is None:
        raise DeserializationError('Failed to deserialize a timestamp entry from a null entry')

    if isinstance(timestamp, int):
        processed_timestamp = Timestamp(timestamp)
    elif isinstance(timestamp, FVal):
        try:
            processed_timestamp = Timestamp(timestamp.to_int(exact=True))
        except ConversionError as e:
            # An fval was not representing an exact int
            raise DeserializationError(
                'Tried to deserialize a timestamp from a non-exact int FVal entry',
            ) from e
    elif isinstance(timestamp, (str | float)):
        try:
            processed_timestamp = Timestamp(FVal(timestamp).to_int(exact=True))
        except (ValueError, ConversionError) as e:
            # String could not be turned to an int
            raise DeserializationError(
                f'Failed to deserialize a timestamp entry from string {timestamp} due to {e}',
            ) from e
    else:
        raise DeserializationError(
            f'Failed to deserialize a timestamp entry. Unexpected type {type(timestamp)} given',
        )

    if processed_timestamp < 0:
        raise DeserializationError(
            f'Failed to deserialize a timestamp entry. Timestamps can not have'
            f' negative values. Given value was {processed_timestamp}',
        )

    return processed_timestamp


def deserialize_timestamp_from_date(
        date: str | None,
        formatstr: str,
        location: str,
        skip_milliseconds: bool = False,
) -> Timestamp:
    """Deserializes a timestamp from a date entry depending on the format str

    formatstr can also have a special value of 'iso8601' in which case the iso8601
    function will be used.

    Can throw DeserializationError if the data is not as expected
    """
    if not date:
        raise DeserializationError(
            f'Failed to deserialize a timestamp from a null entry in {location}',
        )

    if not isinstance(date, str):
        raise DeserializationError(
            f'Failed to deserialize a timestamp from a {type(date)} entry in {location}',
        )

    if skip_milliseconds:
        # Seems that poloniex added milliseconds in their timestamps.
        # https://github.com/rotki/rotki/issues/1631
        # We don't deal with milliseconds in rotki times so we can safely remove it
        splits = date.split('.', 1)
        if len(splits) == 2:
            date = splits[0]

    if formatstr == 'iso8601':
        return iso8601ts_to_timestamp(date)

    date = date.rstrip('Z')
    try:
        return Timestamp(create_timestamp(datestr=date, formatstr=formatstr))
    except ValueError as e:
        raise DeserializationError(
            f'Failed to deserialize {date} {location} timestamp entry',
        ) from e


def deserialize_timestamp_from_bitstamp_date(date: str) -> Timestamp:
    """Deserializes a timestamp from a bitstamp api query result date entry

    The bitstamp dates follow the %Y-%m-%d %H:%M:%S format but are in UTC time
    and not local time so can't use iso8601ts_to_timestamp() directly since that
    would interpret them as local time.

    Can throw DeserializationError if the data is not as expected
    """
    return deserialize_timestamp_from_date(
        date,
        '%Y-%m-%d %H:%M:%S',
        'bitstamp',
        skip_milliseconds=True,
    )


def deserialize_timestamp_from_floatstr(time: str | (FVal | float)) -> Timestamp:
    """Deserializes a timestamp from a kraken api query result entry
    Kraken has timestamps in floating point strings. Example: '1561161486.3056'.

    If the dictionary has passed through rlk_jsonloads the entry can also be an Fval

    Can throw DeserializationError if the data is not as expected
    """
    if not time:
        raise DeserializationError(
            'Failed to deserialize a timestamp entry from a null entry in kraken',
        )

    if isinstance(time, int):
        return Timestamp(time)
    if isinstance(time, float | str):
        try:
            return Timestamp(convert_to_int(time, accept_only_exact=False))
        except ConversionError as e:
            raise DeserializationError(
                f'Failed to deserialize {time} kraken timestamp entry from {type(time)}',
            ) from e
    if isinstance(time, FVal):
        try:
            return Timestamp(time.to_int(exact=False))
        except ConversionError as e:
            raise DeserializationError(
                f'Failed to deserialize {time} kraken timestamp entry from an FVal',
            ) from e

    # else
    raise DeserializationError(
        f'Failed to deserialize a timestamp entry from a {type(time)} entry in kraken',
    )


def deserialize_timestamp_ms_from_intms(value: Any) -> TimestampMS:
    """Deserializes a TimestampMS from an integer timestamp in milliseconds.
    May raise DeserializationError if the data is not as expected.
    """
    if not isinstance(value, int):
        raise DeserializationError(
            f'Failed to deserialize a timestamp entry from a {type(value)} entry',
        )

    return TimestampMS(value)


def deserialize_timestamp_from_intms(value: Any) -> Timestamp:
    """Deserializes a Timestamp from an integer timestamp in milliseconds.
    May raise DeserializationError if the data is not as expected.
    """
    return Timestamp(int(deserialize_timestamp_ms_from_intms(value) / 1000))


def deserialize_fval(
        value: AcceptableFValInitInput,
        name: str | None = None,
        location: str | None = None,
) -> FVal:
    try:
        result = FVal(value)
    except ValueError as e:
        msg = f'Failed to deserialize value entry: {e!s}'
        if name is not None:
            msg += f' for {name}'
        if location is not None:
            msg += f' during {location}'
        raise DeserializationError(msg) from e

    return result


def deserialize_optional_to_optional_fval(
        value: AcceptableFValInitInput | None,
        name: str | None = None,
        location: str | None = None,
) -> FVal | None:
    """
    Deserializes an FVal from a field that was optional and if None returns None
    """
    if value is None:
        return None

    return deserialize_fval(value=value, name=name, location=location)


def deserialize_fval_or_zero(
        value: AcceptableFValInitInput | None,
        name: str | None = None,
        location: str | None = None,
) -> FVal:
    """
    Deserializes an FVal from a field that was optional and if None returns ZERO
    """
    if value is None:
        return ZERO

    return deserialize_fval(value=value, name=name, location=location)


def deserialize_fval_force_positive(
        value: AcceptableFValInitInput,
        name: str | None = None,
        location: str | None = None,
) -> FVal:
    """Acts exactly like deserialize_fval but also forces the number to be positive

    Is needed for some places like some exchanges that list the withdrawal amounts as
    negative numbers because it's a withdrawal.

    May raise:
    - DeserializationError
    """
    if (result := deserialize_fval(value=value, name=name, location=location)) < ZERO:
        result = FVal(abs(result))
    return result


def _split_pair(pair: TradePair) -> tuple[str, str]:
    assets = pair.split('_')
    if len(assets) != 2:
        # Could not split the pair
        raise UnprocessableTradePair(pair)

    if len(assets[0]) == 0 or len(assets[1]) == 0:
        # no base or no quote asset
        raise UnprocessableTradePair(pair)

    return assets[0], assets[1]


def get_pair_position_str(pair: TradePair, position: str) -> str:
    """Get the string representation of an asset of a trade pair"""
    assert position in {'first', 'second'}
    base_str, quote_str = _split_pair(pair)
    return base_str if position == 'first' else quote_str


def deserialize_asset_movement_event_type(
        value: str,
) -> Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL]:
    """Takes a string and determines whether to accept it as an asset movement event_type

    Can throw DeserializationError if value is not as expected
    """
    if isinstance(value, str):
        if (lowered_value := value.lower()) == 'deposit':
            return HistoryEventType.DEPOSIT
        if lowered_value in {'withdraw', 'withdrawal'}:
            return HistoryEventType.WITHDRAWAL
        raise DeserializationError(
            f'Failed to deserialize asset movement category symbol. Unknown {value}',
        )

    raise DeserializationError(
        f'Failed to deserialize asset movement category from {type(value)} entry',
    )


def deserialize_hex_color_code(symbol: str) -> HexColorCode:
    """Takes a string either from the API or the DB and deserializes it into
    a hexadecimal color code.

    Can throw DeserializationError if the symbol is not as expected
    """
    if not isinstance(symbol, str):
        raise DeserializationError(
            f'Failed to deserialize color code from {type(symbol).__name__} entry',
        )

    try:
        color_value = int(symbol, 16)
    except ValueError as e:
        raise DeserializationError(
            f'The given color code value "{symbol}" could not be processed as a hex color value',
        ) from e

    if color_value < 0 or color_value > 16777215:
        raise DeserializationError(
            f'The given color code value "{symbol}" is out of range for a normal color field',
        )

    if len(symbol) != 6:
        raise DeserializationError(
            f'The given color code value "{symbol}" does not have 6 hexadecimal digits',
        )

    return HexColorCode(symbol)


def deserialize_evm_address(symbol: str) -> ChecksumEvmAddress:
    """Deserialize a symbol, check that it's a valid ethereum address
    and return it checksummed.

    This function can raise DeserializationError if the address is not
    valid
    """
    try:
        return to_checksum_address(symbol)
    except ValueError as e:
        raise DeserializationError(
            f'Invalid evm address: {symbol}',
        ) from e


def deserialize_int_from_str(symbol: str, location: str) -> int:
    if not isinstance(symbol, str):
        raise DeserializationError(f'Expected a string but got {type(symbol)} at {location}')

    try:
        result = int(symbol)
    except ValueError as e:
        raise DeserializationError(
            f'Could not turn string "{symbol}" into an integer at {location}',
        ) from e

    return result


def deserialize_int_from_hex(symbol: str, location: str) -> int:
    """Takes a hex string and turns it into an integer. Some apis returns 0x as
    a hex int and this may be an error. So we handle this as return 0 here.

    May Raise:
    - DeserializationError if the given data are in an unexpected format.
    """
    if not isinstance(symbol, str):
        raise DeserializationError(f'Expected hex string but got {type(symbol)} at {location}')

    if symbol == '0x':
        return 0

    try:
        result = int(symbol, 16)
    except ValueError as e:
        raise DeserializationError(
            f'Could not turn string "{symbol}" into an integer at {location}',
        ) from e

    return result


def deserialize_int_from_hex_or_int(symbol: str | int, location: str) -> int:
    """Takes a symbol which can either be an int or a hex string and
    turns it into an integer

    May Raise:
    - DeserializationError if the given data are in an unexpected format.
    """
    if isinstance(symbol, int):
        result = symbol
    elif isinstance(symbol, str):
        if symbol == '0x':
            return 0

        try:
            result = int(symbol, 16)
        except ValueError as e:
            raise DeserializationError(
                f'Could not turn string "{symbol}" into an integer {location}',
            ) from e
    else:
        raise DeserializationError(
            f'Unexpected type {type(symbol)} given to '
            f'deserialize_int_from_hex_or_int() for {location}',
        )

    return result


def deserialize_int(value: str | int) -> int:
    """
    Deserialize int from an entry that could be a string or an integer
    May raise:
    - DeserializationError if value is not a value that can be converted to integer
    """
    try:
        result = int(value)
    except ValueError as e:
        raise DeserializationError(f'Could not transform to integer the {value=}') from e

    return result


def deserialize_str(value: Any) -> str:
    """
    Deserialize str from an entry
    May raise:
    - DeserializationError if value is not a string
    """
    if not isinstance(value, str):
        raise DeserializationError(f'Could not deserialize {value} as string')

    return value


X = TypeVar('X')
Y = TypeVar('Y')


def deserialize_optional(input_val: X | None, fn: Callable[[X], Y]) -> Y | None:
    """An optional deserialization wrapper for any deserialize function"""
    if input_val is None:
        return None

    return fn(input_val)


def _get_transaction_receipt(
        tx_hash: EVMTxHash,
        chain_id: ChainID,
        timestamp: Timestamp,
        evm_inquirer: 'EvmNodeInquirer',
) -> dict[str, Any]:
    """Get the transaction receipt for a tx during deserialization.
    Handles a special case for Optimism transactions before the bedrock upgrade where some nodes
    return null L1 fee values so we need to try the official mainnet node first regardless of the
    default call order.
    """
    call_order = evm_inquirer.default_call_order()
    if chain_id == ChainID.OPTIMISM and timestamp < OP_BEDROCK_UPGRADE:
        call_order.sort(
            key=lambda x: not x.node_info.endpoint.startswith('https://mainnet.optimism.io'),
        )

    return evm_inquirer.get_transaction_receipt(
        tx_hash=tx_hash,
        call_order=call_order,
    )


@overload
def deserialize_evm_transaction(
        data: dict[str, Any],
        internal: Literal[True],
        chain_id: ChainID,
        evm_inquirer: Optional['EvmNodeInquirer'] = None,
        parent_tx_hash: Optional['EVMTxHash'] = None,
) -> tuple[EvmInternalTransaction, None]:
    ...


@overload
def deserialize_evm_transaction(
        data: dict[str, Any],
        internal: Literal[False],
        chain_id: ChainID,
        evm_inquirer: None,
        parent_tx_hash: Optional['EVMTxHash'] = None,
) -> tuple[EvmTransaction, None]:
    ...


@overload
def deserialize_evm_transaction(
        data: dict[str, Any],
        internal: Literal[False],
        chain_id: L2ChainIdsWithL1FeesType,
        evm_inquirer: 'L2WithL1FeesInquirer',
        parent_tx_hash: Optional['EVMTxHash'] = None,
) -> tuple[L2WithL1FeesTransaction, dict[str, Any]]:
    ...


@overload
def deserialize_evm_transaction(
        data: dict[str, Any],
        internal: Literal[False],
        chain_id: ChainID,
        evm_inquirer: 'EvmNodeInquirer',
        parent_tx_hash: Optional['EVMTxHash'] = None,
) -> tuple[EvmTransaction, dict[str, Any]]:
    ...


def deserialize_evm_transaction(
        data: dict[str, Any],
        internal: bool,
        chain_id: ChainID,
        evm_inquirer: Optional['EvmNodeInquirer'] = None,
        parent_tx_hash: Optional['EVMTxHash'] = None,
) -> tuple[EvmTransaction | EvmInternalTransaction, dict[str, Any] | None]:
    """Reads dict data of a transaction and deserializes it.
    If the transaction is not from etherscan then it's missing some data
    so evm inquirer is used to fetch it.

    If it's an internal transaction it's possible, depending on the data source (for example
    https://docs.etherscan.io/api-endpoints/accounts#get-internal-transactions-by-transaction-hash)
    , that the hash is missing from the data string, so it is provided in that case
    as an argument.

    Can raise DeserializationError if something is wrong

    Returns the deserialized transaction and optionally raw receipt data if it was queried
    and if this is not for an internal transaction.
    """
    source = 'etherscan' if evm_inquirer is None else 'web3'
    raw_receipt_data = None
    try:
        tx_hash = parent_tx_hash if parent_tx_hash is not None else deserialize_evm_tx_hash(data['hash'])  # noqa: E501
        block_number = read_integer(data, 'blockNumber', source)
        block_data = None
        if 'timeStamp' not in data:
            if evm_inquirer is None:
                raise DeserializationError('Got in deserialize evm transaction without timestamp and without evm inquirer')  # noqa: E501

            block_data = evm_inquirer.get_block_by_number(block_number)
            timestamp = Timestamp(read_integer(block_data, 'timestamp', source))
        else:
            timestamp = deserialize_timestamp(data['timeStamp'])

        from_address = deserialize_evm_address(data['from'])
        is_empty_to_address = data['to'] != '' and data['to'] is not None
        to_address = deserialize_evm_address(data['to']) if is_empty_to_address else None
        value = read_integer(data, 'value', source)

        authorization_list: list[EvmTransactionAuthorization] | None
        if (raw_authorization_list := data.get('authorizationList')) is not None:
            authorization_list = []
            for entry in raw_authorization_list:
                try:
                    authorization_list.append(EvmTransactionAuthorization(
                        nonce=read_integer(entry, 'nonce', source),
                        delegated_address=deserialize_evm_address(entry['address']),
                    ))
                except DeserializationError as e:
                    log.error(f'Unable to deserialize authorization entry {entry} due to {e}')
        else:
            authorization_list = None

        if internal:
            return EvmInternalTransaction(
                parent_tx_hash=tx_hash,
                chain_id=chain_id,
                # traceId is missing when querying by parent hash
                trace_id=int(data.get('traceId', '0')),
                from_address=from_address,
                to_address=to_address,
                value=value,
                gas=int(data.get('gas', '0')),
                gas_used=int(data.get('gasUsed', '0')),
            ), None

        # else normal transaction
        gas_price = read_integer(data=data, key='gasPrice', api=source)
        input_data = read_hash(data, 'input', source)
        if 'gasUsed' not in data:  # some etherscan APIs may have this
            if evm_inquirer is None:
                raise DeserializationError('Got in deserialize evm transaction without gasUsed and without evm inquirer')  # noqa: E501
            raw_receipt_data = _get_transaction_receipt(
                tx_hash=tx_hash,
                chain_id=chain_id,
                timestamp=timestamp,
                evm_inquirer=evm_inquirer,
            )
            gas_used = read_integer(raw_receipt_data, 'gasUsed', source)
            if chain_id == ChainID.ARBITRUM_ONE:
                # In Arbitrum One the gas price included in the data is the "Gas Price Bid" and not
                # the "Gas Price Paid". The latter is the actual gas price paid for the transaction
                # and is included in the transaction receipt as the effectiveGasPrice.
                gas_price = read_integer(raw_receipt_data, 'effectiveGasPrice', source)
        else:
            gas_used = read_integer(data, 'gasUsed', source)
        nonce = read_integer(data, 'nonce', source)

        if chain_id in L2_CHAINIDS_WITH_L1_FEES:
            try:  # if data is from etherscan's txlist it will already include the L1 fee
                l1_fee = int(data['L1FeesPaid'])
            except (KeyError, ValueError):  # data is not from txlist or malformed data from txlist
                if evm_inquirer is None:
                    l1_fee = None
                else:
                    if raw_receipt_data is None:
                        raw_receipt_data = _get_transaction_receipt(
                            tx_hash=tx_hash,
                            chain_id=chain_id,
                            timestamp=timestamp,
                            evm_inquirer=evm_inquirer,
                        )
                    try:
                        l1_fee = maybe_read_integer(raw_receipt_data, 'l1Fee', source)
                    except DeserializationError as e:  # Fall back to etherscan (via txlist)
                        log.warning(f'Failed to get L1 fee from receipt due to {e!s}. Falling back to etherscan.')  # noqa: E501
                        l1_fee = evm_inquirer.etherscan.maybe_get_l1_fees(
                            chain_id=chain_id,  # type: ignore[arg-type]  # mypy doesn't understand that the if check above limits chain_id
                            account=from_address,
                            tx_hash=tx_hash,
                            block_number=block_number,
                        )

            if l1_fee is None:
                log.error(
                    f'Failed to retrieve L1 fee while deserializing {chain_id.to_name()} '
                    f'transaction {tx_hash.hex()}. Using 0 L1 fee.',
                )
                l1_fee = 0

            return L2WithL1FeesTransaction(
                timestamp=timestamp,
                chain_id=chain_id,
                block_number=block_number,
                tx_hash=tx_hash,
                from_address=from_address,
                to_address=to_address,
                value=value,
                gas=read_integer(data, 'gas', source),
                gas_price=gas_price,
                gas_used=gas_used,
                input_data=input_data,
                nonce=nonce,
                l1_fee=l1_fee,
                authorization_list=authorization_list,
            ), raw_receipt_data
    except KeyError as e:
        raise DeserializationError(
            f'evm {"internal" if internal else ""}transaction from {source} missing expected key {e!s}',  # noqa: E501
        ) from e
    else:
        return EvmTransaction(
            timestamp=timestamp,
            chain_id=chain_id,
            block_number=block_number,
            tx_hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            value=value,
            gas=read_integer(data, 'gas', source),
            gas_price=gas_price,
            gas_used=gas_used,
            input_data=input_data,
            nonce=nonce,
            authorization_list=authorization_list,
        ), raw_receipt_data


R = TypeVar('R')


def ensure_type(symbol: Any, expected_type: type[R], location: str) -> R:
    if isinstance(symbol, expected_type) is True:
        return symbol
    raise DeserializationError(
        f'Value "{symbol}" has type {type(symbol)} '
        f'but expected {expected_type} at location "{location}"',
    )
