import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.makerdao.constants import CPT_VAULT
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash
from rotkehlchen.utils.hexbytes import HexBytes


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x648aA14e4424e0825A5cE739C8C68610e143FB79']])  # noqa: E501
def test_makerdao_simple_transaction(
        database,
        ethereum_inquirer,
):
    """Data taken from
    https://etherscan.io/tx/0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e
    """
    tx_hash = deserialize_evm_tx_hash('0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e')  # noqa: E501
    # We don't need any events here, we just check that no errors occure during decoding
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            event_identifier=HexBytes('0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e'),  # noqa: E501
            sequence_index=0,
            timestamp=1593572988000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.00926134), usd_value=ZERO),
            location_label='0x648aA14e4424e0825A5cE739C8C68610e143FB79',
            notes='Burned 0.00926134 ETH for gas',
            counterparty=CPT_GAS,
            identifier=None,
            extra_data=None,
        ), EvmEvent(
            event_identifier=HexBytes('0x95de47059bcc084ebb8bdd60f48fbcf05619c2af84bf612fdc27a6bbf9b5097e'),  # noqa: E501
            sequence_index=1,
            timestamp=1593572988000,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_ETH,
            balance=Balance(amount=FVal(0.6), usd_value=ZERO),
            location_label='0x648aA14e4424e0825A5cE739C8C68610e143FB79',
            notes='Withdraw 0.6 ETH from ETH-A MakerDAO vault',
            counterparty=CPT_VAULT,
            address=string_to_evm_address('0x809aade1B623d8cDAeb86484d3366A03F8841FBc'),
            identifier=None,
            extra_data={'vault_type': 'ETH-A'},
        ),
    ]
