import pytest

from rotkehlchen.accounting.structures import (
    Balance,
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.chain.ethereum.decoding.oneinch.v1.decoder import CPT_ONEINCH_V1
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_CHI, ZERO_ADDRESS
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])  # noqa: E501
def test_1inchv1_swap(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from
    https://etherscan.io/tx/0x8b8652c502e80ce7c5441cdedc9184ea8f07a9c13b4c3446a47ae08c6c1d6efa
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x8b8652c502e80ce7c5441cdedc9184ea8f07a9c13b4c3446a47ae08c6c1d6efa')  # noqa: E501
    events = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    chispender_addy = '0xed04A060050cc289d91779A8BB3942C3A6589254'
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash.hex(),  # pylint: disable=no-member
            sequence_index=0,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00896373909'), usd_value=ZERO),
            location_label=ADDY,
            notes=f'Burned 0.00896373909 ETH in gas from {ADDY} for transaction {tx_hash.hex()}',  # pylint: disable=no-member  # noqa: E501
            counterparty='gas',
            identifier=None,
            extras=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash.hex(),  # pylint: disable=no-member
            sequence_index=90,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            balance=Balance(amount=FVal('138.75'), usd_value=ZERO),
            location_label=ADDY,
            notes=f'Swap 138.75 USDC in 1inch-v1 from {ADDY}',
            counterparty=CPT_ONEINCH_V1,
            identifier=None,
            extras=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash.hex(),  # pylint: disable=no-member
            sequence_index=91,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            balance=Balance(amount=FVal('135.959878392183347402'), usd_value=ZERO),
            location_label=ADDY,
            notes=f'Receive 135.959878392183347402 DAI from 1inch-v1 swap in {ADDY}',
            counterparty=CPT_ONEINCH_V1,
            identifier=None,
            extras=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash.hex(),  # pylint: disable=no-member
            sequence_index=102,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_CHI,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=ADDY,
            notes=f'Send 0 CHI from {ADDY} to {ZERO_ADDRESS}',
            counterparty=ZERO_ADDRESS,
            identifier=None,
            extras=None,
        ), HistoryBaseEntry(
            event_identifier=tx_hash.hex(),  # pylint: disable=no-member
            sequence_index=103,
            timestamp=1594500575000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_CHI,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label=ADDY,
            notes=f'Approve 0 CHI of {ADDY} for spending by {chispender_addy}',
            counterparty=chispender_addy,
            identifier=None,
            extras=None,
        ),
    ]
    assert expected_events == events
