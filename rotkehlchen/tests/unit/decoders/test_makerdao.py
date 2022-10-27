import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash
from rotkehlchen.utils.hexbytes import HexBytes


@pytest.mark.parametrize('ethereum_accounts', [['0x648aA14e4424e0825A5cE739C8C68610e143FB79']])  # noqa: E501
def test_makerdao_simple_transaction(
        database,
        ethereum_manager,
        function_scope_messages_aggregator,
):
    """Data taken from
    https://etherscan.io/tx/0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e
    """
    tx_hash = deserialize_evm_tx_hash('0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e')  # noqa: E501
    # We don't need any events here, we just check that no errors occure during decoding
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    assert events == [
        HistoryBaseEntry(
            event_identifier=HexBytes('0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e'),  # noqa: E501
            sequence_index=0,
            timestamp=1593572988000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.00926134), usd_value=ZERO),
            location_label='0x648aA14e4424e0825A5cE739C8C68610e143FB79',
            notes='Burned 0.00926134 ETH for gas',
            counterparty='gas',
            identifier=None,
            extra_data=None,
        ), HistoryBaseEntry(
            event_identifier=HexBytes('0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e'),  # noqa: E501
            sequence_index=1,
            timestamp=1593572988000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.6), usd_value=ZERO),
            location_label='0x648aA14e4424e0825A5cE739C8C68610e143FB79',
            notes='Withdraw 0.6 ETH from ETH-A MakerDAO vault',
            counterparty='makerdao vault',
            identifier=None,
            extra_data={'vault_type': 'ETH-A'},
        ), HistoryBaseEntry(
            event_identifier=HexBytes('0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e'),  # noqa: E501
            sequence_index=105,
            timestamp=1593572988000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_DAI,
            balance=Balance(amount=ZERO, usd_value=ZERO),
            location_label='0x648aA14e4424e0825A5cE739C8C68610e143FB79',
            notes='Payback 0 DAI of debt to makerdao vault 9842',
            counterparty='makerdao vault',
            identifier=None,
            extra_data={
                'vault_address': '0xdE3b5816b51d88C59C341A0EAbB486F5566542c0',
                'cdp_id': 9842,
            },
        ),
    ]
