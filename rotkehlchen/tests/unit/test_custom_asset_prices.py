import pytest
from unittest.mock import patch, MagicMock

from rotkehlchen.assets.asset import Asset, CustomAsset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import Price


def test_store_custom_asset_price():
    """Test storing a custom asset price in the _custom_asset_prices dictionary"""
    # Clear the dictionary before testing
    Inquirer._custom_asset_prices = {}
    
    # Create a custom asset
    custom_asset = CustomAsset.initialize(
        identifier='test-car',
        name='My Car',
        custom_asset_type='automobile',
        notes='This is my car',
    )
    
    # Create an Asset from the custom asset
    asset = Asset('test-car')
    
    # Store a price
    test_price = Price(FVal('120000'))
    Inquirer._store_custom_asset_price(asset, test_price)
    
    # Verify the price was stored
    assert 'test-car' in Inquirer._custom_asset_prices
    assert Inquirer._custom_asset_prices['test-car'] == test_price


def test_get_custom_asset_price():
    """Test retrieving a custom asset price from the _custom_asset_prices dictionary"""
    # Set up a test price
    Inquirer._custom_asset_prices = {'test-car': Price(FVal('120000'))}
    
    # Create an Asset
    asset = Asset('test-car')
    
    # Get the price
    price = Inquirer._get_custom_asset_price(asset)
    
    # Verify the price was retrieved
    assert price == Price(FVal('120000'))


def test_get_custom_asset_price_not_found():
    """Test retrieving a custom asset price that doesn't exist"""
    # Clear the dictionary
    Inquirer._custom_asset_prices = {}
    
    # Create an Asset
    asset = Asset('nonexistent-asset')
    
    # Get the price
    price = Inquirer._get_custom_asset_price(asset)
    
    # Verify no price was found
    assert price is None


def test_handle_custom_asset_price():
    """Test the _handle_custom_asset_price method"""
    # Set up a test price
    Inquirer._custom_asset_prices = {'test-car': Price(FVal('120000'))}
    
    # Create an Asset
    asset = Asset('test-car')
    
    # Handle the price
    was_handled, price = Inquirer._handle_custom_asset_price(asset)
    
    # Verify the asset was handled and the price was retrieved
    assert was_handled is True
    assert price == Price(FVal('120000'))


def test_handle_custom_asset_price_not_found():
    """Test the _handle_custom_asset_price method for an asset without a price"""
    # Clear the dictionary
    Inquirer._custom_asset_prices = {}
    
    # Create an Asset
    asset = Asset('nonexistent-asset')
    
    # Mock the _get_custom_asset_price method to return None
    with patch.object(Inquirer, '_get_custom_asset_price', return_value=None):
        # Handle the price
        was_handled, price = Inquirer._handle_custom_asset_price(asset)
        
        # For a custom asset without a price, it should still be marked as handled
        # but return ZERO_PRICE
        assert was_handled is False
        assert price == ZERO_PRICE


def test_find_usd_price_for_custom_asset():
    """Test the find_usd_price method for a custom asset"""
    # Set up a test price
    Inquirer._custom_asset_prices = {'test-car': Price(FVal('120000'))}
    
    # Create an Asset
    asset = Asset('test-car')
    
    # Create a mock custom asset
    mock_custom_asset = CustomAsset.initialize(
        identifier='test-car',
        name='My Car',
        custom_asset_type='automobile',
        notes='This is my car',
    )
    
    # Mock the necessary functions instead of trying to patch the Asset object
    with patch('rotkehlchen.assets.asset.Asset.get_asset_type', return_value=AssetType.CUSTOM_ASSET), \
         patch('rotkehlchen.assets.asset.Asset.resolve', return_value=mock_custom_asset):
        # Get the price
        price = Inquirer.find_usd_price(asset)
        
        # Verify the price was retrieved
        assert price == Price(FVal('120000'))


def test_find_usd_price_for_custom_asset_ignore_cache():
    """Test the find_usd_price method for a custom asset with ignore_cache=True"""
    # Set up a test price
    Inquirer._custom_asset_prices = {'test-car': Price(FVal('120000'))}
    
    # Create an Asset
    asset = Asset('test-car')
    
    # Create a mock custom asset
    mock_custom_asset = CustomAsset.initialize(
        identifier='test-car',
        name='My Car',
        custom_asset_type='automobile',
        notes='This is my car',
    )
    
    # Mock the necessary functions instead of trying to patch the Asset object
    with patch('rotkehlchen.assets.asset.Asset.get_asset_type', return_value=AssetType.CUSTOM_ASSET), \
         patch('rotkehlchen.assets.asset.Asset.resolve', return_value=mock_custom_asset):
        # Get the price with ignore_cache=True
        price = Inquirer.find_usd_price(asset, ignore_cache=True)
        
        # Verify the price was still retrieved (custom assets should ignore the ignore_cache flag)
        assert price == Price(FVal('120000'))


def test_preprocess_assets_to_query_custom_assets():
    """Test the _preprocess_assets_to_query method with custom assets"""
    # Set up a test price
    Inquirer._custom_asset_prices = {'test-car': Price(FVal('120000'))}
    
    # Create an Asset
    asset = Asset('test-car')
    
    # Mock the get_asset_type function at the module level
    with patch('rotkehlchen.assets.asset.Asset.get_asset_type', return_value=AssetType.CUSTOM_ASSET):
        # Preprocess the asset
        found_prices, replaced_assets, unpriced_assets = Inquirer._preprocess_assets_to_query(
            from_assets=[asset],
            to_asset=Asset('USD'),
            ignore_cache=True,
        )
        
        # Verify the asset was found in the _custom_asset_prices dictionary
        assert asset in found_prices
        assert found_prices[asset][0] == Price(FVal('120000'))
        assert len(replaced_assets) == 0
        assert len(unpriced_assets) == 0 