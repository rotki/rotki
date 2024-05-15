from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.modules.airdrops.decoder import ENS_ADDRESS
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.ethereum.modules.ens.decoder import (
    ENS_GOVERNOR,
    ENS_PUBLIC_RESOLVER_2_ADDRESS,
    ENS_REGISTRAR_CONTROLLER_1,
    ENS_REGISTRAR_CONTROLLER_2,
    _save_hash_mappings_get_fullname,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ENS, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    CacheType,
    ChainID,
    EvmTokenKind,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_mint_ens_name(database, ethereum_inquirer, add_subgraph_api_key):  # pylint: disable=unused-argument
    tx_hash = deserialize_evm_tx_hash('0x74e72600c6cd5a1f0170a3ca38ecbf7d59edeb8ceb48adab2ed9b85d12cc2b99')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    expires_timestamp = 2142055301
    timestamp = TimestampMS(1637144069000)
    register_fee_str = '0.019345192039577752'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.023654025517055036')),
            location_label=ADDY,
            notes='Burned 0.023654025517055036 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=43,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=ADDY,
            notes='Set ENS address for hania.eth',
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_1,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=44,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal(register_fee_str)),
            location_label=ADDY,
            notes=f'Register ENS name hania.eth for {register_fee_str} ETH until {decoder.decoders["Ens"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_1,
            extra_data={'name': 'hania.eth', 'expires': expires_timestamp},
        ),
    ]
    assert expected_events == events[0:3]
    erc721_asset = get_or_create_evm_token(  # TODO: Better way to test than this for ERC721 ...?
        userdb=database,
        evm_address=string_to_evm_address('0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC721,
        evm_inquirer=ethereum_inquirer,
    )
    assert events[3] == EvmEvent(
        tx_hash=tx_hash,
        sequence_index=45,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=erc721_asset,
        balance=Balance(amount=ONE),
        location_label=ADDY,
        notes=f'Receive ENS name hania.eth from 0x283Af0B28c62C092C9727F1Ee09c02CA627EB7F5 to {ADDY}',  # noqa: E501
        counterparty=CPT_ENS,
        address=ENS_REGISTRAR_CONTROLLER_1,
        extra_data={
            'token_id': 88045077199635585930173998576189366882372899073811035545363728149974713265418,  # noqa: E501
            'token_name': 'ERC721 token',
        },
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_text_changed_old_name(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument  # noqa: E501
    """
    Test that text changed for an address that is no longer
    pointed to by an ENS name does not break
    """
    tx_hex = deserialize_evm_tx_hash('0xaa59cb2029651d2ed2c0d1ee34b9b88f0b90278fc6da5b51446d4abf24d7f598')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1664548859000)
    gas_str = '0.00655101156241161'
    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    )]
    for seqindex, attribute in [
            (290, 'url'), (291, 'avatar'), (292, 'description'), (293, 'com.discord'),
            (294, 'com.github'), (295, 'com.reddit'), (296, 'com.twitter'), (297, 'org.telegram'),
    ]:
        expected_events.append(EvmEvent(
            tx_hash=evmhash,
            sequence_index=seqindex,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes=f'Set ENS {attribute} attribute for nebolax.eth',
            counterparty=CPT_ENS,
            address=ENS_PUBLIC_RESOLVER_2_ADDRESS,
        ))
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_set_resolver(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument
    tx_hex = deserialize_evm_tx_hash('0xae2cd848ce02c425bc50a8f46f8430eec32234475efb6fcff28315d2791329f6')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1660047719000)
    gas_str = '0.001069480808983134'

    expected_events = [EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_str)),
        location_label=user_address,
        notes=f'Burned {gas_str} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=evmhash,
        sequence_index=271,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        balance=Balance(),
        location_label=user_address,
        notes='Set ENS address for nebolax.eth',
        counterparty=CPT_ENS,
        address=string_to_evm_address('0x084b1c3C81545d370f3634392De611CaaBFf8148'),
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xbc2E9Df6281a8e853121dc52dBc8BCc8bBE3ed0e']])
def test_set_attribute_v2(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument
    """Test that setting ens text attribute using public resolver deployed in March 2023 works"""
    tx_hex = deserialize_evm_tx_hash('0x6b354e4da21cfb06a8eb4cb5b7efd20558ae3be6a7a7c563f318e041fb3bfdd9')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1681296527000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0013186458834505')),
            location_label=user_address,
            notes='Burned 0.0013186458834505 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=192,
            timestamp=TimestampMS(1681296527000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Set ENS url to https://mercury.foundation attribute for alextatarsky.eth',
            counterparty=CPT_ENS,
            address=string_to_evm_address('0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xA3B9E4b2C18eFB1C767542e8eb9419B840881467']])
def test_register_v2(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument
    """Test that registering an ens name using eth registar deployed in March 2023 works"""
    tx_hex = deserialize_evm_tx_hash('0x5150f6e1c76b74fa914e06df9e56577cdeec0faea11f9949ff529daeb16b1c76')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1681220435000)
    expires_timestamp = Timestamp(1712756435)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00670203024617044')),
            location_label=user_address,
            notes='Burned 0.00670203024617044 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002609751671170445')),
            location_label=user_address,
            notes=f'Register ENS name ens2qr.eth for 0.002609751671170445 ETH until {decoder.decoders["Ens"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_2,
            extra_data={'name': 'ens2qr.eth', 'expires': expires_timestamp},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=289,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Set ENS address for ens2qr.eth',
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_2,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xA01f6D0985389a8E106D3158A9441aC21EAC8D8c']])
def test_renewal_with_refund_old_controller(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument  # noqa: E501
    """
    Check that if there was a refund during a renewal, the refund is subtracted from the
    spent amount. Check a refund using the old ENS registrar controller. That contract
    logs the net cost (after refund) of a renewal.
    """
    tx_hex = deserialize_evm_tx_hash('0xd4fd01f50c3c86e7e119311d6830d975cf7d78d6906004d30370ffcbaabdff95')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expires_timestamp = Timestamp(2310615949)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1663628627000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001092736096479008')),
            location_label=user_address,
            notes='Burned 0.001092736096479008 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1663628627000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RENEW,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.054034186623924151')),
            location_label=user_address,
            notes=f'Renew ENS name dfern.eth for 0.054034186623924151 ETH until {decoder.decoders["Ens"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_1,
            extra_data={'name': 'dfern.eth', 'expires': expires_timestamp},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_renewal_with_refund_new_controller(database, ethereum_inquirer, ethereum_accounts):
    """
    Check that if there was a refund during a renewal, the refund is subtracted from the
    spent amount. Check a refund using the new ENS registrar controller. That contract
    logs the brutto cost (msg.value including the refund) of a renewal.
    """
    tx_hex = deserialize_evm_tx_hash('0x0faef1a1a714d5f2f2e5fb344bd186a745180849bae2c92f9d595d8552ef5c96')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    expires_timestamp = Timestamp(1849443293)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=TimestampMS(1688717987000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0022552539')),
            location_label=user_address,
            notes='Burned 0.0022552539 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=TimestampMS(1688717987000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RENEW,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.013465329469696502')),
            location_label=user_address,
            notes=f'Renew ENS name karapetsas.eth for 0.013465329469696502 ETH until {decoder.decoders["Ens"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_2,
            extra_data={'name': 'karapetsas.eth', 'expires': expires_timestamp},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x7277F7849966426d345D8F6B9AFD1d3d89183083']])
def test_content_hash_changed(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument  # noqa: E501
    """Test that transactions changing the content hash of an ENS are properly decoded"""
    tx_hex = deserialize_evm_tx_hash('0x21fa4ef7a4c20f2548cc010ba00974632cca9e55edea4d50b3fb2c00c7f2080b')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1686304523000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001864622767849202')),
            location_label=user_address,
            notes='Burned 0.001864622767849202 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=257,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Change ENS content hash to ipns://12D3KooWFu3TexBDLUusrnFkjh9eh9PL2PY5UuwbQcgesXMRmcyM for kelsos.eth',  # noqa: E501
            counterparty=CPT_ENS,
            address=ENS_PUBLIC_RESOLVER_2_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize(('action', 'ethereum_accounts'), [
    ('Transfer', ['0x4bBa290826C253BD854121346c370a9886d1bC26', '0x34207C538E39F2600FE672bB84A90efF190ae4C7']),  # noqa: E501
    ('Send', ['0x4bBa290826C253BD854121346c370a9886d1bC26']),
    ('Receive', ['0x34207C538E39F2600FE672bB84A90efF190ae4C7']),
])
def test_transfer_ens_name(database, ethereum_inquirer, action, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument  # noqa: E501
    """Test that transfering an ENS name is decoded properly for all 3 cases.

    Owning both addresses in the transfer, only sender or only receiver
    """
    tx_hex = deserialize_evm_tx_hash('0x03f148c39b347c2d9ab87d31d61a7115156220f8641b7bed838ff62542f3eebe')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)

    sequence_index = 433
    if action == 'Transfer':
        from_address = ethereum_accounts[0]
        to_address = ethereum_accounts[1]
        event_type = HistoryEventType.TRANSFER
        notes = f'Transfer ENS name nebolax.eth to {to_address}'
    elif action == 'Send':
        from_address = ethereum_accounts[0]
        to_address = '0x34207C538E39F2600FE672bB84A90efF190ae4C7'
        event_type = HistoryEventType.SPEND
        notes = f'Send ENS name nebolax.eth to {to_address}'
    else:  # Receive
        sequence_index = 432
        from_address = '0x4bBa290826C253BD854121346c370a9886d1bC26'
        to_address = '0x34207C538E39F2600FE672bB84A90efF190ae4C7'
        event_type = HistoryEventType.RECEIVE
        notes = f'Receive ENS name nebolax.eth from {from_address} to {to_address}'
        # For the event's location_label and address, when receiving swap them
        from_address = '0x34207C538E39F2600FE672bB84A90efF190ae4C7'
        to_address = '0x4bBa290826C253BD854121346c370a9886d1bC26'

    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1687771811000)
    gas_event = EvmEvent(
        tx_hash=evmhash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal('0.000742571017054667')),
        location_label=from_address,
        notes='Burned 0.000742571017054667 ETH for gas',
        counterparty=CPT_GAS,
        address=None,
    )
    expected_events = []
    if action != 'Receive':
        expected_events.append(gas_event)
    expected_events.append(EvmEvent(
        tx_hash=evmhash,
        sequence_index=sequence_index,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=event_type,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:1/erc721:0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85'),
        balance=Balance(amount=FVal(1)),
        location_label=from_address,
        notes=notes,
        counterparty=CPT_ENS,
        address=to_address,
        extra_data={
            'token_id': 73552724610198397480670284492690114609730214421511097849210414928326607694469,  # noqa: E501
            'token_name': 'ERC721 token',
        },
    ))
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x5f0eb172CaA67d45865AAd955FA77654Da33196F']])
def test_for_truncated_labelhash(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument  # noqa: E501
    """Test for https://github.com/rotki/rotki/issues/6597 where some labelhashes
    had their leading 0s truncated and lead to graph failures
    """
    tx_hex = deserialize_evm_tx_hash('0x8a809c2286342e04ce74494808c1dee5efd7aeb0af57b600780cb04eb3f83441')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1603662139000)
    gas_str = '0.003424155'
    register_fee_str = '0.122618417748598345'
    expires_timestamp = Timestamp(1919231659)
    erc721_asset = get_or_create_evm_token(  # TODO: Better way to test than this for ERC721 ...?
        userdb=database,
        evm_address=string_to_evm_address('0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC721,
        evm_inquirer=ethereum_inquirer,
    )
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=203,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Set ENS address for cantillon.eth',
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_1,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=204,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(amount=FVal(register_fee_str)),
            location_label=user_address,
            notes=f'Register ENS name cantillon.eth for {register_fee_str} ETH until {decoder.decoders["Ens"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_1,
            extra_data={'name': 'cantillon.eth', 'expires': expires_timestamp},
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=205,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=erc721_asset,
            balance=Balance(amount=FVal(1)),
            location_label=user_address,
            notes=f'Receive ENS name cantillon.eth from {ENS_REGISTRAR_CONTROLLER_1} to {user_address}',  # noqa: E501
            counterparty=CPT_ENS,
            address=ENS_REGISTRAR_CONTROLLER_1,
            extra_data={
                'token_id': 520289412805995815014030902380736904960994587318475958708983757899533811755,  # noqa: E501
                'token_name': 'ERC721 token',
            },
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_vote_cast(database, ethereum_inquirer, ethereum_accounts):
    """Test voting for ENS governance"""
    tx_hex = deserialize_evm_tx_hash('0x4677ffa104b011d591ae0c056ba651a978db982c0dfd131520db74c1b46ff564')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1695935903000)
    gas_str = '0.000916189648966683'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=365,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Voted FOR ens governance proposal https://www.tally.xyz/gov/ens/proposal/10686228418271748393758532071249002330319730525037728746406757788787068261444',
            counterparty=CPT_ENS,
            address=ENS_GOVERNOR,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_set_attribute_for_non_primary_name(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument  # noqa: E501
    """Test that setting ens text attribute for a name that is controlle by but not
    set as the primary name of the address works correctly"""
    tx_hex = deserialize_evm_tx_hash('0x07aa7d1ac61fc03f6416a25c0d6cf96f286e2ce84e9b350dd2a9a1bd6426aef2')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    gas_str = '0.00054662131669239'
    timestamp = TimestampMS(1694558075000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=344,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Set ENS avatar attribute for hania.eth',
            counterparty=CPT_ENS,
            address=ENS_PUBLIC_RESOLVER_2_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xF5d90Ac6747CB3352F05BF61f48b991ACeaE28eB']])
def test_claim_airdrop(database, ethereum_inquirer, ethereum_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument
    tx_hex = deserialize_evm_tx_hash('0xb892797f63943dbf75e9e8a86515e9a4a964dcb6930dad10e93b526a2a648e6d')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    gas_str, claimed_amount = '0.014281582073130576', '88.217476134335168512'
    timestamp = TimestampMS(1637313773000)
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=161,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_ENS,
            balance=Balance(amount=FVal(claimed_amount)),
            location_label=user_address,
            notes=f'Claim {claimed_amount} ENS from ens airdrop',
            counterparty=CPT_ENS,
            address=ENS_ADDRESS,
        ),
    ]
    assert events == expected_events


def test_invalid_ens_name(globaldb: 'GlobalDBHandler'):
    """
    Test that possible exceptions when processing invalid ENS names are handled correctly and
    nothing gets stored in the database cache for invalid names.
    """
    name = 'ʀ'
    full_name = _save_hash_mappings_get_fullname(name=name, tx_hash=make_evm_tx_hash())
    assert full_name == f'{name}.eth'
    with globaldb.conn.read_ctx() as cursor:
        for cache_key in (CacheType.ENS_NAMEHASH, CacheType.ENS_LABELHASH):
            assert cursor.execute(
                f'SELECT COUNT(*) FROM unique_cache WHERE key LIKE "{cache_key.serialize()}%"',
            ).fetchone()[0] == 0
