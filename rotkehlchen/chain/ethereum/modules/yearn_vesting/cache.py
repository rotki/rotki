import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.globaldb.cache import (
    globaldb_delete_general_cache_values,
    globaldb_get_general_cache_values,
    globaldb_set_general_cache_values,
    globaldb_update_cache_last_ts,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import FACTORY_DEPLOYMENTS, FactoryDeployment
from .structures import VestingEscrowData

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _as_bytes(value: bytes | str) -> bytes:
    if isinstance(value, str):
        return bytes.fromhex(value.removeprefix('0x'))
    return bytes(value)


def _word(data: bytes, index: int) -> bytes:
    return data[index * 32:(index + 1) * 32]


def parse_creation_log(
        deployment: FactoryDeployment,
        topics: Sequence[bytes | str],
        data: bytes | str,
) -> VestingEscrowData:
    """Parse one creation log from any supported Yearn vesting factory."""
    decoded_topics = [_as_bytes(topic) for topic in topics]
    decoded_data = _as_bytes(data)
    expected_data_words = (
        7 if deployment.kind == 'token' else 10
    ) if deployment.version == 'v0.4.0' else (
        5 if deployment.version in {'v0.1.0', 'v0.2.0'} else 6
    )
    if len(decoded_topics) != 4 or len(decoded_data) < expected_data_words * 32:
        raise ValueError(
            f'Malformed {deployment.version} {deployment.kind} vesting creation log',
        )

    revoker: ChecksumEvmAddress | None
    yield_recipient: ChecksumEvmAddress | None
    asset_token: ChecksumEvmAddress | None
    if deployment.version == 'v0.4.0':
        escrow = bytes_to_address(decoded_topics[1])
        token = bytes_to_address(decoded_topics[2])
        recipient = bytes_to_address(decoded_topics[3])
        funder = bytes_to_address(_word(decoded_data, 0))
        revoker = bytes_to_address(_word(decoded_data, 1))
        if deployment.kind == 'token':
            amount = funded_amount = int.from_bytes(_word(decoded_data, 2))
            start_time = int.from_bytes(_word(decoded_data, 3))
            duration = int.from_bytes(_word(decoded_data, 4))
            cliff_length = int.from_bytes(_word(decoded_data, 5))
            yield_recipient = asset_token = None
        else:
            yield_recipient = bytes_to_address(_word(decoded_data, 2))
            asset_token = bytes_to_address(_word(decoded_data, 3))
            funded_amount = int.from_bytes(_word(decoded_data, 4))
            amount = int.from_bytes(_word(decoded_data, 5))
            start_time = int.from_bytes(_word(decoded_data, 6))
            duration = int.from_bytes(_word(decoded_data, 7))
            cliff_length = int.from_bytes(_word(decoded_data, 8))
    else:
        funder = bytes_to_address(decoded_topics[1])
        token = bytes_to_address(decoded_topics[2])
        recipient = bytes_to_address(decoded_topics[3])
        escrow = bytes_to_address(_word(decoded_data, 0))
        amount = funded_amount = int.from_bytes(_word(decoded_data, 1))
        start_time = int.from_bytes(_word(decoded_data, 2))
        duration = int.from_bytes(_word(decoded_data, 3))
        cliff_length = int.from_bytes(_word(decoded_data, 4))
        revoker = yield_recipient = asset_token = None

    return VestingEscrowData(
        escrow=escrow,
        factory=deployment.address,
        version=deployment.version,
        kind=deployment.kind,
        token=token,
        recipient=recipient,
        funder=funder,
        revoker=revoker,
        yield_recipient=yield_recipient,
        asset_token=asset_token,
        amount=amount,
        funded_amount=funded_amount,
        start_time=start_time,
        end_time=start_time + duration,
        cliff_length=cliff_length,
    )


def read_yearn_vesting_data_from_cache() -> dict[ChecksumEvmAddress, VestingEscrowData]:
    with GlobalDBHandler().conn.read_ctx() as cursor:
        values = globaldb_get_general_cache_values(
            cursor=cursor,
            key_parts=(CacheType.YEARN_VESTING_ESCROWS,),
        )

    return {
        position.escrow: position
        for value in values
        if (position := VestingEscrowData.deserialize(value))
    }


def query_yearn_vesting_data(
        inquirer: EthereumInquirer,
        cache_type: Literal[CacheType.YEARN_VESTING_ESCROWS],
        msg_aggregator: MessagesAggregator,  # pylint: disable=unused-argument
        reload_all: bool,
) -> list[VestingEscrowData] | None:
    """Query and cache every escrow emitted by the supported immutable factories."""
    existing = {} if reload_all else read_yearn_vesting_data_from_cache()
    positions: dict[ChecksumEvmAddress, VestingEscrowData] = {}
    for deployment in FACTORY_DEPLOYMENTS:
        for event in inquirer.get_logs(
            contract_address=deployment.address,
            abi=deployment.abi,
            event_name=deployment.event_name,
            argument_filters={},
            from_block=deployment.deployed_block,
        ):
            try:
                position = parse_creation_log(
                    deployment=deployment,
                    topics=event['topics'],
                    data=event['data'],
                )
            except (IndexError, KeyError, ValueError) as e:
                log.error(
                    'Failed to parse %s Yearn vesting creation log due to %s',
                    deployment.version,
                    e,
                )
                continue

            positions[position.escrow] = position

    new_positions = [
        position for address, position in positions.items()
        if address not in existing
    ]
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        if reload_all:
            globaldb_delete_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(cache_type,),
            )
            values = [position.serialize() for position in positions.values()]
        else:
            values = [position.serialize() for position in new_positions]

        if len(values) != 0:
            globaldb_set_general_cache_values(
                write_cursor=write_cursor,
                key_parts=(cache_type,),
                values=values,
            )
        globaldb_update_cache_last_ts(
            write_cursor=write_cursor,
            cache_type=cache_type,
            key_parts=None,
        )

    return new_positions or None
