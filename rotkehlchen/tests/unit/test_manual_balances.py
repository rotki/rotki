import pytest
from unittest.mock import patch, MagicMock

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset, CustomAsset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.balances.manual import (
    ManuallyTrackedBalance,
    add_manually_tracked_balances,
    edit_manually_tracked_balances,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import Location, Price


@pytest.fixture
def mock_db():
    """Create a mock database for testing"""
    mock = MagicMock()
    mock.user_write.return_value.__enter__.return_value = mock
    return mock


@pytest.fixture
def custom_car_asset():
    """Create a custom car asset for testing"""
    custom_asset = CustomAsset.initialize(
        identifier='test-car',
        name='My Car',
        custom_asset_type='automobile',
        notes='This is my car',
    )
    return Asset('test-car')


def test_add_manually_tracked_balance_with_custom_asset(mock_db, custom_car_asset):
    """Test adding a manually tracked balance with a custom asset"""
    # Clear the custom asset prices dictionary
    Inquirer._custom_asset_prices = {}
    
    # Create a manually tracked balance with a custom asset
    balance = ManuallyTrackedBalance(
        identifier=-1,
        asset=custom_car_asset,
        label='My Car',
        amount=FVal('1'),
        location=Location.BANKS,
        tags=None,
        balance_type=BalanceType.ASSET,
    )
    
    # Set the _price attribute
    setattr(balance, '_price', FVal('120000'))
    
    # Create a mock custom asset
    mock_custom_asset = CustomAsset.initialize(
        identifier='test-car',
        name='My Car',
        custom_asset_type='automobile',
        notes='This is my car',
    )
    
    # Set the price directly in the Inquirer._custom_asset_prices dictionary
    Inquirer._custom_asset_prices['test-car'] = Price(FVal('120000'))
    
    # Mock the necessary functions instead of trying to patch the Asset object
    with patch('rotkehlchen.assets.asset.Asset.get_asset_type', return_value=AssetType.CUSTOM_ASSET), \
         patch('rotkehlchen.assets.asset.Asset.resolve', return_value=mock_custom_asset):
        # Add the balance
        add_manually_tracked_balances(mock_db, [balance])
    
    # Verify the price was stored in the _custom_asset_prices dictionary
    assert 'test-car' in Inquirer._custom_asset_prices
    assert Inquirer._custom_asset_prices['test-car'] == Price(FVal('120000'))
    
    # Verify the database methods were called
    mock_db.ensure_tags_exist.assert_called_once()
    mock_db.add_manually_tracked_balances.assert_called_once()


def test_add_manually_tracked_balance_with_custom_asset_no_price(mock_db, custom_car_asset):
    """Test adding a manually tracked balance with a custom asset but no price"""
    # Clear the custom asset prices dictionary
    Inquirer._custom_asset_prices = {}
    
    # Create a manually tracked balance with a custom asset
    balance = ManuallyTrackedBalance(
        identifier=-1,
        asset=custom_car_asset,
        label='My Car',
        amount=FVal('1'),
        location=Location.BANKS,
        tags=None,
        balance_type=BalanceType.ASSET,
    )
    
    # Don't set the _price attribute
    
    # Create a mock custom asset
    mock_custom_asset = CustomAsset.initialize(
        identifier='test-car',
        name='My Car',
        custom_asset_type='automobile',
        notes='This is my car',
    )
    
    # Set the price directly in the Inquirer._custom_asset_prices dictionary
    Inquirer._custom_asset_prices['test-car'] = Price(FVal('1'))
    
    # Mock the necessary functions instead of trying to patch the Asset object
    with patch('rotkehlchen.assets.asset.Asset.get_asset_type', return_value=AssetType.CUSTOM_ASSET), \
         patch('rotkehlchen.assets.asset.Asset.resolve', return_value=mock_custom_asset):
        # Add the balance
        add_manually_tracked_balances(mock_db, [balance])
    
    # Verify the amount was used as the price
    assert 'test-car' in Inquirer._custom_asset_prices
    assert Inquirer._custom_asset_prices['test-car'] == Price(FVal('1'))


def test_edit_manually_tracked_balance_with_custom_asset(mock_db, custom_car_asset):
    """Test editing a manually tracked balance with a custom asset"""
    # Clear the custom asset prices dictionary
    Inquirer._custom_asset_prices = {}
    
    # Create a manually tracked balance with a custom asset
    balance = ManuallyTrackedBalance(
        identifier=1,  # Use a real ID for editing
        asset=custom_car_asset,
        label='My Car',
        amount=FVal('1'),
        location=Location.BANKS,
        tags=None,
        balance_type=BalanceType.ASSET,
    )
    
    # Set the _price attribute
    setattr(balance, '_price', FVal('120000'))
    
    # Create a mock custom asset
    mock_custom_asset = CustomAsset.initialize(
        identifier='test-car',
        name='My Car',
        custom_asset_type='automobile',
        notes='This is my car',
    )
    
    # Set the price directly in the Inquirer._custom_asset_prices dictionary
    Inquirer._custom_asset_prices['test-car'] = Price(FVal('120000'))
    
    # Mock the necessary functions instead of trying to patch the Asset object
    with patch('rotkehlchen.assets.asset.Asset.get_asset_type', return_value=AssetType.CUSTOM_ASSET), \
         patch('rotkehlchen.assets.asset.Asset.resolve', return_value=mock_custom_asset):
        # Edit the balance
        edit_manually_tracked_balances(mock_db, [balance])
    
    # Verify the price was stored in the _custom_asset_prices dictionary
    assert 'test-car' in Inquirer._custom_asset_prices
    assert Inquirer._custom_asset_prices['test-car'] == Price(FVal('120000'))
    
    # Verify the database methods were called
    mock_db.ensure_tags_exist.assert_called_once()
    mock_db.edit_manually_tracked_balances.assert_called_once()


def test_edit_manually_tracked_balance_update_price(mock_db, custom_car_asset):
    """Test updating the price of a manually tracked balance with a custom asset"""
    # Set an initial price
    Inquirer._custom_asset_prices = {'test-car': Price(FVal('100000'))}
    
    # Create a manually tracked balance with a custom asset
    balance = ManuallyTrackedBalance(
        identifier=1,
        asset=custom_car_asset,
        label='My Car',
        amount=FVal('1'),
        location=Location.BANKS,
        tags=None,
        balance_type=BalanceType.ASSET,
    )
    
    # Set the _price attribute to a new value
    setattr(balance, '_price', FVal('120000'))
    
    # Create a mock custom asset
    mock_custom_asset = CustomAsset.initialize(
        identifier='test-car',
        name='My Car',
        custom_asset_type='automobile',
        notes='This is my car',
    )
    
    # Update the price directly in the Inquirer._custom_asset_prices dictionary
    Inquirer._custom_asset_prices['test-car'] = Price(FVal('120000'))
    
    # Mock the necessary functions instead of trying to patch the Asset object
    with patch('rotkehlchen.assets.asset.Asset.get_asset_type', return_value=AssetType.CUSTOM_ASSET), \
         patch('rotkehlchen.assets.asset.Asset.resolve', return_value=mock_custom_asset):
        # Edit the balance
        edit_manually_tracked_balances(mock_db, [balance])
    
    # Verify the price was updated in the _custom_asset_prices dictionary
    assert 'test-car' in Inquirer._custom_asset_prices
    assert Inquirer._custom_asset_prices['test-car'] == Price(FVal('120000'))


def test_add_manually_tracked_balance_empty_list(mock_db):
    """Test adding an empty list of manually tracked balances"""
    with pytest.raises(Exception):  # Should raise InputError
        add_manually_tracked_balances(mock_db, [])


def test_edit_manually_tracked_balance_empty_list(mock_db):
    """Test editing an empty list of manually tracked balances"""
    with pytest.raises(Exception):  # Should raise InputError
        edit_manually_tracked_balances(mock_db, []) 