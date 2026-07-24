from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.chain.base.modules.basenames.constants import CPT_BASENAMES
from rotkehlchen.chain.ethereum.airdrops import AIRDROPS_REPO_BASE
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.ethereum.modules.gwei_names.constants import CPT_GNS
from rotkehlchen.chain.ethereum.modules.yearn.vesting.constants import CPT_YEARN_VESTING
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import AIRDROPSDIR_NAME, APPDIR_NAME
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.constants.misc import ONE
from rotkehlchen.constants.timing import DAY_IN_SECONDS, WEEK_IN_SECONDS
from rotkehlchen.db.calendar import CalendarEntry, CalendarFilterQuery, DBCalendar, ReminderEntry
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.calendar import (
    AERO_VELO_CALENDAR_COLOR,
    AIRDROP_CALENDAR_COLOR,
    BRIDGE_CALENDAR_COLOR,
    CRV_CALENDAR_COLOR,
    ENS_CALENDAR_COLOR,
    YEARN_VESTING_CALENDAR_COLOR,
    CalendarReminderCreator,
)
from rotkehlchen.tests.unit.test_ethereum_airdrops import prepare_airdrop_mock_response
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import (
    ChainID,
    EVMTxHash,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress


MOCK_MYSO_ZK_AIRDROP_INDEX = {
    'airdrops': {
        'myso': {
            'file_path': 'airdrops/myso.csv.gz',
            'file_hash': 'b06cf1c89f1183bb22049d8625ba06fcabcaac2bbf1a106eaa107b9ddb91ff87',
            'asset_identifier': 'eip155:1/erc20:0x5fDe99e121F3aC02e7d6ACb081dB1f89c1e93C17',
            'url': 'https://app.myso.finance/airdrop',
            'name': 'MYT',
            'icon': 'myso.svg',
            'icon_path': 'airdrops/icons/myso.jpg',
            'cutoff_time': 1717145230,
            'has_decoder': False,
            'new_asset_data': {
                'asset_type': 'EVM_TOKEN',
                'address': '0x5fDe99e121F3aC02e7d6ACb081dB1f89c1e93C17',
                'name': 'MYSO Token',
                'symbol': 'MYT',
                'chain_id': 1,
                'decimals': 18,
            },
        },
        'zk': {
            'file_path': 'airdrops/zk.csv.gz',
            'file_hash': '17c754bf5b051e322d2bb0a5034f4d541a5c2769ca42294d6b5c3632372debb7',
            'asset_identifier': 'eip155:324/erc20:0x5A7d6b2F92C77FAD6CCaBd7EE0624E64907Eaf3E',
            'url': 'https://claim.zknation.io/',
            'name': 'ZK',
            'icon': 'zksync.jpg',
            'cutoff_time': 1735862400,
            'has_decoder': False,
            'new_asset_data': {
                'asset_type': 'EVM_TOKEN',
                'address': '0x5A7d6b2F92C77FAD6CCaBd7EE0624E64907Eaf3E',
                'name': 'ZKsync',
                'symbol': 'ZK',
                'chain_id': 324,
                'decimals': 18,
            },
        },
    },
    'poap_airdrops': {},
}


def get_airdrop_request_mock(user_address: ChecksumEvmAddress) -> Callable:
    """Get airdrop request mocking function for the specified address."""
    def mock_requests_get(url: str, timeout: int = 0, headers: dict | None = None):  # pylint: disable=unused-argument
        """Mock airdrop data retrieval to avoid huge VCRs"""
        return prepare_airdrop_mock_response(
            url=url,
            mock_airdrop_index=MOCK_MYSO_ZK_AIRDROP_INDEX,
            mock_airdrop_data={
                f'{AIRDROPS_REPO_BASE}/airdrops/myso.csv.gz': f'address,tokens\n{user_address},100.0\n',  # noqa: E501
            },
        )

    return mock_requests_get


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2023-06-01 22:31:11 GMT')
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    '0xA3B9E4b2C18eFB1C767542e8eb9419B840881467',
    '0xA01f6D0985389a8E106D3158A9441aC21EAC8D8c',
]])
@pytest.mark.parametrize('base_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('ens_data', [(
    [
        deserialize_evm_tx_hash('0x4fdcd2632c6aa5549f884c9322943690e4f3c08e20a4dffe59e198ee737b54e8'),  # Register  # noqa: E501
        deserialize_evm_tx_hash('0xd4fd01f50c3c86e7e119311d6830d975cf7d78d6906004d30370ffcbaabdff95'),  # Renew old (same ENS)  # noqa: E501
    ],
    {'dfern.eth': 2310615949},
    CPT_ENS,
), (
    [
        deserialize_evm_tx_hash('0x5150f6e1c76b74fa914e06df9e56577cdeec0faea11f9949ff529daeb16b1c76'),  # Register v2  # noqa: E501
        deserialize_evm_tx_hash('0x0faef1a1a714d5f2f2e5fb344bd186a745180849bae2c92f9d595d8552ef5c96'),  # Renew new  # noqa: E501
    ],
    {'ens2qr.eth': 1712756435, 'karapetsas.eth': 1849443293},
    CPT_ENS,
), (
    [deserialize_evm_tx_hash('0x20280b43dbcfa86cdf0703d2e9f8f2ef200839b2ee0e819d895515d3adb74eff')],  # Register  # noqa: E501
    {'yabir.base.eth': 1758296219},
    CPT_BASENAMES,
)])
def test_ens_expiry_calendar_reminders(
        database: DBHandler,
        base_inquirer: BaseInquirer,
        ethereum_inquirer: EthereumInquirer,
        ens_data: tuple[list[EVMTxHash], dict[str, Timestamp], str],
        add_subgraph_api_key,  # pylint: disable=unused-argument
) -> None:
    """Test that ENS reminders are created at the expiry time of ENS registrations and renewals."""
    ens_tx_hashes, latest_expiry_of_ens, counterparty = ens_data
    calendar_db = DBCalendar(database)
    all_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert all_calendar_entries['entries_total'] == 0
    original_requests_get = requests.get

    def mock_basenames_request_get(url, timeout):
        """There is a basenames api request that fails and is excluded from the VCR. So force
        it to fail here to avoid VCR problems.
        """
        if 'basenames/metadata/45236693060355741244193735256859290971350174497390063529678304497551635844272' in url:  # noqa: E501
            raise requests.exceptions.RequestException('BOOM')

        return original_requests_get(url=url, timeout=timeout)

    with patch(
        target='rotkehlchen.chain.base.modules.basenames.decoder.requests.get',
        side_effect=mock_basenames_request_get,
    ):
        ens_events = [
            next(x for x in get_decoded_events_of_transaction(  # decode ENS registration/renewal event and get the event with the metadata  # noqa: E501
                evm_inquirer=ethereum_inquirer if counterparty == CPT_ENS else base_inquirer,
                tx_hash=ens_tx_hash,
            )[0] if x.extra_data is not None) for ens_tx_hash in ens_tx_hashes
        ]

    reminder_creator = CalendarReminderCreator(database=database, current_ts=ts_now())
    reminder_creator.maybe_create_ens_reminders()

    new_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert new_calendar_entries['entries_found'] == len(latest_expiry_of_ens)  # only one calendar entry per ENS  # noqa: E501

    for idx, calendar_entry in enumerate(new_calendar_entries['entries']):
        assert ens_events[idx].extra_data is not None
        assert ens_events[idx].location_label is not None
        ens_name: str = ens_events[idx].extra_data['name']  # type: ignore[index]  # extra_data is not None, checked above
        ens_expires = latest_expiry_of_ens[ens_name]
        assert calendar_entry == CalendarEntry(  # calendar entry is created for expiry
            identifier=idx + 1,
            name=f'{ens_name} expiry',
            timestamp=ens_expires,
            description=f'{ens_name} expires on {reminder_creator.timestamp_to_date(ens_expires)}',
            counterparty=counterparty,
            address=ens_events[idx].location_label,  # type: ignore[arg-type]  # location_label is not None, checked above
            blockchain=ChainID.deserialize(ens_events[idx].location.to_chain_id()).to_blockchain(),
            color=ENS_CALENDAR_COLOR,
            auto_delete=True,
        )

        # reminders are created 1 week and 1 day before the expiry calendar entry
        reminders = calendar_db.query_reminder_entry(event_id=calendar_entry.identifier)['entries']
        assert len(reminders) == 2
        assert reminders[0].event_id == reminders[1].event_id == calendar_entry.identifier
        assert reminders[0].secs_before == DAY_IN_SECONDS
        assert reminders[1].secs_before == WEEK_IN_SECONDS


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2026-07-04 18:00:00 GMT')  # keep current_ts before the name expiries
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',  # registered lefteris.gwei
    '0x9398084E888CB5B5c126240439054b57C10138E7',  # renewed aiiiden.gwei
]])
def test_gns_expiry_calendar_reminders(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that reminders are created at the expiry time of gwei name
    registrations and renewals."""
    calendar_db = DBCalendar(database)
    assert calendar_db.query_calendar_entry(CalendarFilterQuery.make())['entries_total'] == 0
    for tx_hash in (
        deserialize_evm_tx_hash('0x8dbce5bb53b5a058ae38504202e025ddad273d24336014af2e10d9ed226e1b3b'),  # register lefteris.gwei  # noqa: E501
        deserialize_evm_tx_hash('0x36d7e292fe72905d240399cd90728a2fae916fc11d29a8fdddfef78d3d4f5a9f'),  # renew aiiiden.gwei  # noqa: E501
    ):
        get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)

    reminder_creator = CalendarReminderCreator(database=database, current_ts=ts_now())
    reminder_creator.maybe_create_ens_reminders()

    entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())['entries']
    expected = {
        'lefteris.gwei': (Timestamp(1814717843), ethereum_accounts[0]),
        'aiiiden.gwei': (Timestamp(1846009919), ethereum_accounts[1]),
    }
    assert len(entries) == len(expected)
    for calendar_entry in entries:
        expires, user_address = expected[gwei_name := calendar_entry.name.removesuffix(' expiry')]
        assert calendar_entry == CalendarEntry(
            identifier=calendar_entry.identifier,
            name=f'{gwei_name} expiry',
            timestamp=expires,
            description=f'{gwei_name} expires on {reminder_creator.timestamp_to_date(expires)}',
            counterparty=CPT_GNS,
            address=user_address,
            blockchain=SupportedBlockchain.ETHEREUM,
            color=ENS_CALENDAR_COLOR,
            auto_delete=True,
        )

        # reminders are created 1 week and 1 day before the expiry calendar entry
        reminders = calendar_db.query_reminder_entry(event_id=calendar_entry.identifier)['entries']
        assert len(reminders) == 2
        assert reminders[0].event_id == reminders[1].event_id == calendar_entry.identifier
        assert reminders[0].secs_before == DAY_IN_SECONDS
        assert reminders[1].secs_before == WEEK_IN_SECONDS


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2024-01-01 00:00:00 GMT')
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x510B0068C0756bBEFCBaffB6567e467d661291FE',
    '0x8093c1958Ea5CEBF1eFeAABAB7498A49f2937Fed',
]])
@pytest.mark.parametrize('crv_tx_hashes', [[
    deserialize_evm_tx_hash('0x2675807cf1950b8a8fbd64e1a0fe0ec3b894ba88fbb8e544ddf279aff12c6d55'),
    deserialize_evm_tx_hash('0x15bdc063daef0b1d8d61e9d3f4af5abf50d1ec28421cfc6be1b91b8acbd037e7'),
]])
def test_locked_crv_calendar_reminders(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        crv_tx_hashes: list[EVMTxHash],
) -> None:
    """Test that reminders are created at lock period end of CRV in vote escrow."""
    calendar_db = DBCalendar(database)
    all_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert all_calendar_entries['entries_total'] == 0

    crv_events = [
        next(x for x in get_decoded_events_of_transaction(
            evm_inquirer=ethereum_inquirer,
            tx_hash=crv_tx_hash,
        )[0] if x.extra_data is not None) for crv_tx_hash in crv_tx_hashes
    ]

    reminder_creator = CalendarReminderCreator(database=database, current_ts=ts_now())
    reminder_creator.maybe_create_locked_crv_reminders()

    new_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert new_calendar_entries['entries_found'] == len(crv_tx_hashes)

    for idx, calendar_entry in enumerate(new_calendar_entries['entries']):
        assert crv_events[idx].extra_data is not None
        assert crv_events[idx].location_label is not None
        locktime = Timestamp(crv_events[idx].extra_data['locktime'])  # type: ignore[index]  # extra_data is not None, checked above

        assert calendar_entry == CalendarEntry(  # calendar entry is created for expiry
            identifier=idx + 1,
            name='CRV vote escrow lock period ends',
            timestamp=locktime,
            description=f'Lock period for {crv_events[idx].amount} CRV in vote escrow ends on {reminder_creator.timestamp_to_date(locktime)}',  # noqa: E501
            counterparty=CPT_CURVE,
            address=crv_events[idx].location_label,  # type: ignore[arg-type]  # location_label is not None, checked above
            blockchain=ChainID.deserialize(crv_events[idx].location.to_chain_id()).to_blockchain(),
            color=CRV_CALENDAR_COLOR,
            auto_delete=True,
        )

        # one reminder is created at the time of the calendar entry
        reminders = calendar_db.query_reminder_entry(event_id=calendar_entry.identifier)['entries']
        assert len(reminders) == 1
        assert reminders[0].event_id == calendar_entry.identifier
        assert reminders[0].secs_before == 0


@pytest.mark.freeze_time('2024-01-01 00:00:00 GMT')
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x510B0068C0756bBEFCBaffB6567e467d661291FE',
]])
def test_airdrop_claim_calendar_reminders(
        database: DBHandler,
        data_dir: Path,
        ethereum_accounts: list[ChecksumEvmAddress],
        ethereum_inquirer: EthereumInquirer,
) -> None:
    """Test that reminders are created for airdrop claim deadlines.
    The zksync era airdrop should be skipped currently since it is not in SupportedBlockchain
    """
    calendar_db = DBCalendar(database)
    user_address = ethereum_accounts[0]
    all_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert all_calendar_entries['entries_total'] == 0
    myso_airdrop_file = data_dir / APPDIR_NAME / AIRDROPSDIR_NAME / 'myso.csv.gz'
    myso_airdrop_file.unlink(missing_ok=True)
    assert myso_airdrop_file.exists() is False
    reminder_creator = CalendarReminderCreator(database=database, current_ts=ts_now())

    with (
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=get_airdrop_request_mock(user_address)),  # noqa: E501
        patch('rotkehlchen.chain.ethereum.airdrops.check_linea_airdrop', side_effect=lambda addresses, database, found_data: found_data),  # noqa: E501
    ):
        reminder_creator.maybe_create_airdrop_claim_reminder()

    assert (database.user_data_dir / APPDIR_NAME / AIRDROPSDIR_NAME).exists() is False  # regression check for an issue creating the airdrops folder in the wrong directory.  # noqa: E501
    assert myso_airdrop_file.exists() is True
    new_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert new_calendar_entries['entries_found'] == 1

    myso_cutoff = Timestamp(1717145230)
    assert new_calendar_entries['entries'] == [
        CalendarEntry(
            name='Myso airdrop claim deadline',
            timestamp=myso_cutoff,
            description=f'Myso airdrop of 100.0 MYT has claim deadline on {reminder_creator.timestamp_to_date(myso_cutoff)}',  # noqa: E501
            counterparty='myso',
            address=user_address,
            blockchain=SupportedBlockchain.ETHEREUM,
            color=AIRDROP_CALENDAR_COLOR,
            auto_delete=True,
            identifier=1,
        ),
    ]

    # reminders are created 1 week and 1 day before the expiry calendar entry
    calendar_entry = new_calendar_entries['entries'][0]
    reminders = calendar_db.query_reminder_entry(event_id=calendar_entry.identifier)['entries']
    assert len(reminders) == 2
    assert reminders[0].event_id == reminders[1].event_id == calendar_entry.identifier
    assert reminders[0].secs_before == DAY_IN_SECONDS
    assert reminders[1].secs_before == WEEK_IN_SECONDS


@pytest.mark.freeze_time('2024-01-01 00:00:00 GMT')
@pytest.mark.parametrize('arbitrum_one_accounts', [[
    '0x510B0068C0756bBEFCBaffB6567e467d661291FE',
]])
def test_airdrop_claim_calendar_reminders_wrong_chain(
        database: DBHandler,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that no calendar entries are created if the airdrop is for a chain
    that the given address is not configured to track.
    """
    reminder_creator = CalendarReminderCreator(database=database, current_ts=ts_now())

    with (
        patch('rotkehlchen.chain.ethereum.airdrops.requests.get', side_effect=get_airdrop_request_mock(arbitrum_one_accounts[0])),  # noqa: E501
        patch('rotkehlchen.chain.ethereum.airdrops._query_linea_airdrop_contract', return_value=None),  # noqa: E501
    ):
        reminder_creator.maybe_create_airdrop_claim_reminder()

    new_calendar_entries = DBCalendar(database).query_calendar_entry(CalendarFilterQuery.make())
    assert new_calendar_entries['entries_found'] == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.freeze_time('2023-06-30 15:45:00 GMT')
@pytest.mark.parametrize('arbitrum_one_accounts', [[
    '0x5EA45c8E36704d7F4053Bb0e23cDd96E4d8b80F7',
]])
@pytest.mark.parametrize('optimism_accounts', [[
    '0xE232E72983E329757F02292322296f5B96dAfC8F',
]])
@pytest.mark.parametrize('base_accounts', [[
    '0x6730b1Df17E50217777EeE475E34815964e3BFb2',
]])
def test_l2_bridge_claim_reminders(arbitrum_one_accounts, arbitrum_one_inquirer, optimism_accounts, optimism_inquirer, base_accounts, base_inquirer, database):  # noqa: E501
    parameters = [
        (optimism_accounts, optimism_inquirer, '0xe2111cddcd42c8214770c7a3270490c31663cd8b4b20b3fc27018ca3ce7a3979', '2023-01-09 08:34:00 GMT'),  # noqa: E501
        (arbitrum_one_accounts, arbitrum_one_inquirer, '0xdb8e29f27a7b7b416f168e8135347703268a142b6776503e26419dbfc43bcabf', '2023-06-30 15:45:00 GMT'),  # noqa: E501
        (base_accounts, base_inquirer, '0xe451ca095dd9d48f6558a226fc6cc9b28d19f39080545db63b8ba9410fe3df3e', '2024-10-18 07:24:00 GMT'),  # noqa: E501
    ]
    expected_entries = 0
    for idx, (accounts, inquirer, tx_hash, time_to_freeze) in enumerate(parameters):
        with freeze_time(time_to_freeze):
            events, _ = get_decoded_events_of_transaction(
                tx_hash=deserialize_evm_tx_hash(tx_hash),
                evm_inquirer=inquirer,
            )

            calendar_db = DBCalendar(database)
            all_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
            assert all_calendar_entries['entries_total'] == expected_entries

            CalendarReminderCreator(
                database=database,
                current_ts=ts_now(),
            ).maybe_create_l2_bridging_reminder()
            expected_entries += 1

            new_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
            assert new_calendar_entries['entries_found'] == expected_entries

            calendar_entry = new_calendar_entries['entries'][-1]
            bridge_event = events[-1]
            asset_symbol = bridge_event.asset.resolve_to_asset_with_symbol().symbol
            assert calendar_entry == CalendarEntry(
                identifier=idx + 1,
                name=f'Claim {bridge_event.amount} {asset_symbol} bridge deposit on Ethereum',
                timestamp=ts_ms_to_sec(TimestampMS(bridge_event.timestamp + WEEK_IN_SECONDS * 1000)),  # noqa: E501
                description=f'Bridge deposit of {bridge_event.amount} {asset_symbol} is ready to claim on Ethereum',  # noqa: E501
                counterparty=bridge_event.counterparty,
                auto_delete=True,
                blockchain=inquirer.chain_id.to_blockchain(),
                address=accounts[0],
                color=BRIDGE_CALENDAR_COLOR,
            )

            # one reminder is created at the time of the calendar entry
            reminders = calendar_db.query_reminder_entry(event_id=calendar_entry.identifier)['entries']  # noqa: E501
            assert len(reminders) == 1
            assert reminders[0].event_id == calendar_entry.identifier
            assert reminders[0].secs_before == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.freeze_time('2025-03-05 00:00:00 GMT')
@pytest.mark.parametrize('optimism_accounts', [['0xD4dd9a1FAc6D7bBe327c2b4A5Dc3197D0B10874b']])
def test_locked_velo_calendar_reminders(
        database: DBHandler,
        optimism_accounts: list[ChecksumEvmAddress],
        optimism_inquirer: OptimismInquirer,
) -> None:
    """Test that reminders are created at lock period end of VELO in vote escrow."""
    calendar_db = DBCalendar(database)
    all_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert all_calendar_entries['entries_total'] == 0

    events, _ = get_decoded_events_of_transaction(
        tx_hash=deserialize_evm_tx_hash('0x8747ae5f08613802c76f3c6d4517c87c2133b0231990dd30df32b8c9bb9fa7a1'),
        evm_inquirer=optimism_inquirer,
    )
    reminder_creator = CalendarReminderCreator(database=database, current_ts=ts_now())
    reminder_creator.maybe_create_locked_aero_vero_reminders()

    new_calendar_entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert new_calendar_entries['entries_found'] == 1

    calendar_entry = new_calendar_entries['entries'][0]
    assert events[2].extra_data is not None
    assert calendar_entry == CalendarEntry(
        identifier=1,
        name='VELO veNFT-30123 vote escrow lock period ends',
        timestamp=Timestamp(1741219200),
        description=f'Lock period for VELO veNFT-30123 in vote escrow ends on {reminder_creator.timestamp_to_date(events[2].extra_data["lock_time"])}',  # noqa: E501
        counterparty=CPT_VELODROME,
        blockchain=ChainID.deserialize(events[2].location.to_chain_id()).to_blockchain(),
        address=optimism_accounts[0],
        color=AERO_VELO_CALENDAR_COLOR,
        auto_delete=True,
    )
    reminders = calendar_db.query_reminder_entry(event_id=calendar_entry.identifier)['entries']
    assert len(reminders) == 1
    assert reminders[0].event_id == calendar_entry.identifier
    assert reminders[0].secs_before == 0


@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_delete_calendar_entry_preserves_unrelated_reminders(
        database: DBHandler,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Regression test for the calendar entry deletion also removing the reminder whose
    own primary key matched the deleted entry's calendar identifier. Since reminders and
    calendar entries have separate identifier spaces this deleted the reminder of an
    unrelated calendar entry, while the deleted entry's own reminders are already
    removed by the foreign key cascade.
    """
    user_address = ethereum_accounts[0]
    calendar_db = DBCalendar(database)
    entry_a_id, entry_b_id = (calendar_db.create_calendar_entry(CalendarEntry(
        name=name,
        timestamp=Timestamp(ts_now() + WEEK_IN_SECONDS),
        description=None,
        counterparty=CPT_ENS,
        address=user_address,
        blockchain=SupportedBlockchain.ETHEREUM,
        color=None,
        auto_delete=False,
    )) for name in ('Entry A', 'Entry B'))
    for event_id in (entry_b_id, entry_a_id):  # create B's reminder first so that A's reminder gets a primary key equal to entry B's calendar identifier  # noqa: E501
        calendar_db.create_reminder_entries(reminders=[ReminderEntry(
            identifier=0,  # ignored, auto-generated in the db
            event_id=event_id,
            secs_before=0,
            acknowledged=False,
        )])

    reminder_a = calendar_db.query_reminder_entry(event_id=entry_a_id)['entries'][0]
    assert reminder_a.identifier == entry_b_id  # precondition for the regression scenario

    CalendarReminderCreator(database=database, current_ts=ts_now()).delete_calendar_entry(
        name='Entry B',
        counterparty=CPT_ENS,
        address=user_address,
        blockchain=SupportedBlockchain.ETHEREUM,
    )
    assert calendar_db.query_calendar_entry(CalendarFilterQuery.make())['entries_found'] == 1
    assert calendar_db.count_reminder_entries(event_id=entry_b_id) == 0  # removed by the cascade
    assert calendar_db.count_reminder_entries(event_id=entry_a_id) == 1  # unrelated reminder kept


@pytest.mark.freeze_time('2026-01-01 00:00:00 GMT')
@pytest.mark.parametrize('ethereum_accounts', [['0xe07d9C9cF00F9d6a4fD595A31cbb7BC0953a41A0']])
def test_yearn_vesting_calendar_reminders(
        database: DBHandler,
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that cliff and fully vested reminders are created for yearn vesting escrows
    discovered from the decoded events, with the schedule queried from the chain.
    Time is frozen before the escrow cliff so that both milestones are in the future.
    """
    escrow = string_to_evm_address('0xd3604112d1666AEE55d2133947A55663cA9fbF4C')
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_event(write_cursor=write_cursor, event=EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=0,
            timestamp=TimestampMS(0),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
            asset=A_DAI,  # the asset is not used by the reminder creation
            amount=ONE,
            location_label=(user_address := ethereum_accounts[0]),
            counterparty=CPT_YEARN_VESTING,
            address=escrow,
        ))

    reminder_creator = CalendarReminderCreator(
        database=database,
        current_ts=ts_now(),
        ethereum_inquirer=ethereum_inquirer,
    )
    reminder_creator.maybe_create_yearn_vesting_reminders()

    calendar_db = DBCalendar(database)
    entries = calendar_db.query_calendar_entry(CalendarFilterQuery.make())
    assert entries['entries_found'] == 2
    cliff_entry, end_entry = entries['entries']
    cliff_time, end_time = Timestamp(1778155200), Timestamp(1856995200)
    assert cliff_entry == CalendarEntry(
        identifier=2,
        name=f'Yearn vesting cliff for {escrow}',
        timestamp=cliff_time,
        description=f'Yearn vesting escrow {escrow} reaches its cliff on {reminder_creator.timestamp_to_date(cliff_time)}',  # noqa: E501
        counterparty=CPT_YEARN_VESTING,
        address=user_address,
        blockchain=SupportedBlockchain.ETHEREUM,
        color=YEARN_VESTING_CALENDAR_COLOR,
        auto_delete=True,
    )
    assert end_entry == CalendarEntry(
        identifier=1,
        name=f'Yearn vesting ends for {escrow}',
        timestamp=end_time,
        description=f'Yearn vesting escrow {escrow} is fully vested on {reminder_creator.timestamp_to_date(end_time)}',  # noqa: E501
        counterparty=CPT_YEARN_VESTING,
        address=user_address,
        blockchain=SupportedBlockchain.ETHEREUM,
        color=YEARN_VESTING_CALENDAR_COLOR,
        auto_delete=True,
    )
    for entry in (cliff_entry, end_entry):
        reminders = calendar_db.query_reminder_entry(event_id=entry.identifier)['entries']
        assert len(reminders) == 1
        assert reminders[0].secs_before == 0
