import sys
from typing import Any, Dict

MANUALLY_CHECKED = {
    # On 16/03/2019 BCY is still active and trading in one exchange
    # https://coinmarketcap.com/currencies/bitcrystals/#charts
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'BCY': True,
    # On 16/03/2019 TALK is still active and trading in one exchange
    # https://coinmarketcap.com/currencies/btctalkcoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'TALK': True,
    # On 16/03/2019 Bitmark is still active and trading in one exchange
    # https://coinmarketcap.com/currencies/bitmark/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'BTM': True,
    # On 17/03/2019 DreamCoin is still active and trading in 2 exchanges
    # https://coinmarketcap.com/currencies/dreamcoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'DRM': True,
    # On 17/03/2019 e-Gulden is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/e-gulden/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'EFL': True,
    # On 18/03/2019 OPAL is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/opal/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'OPAL': True,
    # On 18/03/2019 Piggy coin is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/piggycoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'PIGGY': True,
    # On 18/03/2019 Smart coin is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/smartcoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'SMC': True,
    # On 18/03/2019 Ultra coin is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/ultracoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'UTC': True,
    # On 21/03/2019 Mithril Ore token is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/mithril-ore/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'MORE-2': True,
    # On 25/03/2019 Modum is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/modum/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'MOD': True,
    # On 30/03/2019 Adcoin is still active and trading in 2 exchange
    # https://coinmarketcap.com/currencies/adcoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'ACC': True,
    # On 31/03/2019 PolyAI is still active and trading in 2 exchange
    # https://coinmarketcap.com/currencies/poly-ai/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'AI': True,
    # On 31/03/2019 BlockchainData Token is still active and trading in 2 exchange
    # https://coinmarketcap.com/currencies/blockchain-certified-data-token/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'BCDT': True,
    # On 31/03/2019 Dao.Casino is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/dao-casino/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'BET': True,
    # On 31/03/2019 BrokerNekoNetwork is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/brokernekonetwork/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'BNN': True,
}


def active_check(
        asset_symbol: str,
        our_asset: Dict[str, Any],
        our_data: Dict[str, Any],
        paprika_data: Dict[str, Any],
        cmc_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Process the active attribute from coin paprika and coinmarketcap

    Then compare to our data and provide choices to clean up the data.
    """
    our_active = our_asset.get('active', None)
    cmc_active = None
    if cmc_data:
        cmc_active = True if cmc_data['is_active'] == 1 else False
    paprika_active = None
    if paprika_data:
        paprika_active = paprika_data['is_active']

    if asset_symbol in MANUALLY_CHECKED:
        our_data[asset_symbol]['active'] = MANUALLY_CHECKED[asset_symbol]
        return our_data

    if our_active:
        if paprika_active != our_active:
            print(
                f"For asset {asset_symbol}'s 'is_active' our data and "
                f"coin paprika do not agree.",
            )
            sys.exit(1)

    if cmc_data and paprika_data and cmc_active != paprika_active:
        print(
            f"For asset {asset_symbol}'s 'is_active' coin paprika and "
            f"coinmarketcap do not agree.",
        )
        sys.exit(1)

    # If we get here and externals say it's not active then set it so
    if our_active is None and paprika_data and paprika_active is False:
        print(f'External APIs tell us that {asset_symbol} is not currently active')
        our_data[asset_symbol]['active'] = paprika_active

    return our_data
