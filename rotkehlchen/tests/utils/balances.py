from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.rotkehlchen import BalancesTestSetup
from rotkehlchen.utils.misc import from_wei, satoshis_to_btc


def get_asset_balance_total(asset_symbol: str, setup: BalancesTestSetup) -> FVal:
    conversion_function = satoshis_to_btc if asset_symbol == 'BTC' else from_wei
    total = ZERO
    asset = Asset(asset_symbol)

    if asset_symbol in ('ETH', 'BTC'):
        asset_balances = getattr(setup, f'{asset_symbol.lower()}_balances')
        total += sum(conversion_function(FVal(b)) for b in asset_balances)
    elif asset.is_eth_token():
        asset_balances = setup.token_balances[EthereumToken(asset_symbol)]
        total += sum(conversion_function(FVal(b)) for b in asset_balances)

    total += setup.binance_balances.get(asset_symbol, ZERO)
    total += setup.poloniex_balances.get(asset_symbol, ZERO)

    if setup.manually_tracked_balances:
        for entry in setup.manually_tracked_balances:
            if entry.asset.identifier == asset_symbol:
                total += entry.amount

    return total
