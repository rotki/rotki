from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.rotkehlchen import BalancesTestSetup
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc


def get_asset_balance_total(asset: str, setup: BalancesTestSetup) -> FVal:
    conversion_function = satoshis_to_btc if asset == 'BTC' else from_wei
    total = ZERO
    if Asset(asset).is_fiat():
        total += setup.fiat_balances.get(asset, ZERO)
    elif asset in ('ETH', 'BTC'):
        asset_balances = getattr(setup, f'{asset.lower()}_balances')
        total += sum(conversion_function(FVal(b)) for b in asset_balances)
    elif EthereumToken(asset):
        asset_balances = setup.token_balances[asset]
        total += sum(conversion_function(FVal(b)) for b in asset_balances)
    else:
        raise AssertionError(f'not implemented for asset {asset}')
    total += setup.binance_balances.get(asset, ZERO)
    total += setup.poloniex_balances.get(asset, ZERO)

    return total
