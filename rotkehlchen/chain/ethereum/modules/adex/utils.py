from typing import Union

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ethereum_address,
    deserialize_timestamp,
)

from .typing import AdexEventDBTuple, AdexEventType, Bond, ChannelWithdraw, Unbond, UnbondRequest

SUBGRAPH_REMOTE_ERROR_MSG = (
    "Failed to request the AdEx subgraph due to {error_msg}. "
    "All staking balances and events history queries are not functioning until this is fixed. "  # noqa: E501
    "Probably will get fixed with time. If not report it to rotki's support channel"  # noqa: E501
)
# Constants from the AdExNetwork repo
IDENTITY_FACTORY_ADDR = '0x9fe0d438E3c29C7CFF949aD8e8dA9403A531cC1A'
IDENTITY_PROXY_INIT_CODE = (
    '0x608060405234801561001057600080fd5b5060026000803073ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060006101000a81548160ff021916908360ff160217905550600260008073'  # noqa: E501
    '{signer_address}'
    '73ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060006101000a81548160ff021916908360ff1602179055506000734470bb87d77b963a013db939be332f927f2b992e9050600073ade00c28244d5ce17d72e40330b1c318cd12b7c3905060008273ffffffffffffffffffffffffffffffffffffffff166370a08231306040518263ffffffff1660e01b81526004016101429190610501565b60206040518083038186803b15801561015a57600080fd5b505afa15801561016e573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610192919061045a565b90506000811115610276578273ffffffffffffffffffffffffffffffffffffffff1663095ea7b383836040518363ffffffff1660e01b81526004016101d892919061051c565b600060405180830381600087803b1580156101f257600080fd5b505af1158015610206573d6000803e3d6000fd5b505050508173ffffffffffffffffffffffffffffffffffffffff166394b918de826040518263ffffffff1660e01b81526004016102439190610560565b600060405180830381600087803b15801561025d57600080fd5b505af1158015610271573d6000803e3d6000fd5b505050505b60008273ffffffffffffffffffffffffffffffffffffffff166370a08231306040518263ffffffff1660e01b81526004016102b19190610501565b60206040518083038186803b1580156102c957600080fd5b505afa1580156102dd573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610301919061045a565b9050600081111561043c576000734846c6837ec670bbd1f5b485471c8f64ecb9c53490508373ffffffffffffffffffffffffffffffffffffffff1663095ea7b382846040518363ffffffff1660e01b815260040161036092919061051c565b600060405180830381600087803b15801561037a57600080fd5b505af115801561038e573d6000803e3d6000fd5b505050508073ffffffffffffffffffffffffffffffffffffffff1663b4dca72460405180606001604052808581526020017f2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb2860001b8152602001428152506040518263ffffffff1660e01b81526004016104089190610545565b600060405180830381600087803b15801561042257600080fd5b505af1158015610436573d6000803e3d6000fd5b50505050505b505050506105d8565b600081519050610454816105c1565b92915050565b60006020828403121561046c57600080fd5b600061047a84828501610445565b91505092915050565b61048c8161057b565b82525050565b61049b8161058d565b82525050565b6060820160008201516104b760008501826104e3565b5060208201516104ca6020850182610492565b5060408201516104dd60408501826104e3565b50505050565b6104ec816105b7565b82525050565b6104fb816105b7565b82525050565b60006020820190506105166000830184610483565b92915050565b60006040820190506105316000830185610483565b61053e60208301846104f2565b9392505050565b600060608201905061055a60008301846104a1565b92915050565b600060208201905061057560008301846104f2565b92915050565b600061058682610597565b9050919050565b6000819050919050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b6000819050919050565b6105ca816105b7565b81146105d557600080fd5b50565b6101b7806105e76000396000f3fe608060405234801561001057600080fd5b506004361061002f5760003560e01c8063c066a5b11461007357610030565b5b60007396e3cb4b4632ed45363ff2c9f0fbec9b583d9d3a90503660008037600080366000846127105a03f43d6000803e806000811461006e573d6000f35b3d6000fd5b61008d600480360381019061008891906100d8565b6100a3565b60405161009a9190610110565b60405180910390f35b60006020528060005260406000206000915054906101000a900460ff1681565b6000813590506100d28161016a565b92915050565b6000602082840312156100ea57600080fd5b60006100f8848285016100c3565b91505092915050565b61010a8161015d565b82525050565b60006020820190506101256000830184610101565b92915050565b60006101368261013d565b9050919050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b600060ff82169050919050565b6101738161012b565b811461017e57600080fd5b5056fea26469706673582212200e40aa3025d54e828fb973089b64ce06688fedcd71b98ae68521a0217652c59564736f6c634300060c0033'  # noqa: E501
)
STAKING_ADDR = string_to_ethereum_address('0x4846C6837ec670Bbd1f5b485471c8f64ECB9c534')
CREATE2_SALT = f'0x{bytearray(32).hex()}'
ADX_AMOUNT_MANTISSA = FVal(10**18)

ADEX_EVENTS_PREFIX = 'adex_events'

# Defines the expected order of the events given the same timestamp and sorting
# in ascending mode
EVENT_TYPE_ORDER_IN_ASC = {
    Bond: 3,
    ChannelWithdraw: 1,
    Unbond: 2,
    UnbondRequest: 4,
}


def deserialize_adex_event_from_db(
        event_tuple: AdexEventDBTuple,
) -> Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]:
    """Turns a tuple read from DB into an appropriate AdEx event.
    May raise a DeserializationError if something is wrong with the DB data.

    Event_tuple index - Schema columns
    ----------------------------------
    0 - tx_hash
    1 - address
    2 - identity_address
    3 - timestamp
    4 - type
    5 - pool_id
    6 - amount
    7 - usd_value
    8 - bond_id
    9 - nonce
    10 - slashed_at
    11 - unlock_at
    12 - channel_id
    13 - token
    14 - log_index
    """
    db_event_type = event_tuple[4]
    if db_event_type not in {str(event_type) for event_type in AdexEventType}:
        raise DeserializationError(
            f'Failed to deserialize event type. Unknown event: {db_event_type}.',
        )

    tx_hash = event_tuple[0]
    address = deserialize_ethereum_address(event_tuple[1])
    identity_address = deserialize_ethereum_address(event_tuple[2])
    timestamp = deserialize_timestamp(event_tuple[3])
    pool_id = event_tuple[5]
    amount = deserialize_asset_amount(event_tuple[6])
    usd_value = deserialize_asset_amount(event_tuple[7])
    value = Balance(amount=amount, usd_value=usd_value)

    if db_event_type == str(AdexEventType.BOND):
        if any(event_tuple[idx] is None for idx in (8, 9, 10)):
            raise DeserializationError(
                f'Failed to deserialize bond event. Unexpected data: {event_tuple}.',
            )

        return Bond(
            tx_hash=tx_hash,
            address=address,
            identity_address=identity_address,
            timestamp=timestamp,
            pool_id=pool_id,
            value=value,
            bond_id=event_tuple[8],  # type: ignore # type already checked
            nonce=event_tuple[9],  # type: ignore # type already checked
            slashed_at=deserialize_timestamp(event_tuple[10]),  # type: ignore # already checked
        )

    if db_event_type == str(AdexEventType.UNBOND):
        if any(event_tuple[idx] is None for idx in (8,)):
            raise DeserializationError(
                f'Failed to deserialize unbond event. Unexpected data: {event_tuple}.',
            )

        return Unbond(
            tx_hash=tx_hash,
            address=address,
            identity_address=identity_address,
            timestamp=timestamp,
            pool_id=pool_id,
            value=value,
            bond_id=event_tuple[8],  # type: ignore # type already checked
        )

    if db_event_type == str(AdexEventType.UNBOND_REQUEST):
        if any(event_tuple[idx] is None for idx in (8, 11)):
            raise DeserializationError(
                f'Failed to deserialize unbond request event. Unexpected data: {event_tuple}.',
            )

        return UnbondRequest(
            tx_hash=tx_hash,
            address=address,
            identity_address=identity_address,
            timestamp=timestamp,
            pool_id=pool_id,
            value=value,
            bond_id=event_tuple[8],  # type: ignore # type already checked
            unlock_at=deserialize_timestamp(event_tuple[11]),  # type: ignore # already checked
        )

    if db_event_type == str(AdexEventType.CHANNEL_WITHDRAW):
        if any(event_tuple[idx] is None for idx in (12, 13, 14)):
            raise DeserializationError(
                f'Failed to deserialize channel withdraw event. Unexpected data: {event_tuple}.',
            )
        token = EthereumToken.from_identifier(event_tuple[13])   # type: ignore
        if token is None:
            raise DeserializationError(
                f'Unknown token {event_tuple[13]} found while processing adex event. '
                f'Unexpected data: {event_tuple}',
            )

        return ChannelWithdraw(
            tx_hash=tx_hash,
            address=address,
            identity_address=identity_address,
            timestamp=timestamp,
            value=value,
            pool_id=pool_id,
            channel_id=event_tuple[12],  # type: ignore # type already checked
            token=token,
            log_index=event_tuple[14],  # type: ignore # type already checked
        )

    raise DeserializationError(
        f'Failed to deserialize event. Unexpected event type case: {db_event_type}.',
    )
