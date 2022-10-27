import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChainID, EvmTokenKind, Location, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])  # noqa: E501
def test_mint_ens_name(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from
    https://etherscan.io/tx/0x74e72600c6cd5a1f0170a3ca38ecbf7d59edeb8ceb48adab2ed9b85d12cc2b99
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0x74e72600c6cd5a1f0170a3ca38ecbf7d59edeb8ceb48adab2ed9b85d12cc2b99')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        tx_hash=tx_hash,
    )
    expires_timestamp = 2142055301
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1637144069000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.023654025517055036')),
            location_label=ADDY,
            notes='Burned 0.023654025517055036 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=2,
            timestamp=1637144069000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.021279711243535527')),
            location_label=ADDY,
            notes=f'Register ENS name hania.eth for 0.019345192039577752 ETH until {decoder.decoders["Ens"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_ENS,
        )]
    assert expected_events == events[0:2]
    erc721_asset = get_or_create_evm_token(  # TODO: Better way to test than this for ERC721 ...?
        userdb=database,
        evm_address='0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85',
        chain=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC721,
        ethereum_manager=ethereum_manager,
    )
    assert events[2] == HistoryBaseEntry(
        event_identifier=tx_hash,
        sequence_index=47,
        timestamp=1637144069000,
        location=Location.BLOCKCHAIN,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=erc721_asset,
        balance=Balance(amount=ONE),
        location_label=ADDY,
        notes='Receive ENS name ERC721 token for hania.eth with id 88045077199635585930173998576189366882372899073811035545363728149974713265418',  # noqa: E501
        counterparty=CPT_ENS,
        extra_data={
            'token_id': 88045077199635585930173998576189366882372899073811035545363728149974713265418,  # noqa: E501
            'token_name': 'ERC721 token',
        },
    )
