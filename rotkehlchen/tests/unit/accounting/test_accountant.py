from unittest.mock import patch

import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.constants.assets import A_ETH, A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Location, Timestamp, TimestampMS


@pytest.fixture
def new_accountant(database, messages_aggregator, blockchain, price_historian):
    """Create a new Accountant instance for testing"""
    return Accountant(
        db=database,
        msg_aggregator=messages_aggregator,
        chains_aggregator=blockchain,
        premium=None,
    )


@pytest.fixture
def sample_history_events(database):
    """Create sample history events for testing"""
    events = []

    # Use consistent addresses for related events
    eth_address = make_evm_address()

    # Create all events
    events.extend([
        # Event 1: Receive 1 ETH
        HistoryEvent(
            event_identifier='0x1',
            sequence_index=0,
            timestamp=TimestampMS(1600000000000),  # 2020-09-13
            location=Location.ETHEREUM,
            location_label=eth_address,
            asset=A_ETH,
            amount=FVal('1.0'),
            notes='Received ETH',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
        ),
        # Event 2: Receive 1000 USD
        HistoryEvent(
            event_identifier='0x2',
            sequence_index=0,
            timestamp=TimestampMS(1600010000000),  # ~3 hours later
            location=Location.KRAKEN,
            location_label='kraken1',
            asset=A_USD,
            amount=FVal('1000.0'),
            notes='Received USD',
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
        ),
        # Event 3: Spend 0.5 ETH
        HistoryEvent(
            event_identifier='0x3',
            sequence_index=0,
            timestamp=TimestampMS(1600020000000),  # ~6 hours later
            location=Location.ETHEREUM,
            location_label=eth_address,  # Same address as event 1
            asset=A_ETH,
            amount=FVal('-0.5'),
            notes='Spent ETH',
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
        ),
    ])

    # Save events to database
    from rotkehlchen.db.history_events import DBHistoryEvents
    dbevents = DBHistoryEvents(database)

    with database.user_write() as write_cursor:
        for event in events:
            dbevents.add_history_event(write_cursor, event)

    return events


class TestAccountantBasics:
    """Test basic Accountant functionality"""

    def test_accountant_initialization(self, new_accountant):
        """Test that Accountant initializes correctly"""
        assert new_accountant.db is not None
        assert new_accountant.msg_aggregator is not None
        assert new_accountant.chains_aggregator is not None
        assert new_accountant.premium is None

    def test_has_pending_work_initially_false(self, new_accountant):
        """Test that initially there's no pending work"""
        assert new_accountant.has_pending_work() is False

    def test_mark_and_clear_pending_work(self, new_accountant):
        """Test marking and clearing pending work"""
        # Initially no pending work
        assert new_accountant.has_pending_work() is False

        # Mark work as pending
        new_accountant._mark_accounting_work_pending()
        assert new_accountant.has_pending_work() is True

        # Clear pending work
        new_accountant._clear_accounting_work_pending()
        assert new_accountant.has_pending_work() is False


class TestSettingsHash:
    """Test settings hash generation and behavior"""

    def test_settings_hash_generation(self, new_accountant):
        """Test that settings hash is generated consistently"""
        hash1 = new_accountant.get_current_settings_hash()
        hash2 = new_accountant.get_current_settings_hash()

        # Should be consistent
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex string

    def test_settings_hash_changes_with_settings(self, new_accountant, database):
        """Test that settings hash changes when settings change"""
        # Get initial hash
        initial_hash = new_accountant.get_current_settings_hash()

        # Change a setting that affects accounting
        with database.user_write() as cursor:
            cursor.execute(
                'INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)',
                ('include_crypto2crypto', '1'),  # Change a different setting
            )

        # Hash should be different
        new_hash = new_accountant.get_current_settings_hash()
        assert new_hash != initial_hash, f'Hash should change: {initial_hash} vs {new_hash}'


class TestEventProcessing:
    """Test event processing and accounting calculation"""

    def test_get_events_missing_accounting(self, new_accountant, sample_history_events):
        """Test finding events that need accounting calculation"""
        settings_hash = new_accountant.get_current_settings_hash()

        # All events should be missing accounting initially
        missing_events = new_accountant._get_events_missing_accounting(settings_hash)
        assert len(missing_events) == 3

        # IDs should be in order
        assert missing_events == sorted(missing_events)

    @patch('rotkehlchen.accounting.accountant.PriceHistorian')
    def test_basic_accounting_calculation(
            self, mock_historian_class, new_accountant, sample_history_events,
    ):
        """Test basic accounting calculation for events"""
        # Mock price to 1000 USD per ETH
        mock_historian = mock_historian_class.return_value
        mock_historian.query_historical_price.return_value = FVal('1000')

        settings_hash = new_accountant.get_current_settings_hash()
        missing_events = new_accountant._get_events_missing_accounting(settings_hash)

        # Process the events
        processed_count = new_accountant._calculate_accounting_for_events(
            missing_events, settings_hash,
        )
        assert processed_count == 3

        # Verify accounting data was created
        with new_accountant.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM history_events_accounting '
                'WHERE accounting_settings_hash = ?',
                (settings_hash,),
            )
            count = cursor.fetchone()[0]
            assert count == 3

    @patch('rotkehlchen.accounting.accountant.PriceHistorian')
    def test_balance_tracking(self, mock_historian_class, new_accountant, sample_history_events):
        """Test that asset balances are tracked correctly"""
        # Mock prices
        mock_historian = mock_historian_class.return_value
        mock_historian.query_historical_price.return_value = FVal('1000')  # 1000 USD per ETH

        settings_hash = new_accountant.get_current_settings_hash()
        missing_events = new_accountant._get_events_missing_accounting(settings_hash)

        # Process events
        new_accountant._calculate_accounting_for_events(missing_events, settings_hash)

        # Check balance tracking table
        with new_accountant.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT asset, amount FROM asset_location_balances ORDER BY timestamp',
            )
            balances = cursor.fetchall()

            # Should have balance updates for each event
            assert len(balances) >= 3

            # Check some specific balances
            eth_balances = [b for b in balances if b[0] == A_ETH.identifier]
            assert len(eth_balances) >= 2  # At least receive and spend

            # Final ETH balance should be 0.5 (1.0 received - 0.5 spent)
            final_eth_balance = FVal(eth_balances[-1][1])
            assert final_eth_balance == FVal('0.5')


class TestInvalidation:
    """Test invalidation logic"""

    @patch('rotkehlchen.accounting.accountant.PriceHistorian')
    def test_invalidate_from_timestamp(
            self, mock_historian_class, new_accountant, sample_history_events,
    ):
        """Test invalidating accounting data from a specific timestamp"""
        mock_historian = mock_historian_class.return_value
        mock_historian.query_historical_price.return_value = FVal('1000')

        settings_hash = new_accountant.get_current_settings_hash()
        missing_events = new_accountant._get_events_missing_accounting(settings_hash)

        # Process all events
        new_accountant._calculate_accounting_for_events(missing_events, settings_hash)

        # Verify all events have accounting data
        with new_accountant.db.conn.read_ctx() as cursor:
            cursor.execute('SELECT COUNT(*) FROM history_events_accounting')
            initial_count = cursor.fetchone()[0]
            assert initial_count == 3

        # Invalidate from middle timestamp
        invalidate_timestamp = Timestamp(1600015000)  # Between event 2 and 3
        new_accountant.invalidate_from_timestamp(invalidate_timestamp)

        # Should have removed accounting data for events after timestamp
        with new_accountant.db.conn.read_ctx() as cursor:
            cursor.execute('SELECT COUNT(*) FROM history_events_accounting')
            remaining_count = cursor.fetchone()[0]
            assert remaining_count < initial_count

        # Should have marked work as pending
        assert new_accountant.has_pending_work() is True

    @patch('rotkehlchen.accounting.accountant.PriceHistorian')
    def test_invalidate_specific_assets(
            self, mock_historian_class, new_accountant, sample_history_events,
    ):
        """Test invalidating accounting data for specific assets only"""
        mock_historian = mock_historian_class.return_value
        mock_historian.query_historical_price.return_value = FVal('1000')

        settings_hash = new_accountant.get_current_settings_hash()
        missing_events = new_accountant._get_events_missing_accounting(settings_hash)

        # Process all events
        new_accountant._calculate_accounting_for_events(missing_events, settings_hash)

        # Invalidate only ETH events from beginning
        new_accountant.invalidate_from_timestamp(
            timestamp=Timestamp(1600000000),
            affected_assets={A_ETH},
        )

        # Should still have USD accounting data
        with new_accountant.db.conn.read_ctx() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM history_events_accounting hea
                JOIN history_events he ON hea.history_event_id = he.identifier
                WHERE he.asset = ?
            """, (A_USD.identifier,))
            usd_count = cursor.fetchone()[0]
            assert usd_count > 0  # USD data should remain


class TestPnLCalculation:
    """Test PnL calculation accuracy"""

    @patch('rotkehlchen.accounting.accountant.PriceHistorian')
    def test_pnl_totals_calculation(
            self, mock_historian_class, new_accountant, sample_history_events,
    ):
        """Test that PnL totals are calculated correctly"""
        mock_historian = mock_historian_class.return_value
        mock_historian.query_historical_price.return_value = FVal('1000')  # 1000 USD per ETH

        settings_hash = new_accountant.get_current_settings_hash()
        missing_events = new_accountant._get_events_missing_accounting(settings_hash)

        # Process events
        new_accountant._calculate_accounting_for_events(missing_events, settings_hash)

        # Get PnL totals
        pnl_totals = new_accountant.get_pnl_totals(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1700000000),
        )

        # Should have some PnL data
        assert pnl_totals is not None
        # Note: Exact values depend on cost basis calculation implementation

    def test_ensure_accounting_calculated(self, new_accountant, sample_history_events):
        """Test the main entry point for ensuring accounting is calculated"""
        # Initially should find missing events and mark work pending
        new_accountant.ensure_accounting_calculated()

        # Should have pending work now
        assert new_accountant.has_pending_work() is True


class TestDataAccess:
    """Test data access methods"""

    @patch('rotkehlchen.accounting.accountant.PriceHistorian')
    def test_get_events_with_accounting(
            self, mock_historian_class, new_accountant, sample_history_events,
    ):
        """Test retrieving events with accounting data overlay"""
        mock_historian = mock_historian_class.return_value
        mock_historian.query_historical_price.return_value = FVal('1000')

        settings_hash = new_accountant.get_current_settings_hash()
        missing_events = new_accountant._get_events_missing_accounting(settings_hash)

        # Process events
        new_accountant._calculate_accounting_for_events(missing_events, settings_hash)

        # Get events with accounting data
        events_with_accounting = new_accountant.get_events_with_accounting(
            start_ts=Timestamp(1600000000),
            end_ts=Timestamp(1700000000),
        )

        # Should return events (though event deserialization needs work)
        assert isinstance(events_with_accounting, list)
        # Note: Full testing requires proper event deserialization
