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
    # On 04/08/2019 Contentos is still active and trading in one exchange
    # https://coinmarketcap.com/currencies/contentos/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'COS': True,
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
    # On 01/04/2019 Biotron is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/biotron/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'BTRN': True,
    # On 01/04/2019 BlockCAT is still active and trading in 2 exchanges
    # https://coinmarketcap.com/currencies/blockcat/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'CAT-2': True,
    # On 01/04/2019 CoinEx is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/coinex-token/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'CET': True,
    # On 01/04/2019 CruiseBit is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/cruisebit/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'CRBT': True,
    # On 01/04/2019 Verify/CRED is still active and trading in 3 exchanges
    # https://coinmarketcap.com/currencies/verify/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'CRED': True,
    # On 01/04/2019 Cryptosolartech is still active and trading in 3 exchanges
    # https://coinmarketcap.com/currencies/cryptosolartech/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'CST': True,
    # On 02/04/2019 DEW is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/dew
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'DEW': True,
    # On 02/04/2019 DOR is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/dorado/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'DOR': True,
    # On 02/04/2019 EARTH is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/earth-token/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'EARTH': True,
    # On 03/04/2019 EDU-2 (EDU token) is still active and trading in 1 exchange
    # https://coincodex.com/crypto/open-source-university/exchanges/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'EDU-2': True,
    # On 03/04/2019 Ethersport is still active and trading in 2 exchanges
    # https://coinmarketcap.com/currencies/ethersportz/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'ESZ': True,
    # On 03/04/2019 EZToken is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/eztoken/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'EZT': True,
    # On 04/04/2019 Fidelium is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/fidelium/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'FID': True,
    # On 04/04/2019 FoodCoin is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/food/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'FOOD': True,
    # On 04/04/2019 ForkCoin is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/forkcoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'FORK': True,
    # On 04/04/2019 Fcoin Token is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/ftoken
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'FT-2': True,
    # On 05/04/2019 GreenMed Token is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/greenmed/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'GRMD': True,
    # On 06/04/2019 Linkey is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/linkey/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'LKY': True,
    # On 28/07/2019 LUNA Terra is still active and trading in multiple exchanges
    # https://coinmarketcap.com/currencies/terra/#markets
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'LUNA-2': True,
    # On 06/04/2019 MCAP is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/mcap/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'MCAP': True,
    # On 06/04/2019 MindexCoin is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/mindexcoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'MIC': True,
    # On 06/04/2019 ModulTrade is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/modultrade/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'MTRC': True,
    # On 07/04/2019 NEVERDIE appears to be inactive and trading in 0 exchanges
    # https://coinmarketcap.com/currencies/neverdie/
    # For some reason coinmarketcap does not show it as inactive yet
    'NDC': False,
    # On 07/04/2019 Nuggets is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/nuggets/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'NUG': True,
    # On 09/04/2019 POS is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/postoken/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'POS': True,
    # On 10/04/2019 RIYA is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/etheriya
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'RIYA': True,
    # On 10/04/2019 RTB is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/ab-chain-rtb/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'RTB': True,
    # On 10/04/2019 SAC is still active and trading in 2 exchanges
    # https://coinmarketcap.com/currencies/smart-application-chain/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'SAC': True,
    # On 10/04/2019 SugarExchange is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/sugar-exchange/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'SGR': True,
    # On 11/04/2019 SpeedMiningService is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/speed-mining-service/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'SMS': True,
    # On 28/07/2019 Spin protocol is active and trading in multiple exchanges
    # https://coinmarketcap.com/currencies/spin-protocol/#markets
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'SPIN': True,
    # On 11/04/2019 TALAO is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/talao/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'TALAO': True,
    # On 11/04/2019 TigerCash is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/tigercash/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'TCH-2': True,
    # On 11/04/2019 TargetCoin is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/target-coin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'TGT': True,
    # On 11/04/2019 Ties.DB is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/tiesdb/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'TIE': True,
    # On 12/04/2019 Tokia is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/tokia/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'TKA': True,
    # On 12/04/2019 Trakinvest is still active and trading in 2 exchanges
    # https://coinmarketcap.com/currencies/trakinvest/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'TRAK': True,
    # On 12/04/2019 Verisafe is still active and trading in 3 exchanges
    # https://coinmarketcap.com/currencies/verisafe/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'VSF': True,
    # On 12/04/2019 Wi Coin appears to be inactive and trading in 0 exchanges
    # https://coinmarketcap.com/currencies/wi-coin/
    # For some reason coinmarketcap does not show it as inactive yet
    'WIC': False,
    # On 12/04/2019 Wysker is still active and trading in 1 exchanges
    # https://coinmarketcap.com/currencies/wys-token
    # For some reason coin paprika thinks it's not so specify here we manually
    # checked
    'WYS': True,
    # On 12/04/2019 Billionare token is still active and trading in 1 exchanges
    # https://coinmarketcap.com/currencies/billionaire-token/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked
    'XBL': True,
    # On 12/04/2019 ClearCoin is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/clearcoin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'XCLR': True,
    # On 12/04/2019 Xenon appears to be inactive and trading in 0 exchanges
    # https://coinmarketcap.com/currencies/xenon/
    # For some reason coinmarketcap does not show it as inactive yet
    'XNN': False,
    # On 29/01/2020 Xensor is still active and trading in multiple exchanges
    # https://coinmarketcap.com/currencies/xensor/markets/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'XSR': True,
    # On 29/04/2020 YOU is still active and trading in 3 exchange
    # https://coinmarketcap.com/currencies/you-coin/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'YOU': True,
    # On 12/04/2019 Crowdholding is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/crowdholding/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'YUP': True,
    # On 12/04/2019 ZeusNetwork is still active and trading in 2 exchanges
    # https://coinmarketcap.com/currencies/zeusnetwork/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'ZEUS': True,
    # On 12/04/2019 Zinc is still active and trading in 1 exchange
    # https://coinmarketcap.com/currencies/zinc/
    # For some reason coin paprika thinks it's not so specify here we
    # manually checked.
    'ZINC': True,
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
            f"coinmarketcap do not agree. Paprika says: {paprika_active} and ",
            f"coinmarketcap says: {cmc_active}"
        )
        sys.exit(1)

    # If we get here and externals say it's not active then set it so
    if our_active is None and paprika_data and paprika_active is False:
        print(f'External APIs tell us that {asset_symbol} is not currently active')
        our_data[asset_symbol]['active'] = paprika_active

    return our_data
