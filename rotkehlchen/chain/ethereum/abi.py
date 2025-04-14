import json
import logging
from typing import TYPE_CHECKING

from eth_typing import ABIEvent
from eth_utils import event_abi_to_log_topic, get_abi_input_names
from web3 import Web3
from web3._utils.abi import (
    exclude_indexed_event_inputs,
    get_indexed_event_inputs,
    map_abi_data,
    normalize_event_input_types,
)
from web3._utils.events import get_event_abi_types_for_decoding
from web3._utils.normalizers import BASE_RETURN_NORMALIZERS

from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

WEB3 = Web3()


def decode_event_data_abi_str(
        tx_log: 'EvmTxReceiptLog',
        abi_json: str,
) -> tuple[list, list]:
    """This is an adjustment of web3's event data decoding to work with our code
    source: https://github.com/ethereum/web3.py/blob/8f853f5841fd62187bce0c9f17be75627104ca43/web3/_utils/events.py#L214

    Returns a tuple containing the decoded topic data and decoded log data.

    May raise:
    - DeserializationError if the abi string is invalid or abi or log topics/data do not match
    """
    try:
        event_abi = json.loads(abi_json)
    except json.decoder.JSONDecodeError as e:
        raise DeserializationError('Failed to read the given event abi into json') from e
    return decode_event_data_abi(tx_log, event_abi)


def decode_event_data_abi(
        tx_log: 'EvmTxReceiptLog',
        event_abi: ABIEvent,
) -> tuple[list, list]:
    """This is an adjustment of web3's event data decoding to work with our code
    source: https://github.com/ethereum/web3.py/blob/8f853f5841fd62187bce0c9f17be75627104ca43/web3/_utils/events.py#L214

    Returns a tuple containing the decoded topic data and decoded log data.

    May raise:
    - DeserializationError if the abi string is invalid or abi or log topics/data do not match
    """
    if event_abi.get('anonymous', False):
        topics = tx_log.topics
    elif len(tx_log.topics) == 0:
        raise DeserializationError('Expected non-anonymous event to have 1 or more topics')
    elif event_abi_to_log_topic(event_abi) != tx_log.topics[0]:
        raise DeserializationError('The event signature did not match the provided ABI')
    else:
        topics = tx_log.topics[1:]

    log_topics_abi = get_indexed_event_inputs(event_abi)
    if len(log_topics_abi) != 0:
        log_topic_normalized_inputs = normalize_event_input_types(log_topics_abi)
        log_topic_types = get_event_abi_types_for_decoding(log_topic_normalized_inputs)
        log_topic_names = get_abi_input_names(log_topics_abi[0])  # type: ignore  # getting indexed component is right

        if len(topics) != len(log_topic_types):
            raise DeserializationError(
                f'Expected {len(log_topic_types)} log topics.  Got {len(topics)}',
            )
    else:
        log_topic_names, log_topic_types = [], ()

    log_data_abi = exclude_indexed_event_inputs(event_abi)
    if len(log_data_abi) != 0:
        log_data_normalized_inputs = normalize_event_input_types(log_data_abi)
        log_data_types = get_event_abi_types_for_decoding(log_data_normalized_inputs)
        log_data_names = get_abi_input_names(log_data_abi[0])  # type: ignore  # getting indexed component is right
    else:
        log_data_names, log_data_types = [], ()

    # sanity check that there are not name intersections between the topic
    # names and the data argument names.
    if (duplicate_names := set(log_topic_names).intersection(log_data_names)):
        raise DeserializationError(
            f'The following argument names are duplicated '
            f"between event inputs: '{', '.join({name for name in duplicate_names if name is not None})}'",  # noqa: E501
        )

    decoded_log_data = WEB3.codec.decode(log_data_types, tx_log.data)
    normalized_log_data = map_abi_data(
        BASE_RETURN_NORMALIZERS,
        log_data_types,
        decoded_log_data,
    )
    decoded_topic_data = [
        WEB3.codec.decode([topic_type], topic_data)[0]
        for topic_type, topic_data in zip(log_topic_types, topics, strict=False)
    ]
    normalized_topic_data = map_abi_data(
        BASE_RETURN_NORMALIZERS,
        log_topic_types,
        decoded_topic_data,
    )
    return normalized_topic_data, normalized_log_data
