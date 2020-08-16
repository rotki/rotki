# TODO: For the ones missing from cryptocompare make sure to also
# disallow price queries to cryptocompare for these assets
KNOWN_TO_MISS_FROM_CRYPTOCOMPARE = (
    # This is just kraken's internal fee token
    'KFEE',
    # This is just bittrex's internal credit token
    'BTXCRD',
    # For us ACH is the Altcoin Herald token. For cryptocompare it's
    # Achievecoin
    # https://www.cryptocompare.com/coins/ach/overview
    'ACH',
    # We got APH as Aphelion and APH-2 as a very shortlived Aphrodite coin
    # Cryptocompare has no data for Aphrodite coin
    'APH-2',
    # Atomic coin (https://coinmarketcap.com/currencies/atomic-coin/) is not in
    # cryptocompare but is in paprika
    'ATOM-2',
    # BORA (https://coinmarketcap.com/currencies/bora/)
    # is not in cryptocompare but is in paprika
    'BORA',
    # BOXX (https://coinmarketcap.com/currencies/blockparty-boxx-token/)
    # is not in cryptocompare but is in paprika
    'BOXX',
    # Block.Money is not in cryptocompare but it's in coin paprika
    # https://coinmarketcap.com/currencies/bloc-money/
    'BLOC-2',
    # BTCTalkCoin is not in cryptocompare but it's in coin paprika
    # https://api.coinpaprika.com/v1/coins/talk-btctalkcoin and in coinmarketcap
    # https://coinmarketcap.com/currencies/btctalkcoin/#charts
    'TALK',
    # CCN is CustomContractNetwork in Rotkehlchen but Cannacoin in cryptocompare
    # and cryptocompare does not have data for CustomContractNetwork
    'CCN',
    # Dreamcoin (https://coinmarketcap.com/currencies/dreamcoin/#charts) is not
    # in cryptocompare.
    'DRM',
    # KEY (bihu) (https://coinmarketcap.com/currencies/key/) is not in
    # cryptocompare. But it's in paprika
    'KEY-2',
    # MRS (Marginless) is not in cryptocompare. There is a coin with that
    # symbol there, but it's the MARScoin
    'MRS',
    # PRcoin, known as PRC-2 in Rotkehlcen has no data in cryptocompare
    'PRC-2',
    # Wiki coin/token is not in cryptocompare but is in paprika wiki-wiki-token
    'WIKI',
    # More token (https://coinmarketcap.com/currencies/more-coin/) is not in
    # cryptocompare but is in paprika
    'MORE',
    # Mithril Ore token (https://coinmarketcap.com/currencies/mithril-ore/) is not in
    # cryptocompare but is in paprika
    'MORE-2',
    # Aidus Token (https://coinmarketcap.com/currencies/aidus-token/) is not in
    # cryptocompare but is in paprika
    'AID-2',
    # Cashbery coin (https://coinmarketcap.com/currencies/cashbery-coin/) is not
    # in cryptocompare but is in paprika
    'CBC-2',
    # Cyber movie chain (https://coinmarketcap.com/currencies/cyber-movie-chain/)
    # is not in cryptocompare but is in paprika
    'CMCT-2',
    # Moss (https://coinmarketcap.com/currencies/moss-coin/)
    # is not in cryptocompare but is in paprika
    'MOC',
    # Solve.care (https://coinmarketcap.com/currencies/solve/) is not
    # in cryptocompare but is in paprika
    'SOLVE',
    # Stronghold USD (https://coinmarketcap.com/currencies/stronghold-usd/)
    # is not in cryptocompare but is in paprika
    'USDS-2',
    # HXRO (https://coinmarketcap.com/currencies/hxro/)
    # is not in cryptocompare but is in paprika
    'HXRO',
    # SERV (https://coinmarketcap.com/currencies/serve/)
    # is not in cryptocompare but is in paprika
    'SERV',
    # TTC (https://coinmarketcap.com/currencies/ttc-protocol/)
    # is not in cryptocompare but is in paprika
    # There is a "titcoin" as TTC in cryptocompare but that is wrong
    # https://www.cryptocompare.com/coins/ttc/overview
    'TTC',
    # BlazeCoin (https://coinmarketcap.com/currencies/blazecoin/)
    # is not in cryptocompare but is in paprika
    'BLZ-2',
    # Bitgem (https://coinmarketcap.com/currencies/bitgem/)
    # is not in cryptocompare but is in paprika
    'BTG-2',
    # 1SG (https://coinmarketcap.com/currencies/1sg/)
    # is not in cryptocompare but is in paprika
    '1SG',
    # ACChain (https://coinmarketcap.com/currencies/acchain/)
    # is not in cryptocompare but is in paprika
    'ACC-2',
    # PolyAI (https://coinmarketcap.com/currencies/poly-ai/)
    # is not in cryptocompare but is in paprika
    'AI',
    # Akropolis (https://coinmarketcap.com/currencies/akropolis/)
    # is not in cryptocompare but is in paprika
    'AKRO',
    # AiLink token (https://coinmarketcap.com/currencies/ailink-token/)
    # is not in cryptocompare but is in paprika
    'ALI',
    # Bankcoin BCash (https://bankcoinbcash.com/)
    # is not in cryptocompare but is in paprika
    'BCASH',
    # BitcapitalVendor (https://coinmarketcap.com/currencies/bitcapitalvendor/)
    # is not in cryptocompare but is in paprika
    'BCV',
    # BitPark (https://coinmarketcap.com/currencies/bitpark-coin/)
    # is not in cryptocompare but is in paprika
    'BITPARK',
    # BankCoin Cash (https://bankcoin-cash.com/)
    # is not in cryptocompare but is in paprika
    'BKC',
    # Bionic (https://coinmarketcap.com/currencies/bionic/)
    # is not in cryptocompare but is in paprika
    'BNC',
    # BrokerNekoNetwork (https://coinmarketcap.com/currencies/brokernekonetwork/)
    # is not in cryptocompare but is in paprika
    'BNN',
    # BoxToken (https://coinmarketcap.com/currencies/contentbox/)
    # is not in cryptocompare but is in paprika
    'BOX',
    # BitcoinOne (https://coinmarketcap.com/currencies/bitcoin-one/)
    # is not in cryptocompare but is in paprika
    'BTCONE',
    # BitcoinToken (https://coinmarketcap.com/currencies/bitcoin-token/)
    # is not in cryptocompare but is in paprika
    'BTK',
    # Bitether (https://coinmarketcap.com/currencies/bitether/)
    # is not in cryptocompare but is in paprika
    'BTR',
    # Blue whale token (https://coinmarketcap.com/currencies/blue-whale-token/)
    # is not in cryptocompare but is in paprika
    'BWX',
    # Carboneum (https://coinmarketcap.com/currencies/carboneum-c8-token/)
    # is not in cryptocompare but is in paprika
    'C8',
    # Cloudbrid (https://www.cloudbric.io/)
    # is not in cryptocompare but is in paprika
    'CLB',
    # COCOS-BCX (https://coinmarketcap.com/currencies/cocos-bcx/)
    # is not in cryptocompare but is in paprika
    'COCOS',
    # CruiseBit (https://coinmarketcap.com/currencies/cruisebit/)
    # is not in cryptocompare but is in paprika
    'CRBT',
    # Cryptosolartech (https://coinmarketcap.com/currencies/cryptosolartech/)
    # is not in cryptocompare but is in paprika
    'CST',
    # Centauri (https://coinmarketcap.com/currencies/centauri/)
    # is not in cryptocompare but is in paprika
    'CTX',
    # CyberFM (https://coinmarketcap.com/currencies/cyberfm/)
    # is not in cryptocompare but is in paprika
    'CYFM',
    # CyberMusic (https://coinmarketcap.com/currencies/cybermusic/)
    # is not in cryptocompare but is in paprika
    'CYMT',
    # CanonChain (https://coinmarketcap.com/currencies/cononchain/)
    # is not in cryptocompare but is in paprika
    'CZR',
    # DACSEE (https://coinmarketcap.com/currencies/dacsee/)
    # is not in cryptocompare but is in paprika
    'DACS',
    # Dalecoin (https://coinmarketcap.com/currencies/dalecoin/)
    # is not in cryptocompare but is in paprika
    'DALC',
    # Digital Assets Exchange token
    # (https://coinmarketcap.com/currencies/digital-asset-exchange-token/)
    # is not in cryptocompare but is in paprika
    'DAXT',
    # Deltachain (https://coinmarketcap.com/currencies/delta-chain/)
    # is not in cryptocompare but is in paprika
    'DELTA',
    # Dew (https://coinmarketcap.com/currencies/dew/)
    # is not in cryptocompare but is in paprika
    'DEW',
    # DEX (https://coinmarketcap.com/currencies/dex/)
    # is not in cryptocompare but is in paprika
    'DEX',
    # DragonGlass (https://coinmarketcap.com/currencies/dragonglass/)
    # is not in cryptocompare but is in paprika
    'DGS',
    # DigitalInsuranceToken (https://coinmarketcap.com/currencies/digital-insurance-token/)
    # is not in cryptocompare but is in paprika
    'DIT',
    # DigitalTicks (https://www.coingecko.com/en/coins/digital-ticks) is not in
    # cryptocompate but is in paprika
    'DTX-2',
    # E4Row (https://coinmarketcap.com/currencies/ether-for-the-rest-of-the-world/) is not in
    # cryptocompare but is in paprika
    'E4ROW',
    # EAGLE (https://coinmarketcap.com/currencies/eaglecoin/) is not in
    # cryptocompare but is in paprika
    'EAGLE',
    # OpenSource university (https://os.university/) is not in
    # cryptocompare but is in paprika
    'EDU-2',
    # ExcaliburCoin  (https://coinmarketcap.com/currencies/excaliburcoin/) is not
    # in cryptocompare but is in paprika
    'EXC',
    # Fingerprint  (https://fingerprintcoin.org/) is not
    # in cryptocompare but is in paprika
    'FGP',
    # Formosa Fincial Token  (https://coinmarketcap.com/currencies/formosa-financial/)
    # is not in cryptocompare but is in paprika
    'FMF',
    # Fcoin token  (https://coinmarketcap.com/currencies/ftoken/)
    # is not in cryptocompare but is in paprika
    'FT-2',
    # Futurax (https://coinmarketcap.com/currencies/futurax/)
    # is not in cryptocompare but is in paprika
    'FTXT',
    # FunctionX (https://coinmarketcap.com/currencies/function-x/)
    # is not in cryptocompare but is in paprika
    'FX',
    # Flexacoin (https://coinmarketcap.com/currencies/flexacoin/)
    # is not in cryptocompare but is in paprika
    'FXC',
    # Themis GET (https://coinmarketcap.com/currencies/themis/)
    # is not in cryptocompare but is in paprika
    'GET-2',
    # ParkinGO (https://coinmarketcap.com/currencies/parkingo/)
    # is not in cryptocompare but is in paprika
    'GOT-2',
    # GSENetwork (https://coinmarketcap.com/currencies/gsenetwork/)
    # is not in cryptocompare but is in paprika
    'GSE',
    # Jury.Online Token (https://coinmarketcap.com/currencies/jury-online-token/)
    # is not in cryptocompare but is in paprika
    'JOT',
    # Kava (https://coinmarketcap.com/currencies/kava/)
    # is not in cryptocompare but is in paprika
    'KAVA',
    # KanadeCoin (https://coinmarketcap.com/currencies/kanadecoin/)
    # is not in cryptocompare but is in paprika
    'KNDC',
    # KoraNetworkToken (https://coinmarketcap.com/currencies/kora-network-token/)
    # is not in cryptocompare but is in paprika
    'KNT',
    # Knekted (https://coinmarketcap.com/currencies/knekted/)
    # is not in cryptocompare but is in paprika
    'KNT-2',
    # 4NEW KWATT (https://coinmarketcap.com/currencies/4new/)
    # is not in cryptocompare but is in paprika
    'KWATT',
    # Liquorchain Token (https://etherscan.io/address/0x4A37A91eec4C97F9090CE66d21D3B3Aadf1aE5aD)
    # is not in cryptocompare but is in paprika
    'LCT-2',
    # LemoChain (https://coinmarketcap.com/currencies/lemochain/)
    # is not in cryptocompare but is in paprika
    'LEMO',
    # Linkey (https://coinmarketcap.com/currencies/linkey/)
    # is not in cryptocompare but is in paprika
    'LKY',
    # Lisk Machine Learning (https://coinmarketcap.com/currencies/lisk-machine-learning/)
    # is not in cryptocompare but is in paprika
    'LML',
    # Locus Chain (https://etherscan.io/address/0xC64500DD7B0f1794807e67802F8Abbf5F8Ffb054)
    # is not in cryptocompare but is in paprika
    'LOCUS',
    # LUNA Coin (https://coinmarketcap.com/currencies/luna-coin/markets/)
    # is not in cryptocompare but is in paprika
    'LUNA',
    # Midas Protocol (https://coinmarketcap.com/currencies/midasprotocol/)
    # is not in cryptocompare but is in paprika
    'MAS',
    # Matic (https://coinmarketcap.com/currencies/matic-network/)
    # is not in cryptocompare but is in paprika
    'MATIC',
    # Meshbox (https://coinlib.io/coin/MESH/MeshBox)
    # is not in cryptocompare but is in paprika
    'MESH',
    # Nami ICO (https://etherscan.io/address/0x8d80de8A78198396329dfA769aD54d24bF90E7aa)
    # is not in cryptocompate but is in paprika
    'NAC',
    # For Rotkehlchen NCC is neurochain and NCC-2 is NeedsCoin and neither of them
    # is in cryptocompare but they are both in paprika
    'NCC',
    'NCC-2',
    # NDEX (https://coinmarketcap.com/currencies/ndex/)
    # is not in cryptocompare but is in paprika
    'NDX',
    # NetKoin (https://coinmarketcap.com/currencies/netkoin/)
    # is not in cryptocompare but is in paprika
    'NTK-2',
    # Nuggets (https://coinmarketcap.com/currencies/nuggets/)
    # is not in cryptocompare but is in paprika
    'NUG',
    # OCtoin (https://coinmarketcap.com/currencies/octoin-coin/)
    # is not in cryptocompare but is in paprika
    'OCC',
    # OptiToken (https://coinmarketcap.com/currencies/optitoken/)
    # is not in cryptocompare but is in paprika
    'OPTI',
    # Wisepass (https://coinmarketcap.com/currencies/wisepass/)
    # is not in cryptocompare but is in paprika
    'PASS-2',
    # PLG is pledgecoin for rotki but in cryptocompare it's pledgecamp so we skip
    'PLG',
    # Kleros (https://coinmarketcap.com/currencies/kleros/)
    # is not in cryptocompare but is in paprika
    # Note: Cryptocompare has SteamPunk as PNK ...
    'PNK',
    # For Rotkehlchen POP is PopularCoin, and POP-2 is POP Chest Token, but in
    # cryptocompare POP Chest appears also as POP so I can only assume it's not
    # supported https://www.cryptocompare.com/coins/popc/overview
    'POP-2',
    # Foresting (https://coinmarketcap.com/currencies/pton/)
    # is not in cryptocompare but is in paprika
    'PTON',
    # Proton (https://coinmarketcap.com/currencies/proton-token/)
    # is not in cryptocompare but is in paprika. Cryptocompare has
    # Pink Taxi Token as PTT.
    'PTT',
    # Pixel (https://coinmarketcap.com/currencies/pixel/)
    # is not in cryptocompare but is in paprika. Cryptocompare hasattr
    # Phalanx as PXL
    'PXL',
    # Rublix (https://coinmarketcap.com/currencies/rublix/)
    # is not in cryptocompare but is in paprika
    'RBLX',
    # Red Token (https://coinmarketcap.com/currencies/red/)
    # is not in cryptocompare but is in paprika
    'RED',
    # Rusgas (https://coinmarketcap.com/currencies/rusgas/)
    # is not in cryptocompare but is in paprika
    'RGS',
    # RemiCoin (https://coinmarketcap.com/currencies/remicoin/)
    # is not in cryptocompare but is in paprika
    'RMC',
    # Rotharium (https://coinmarketcap.com/currencies/rotharium/)
    # is not in cryptocompare but is in paprika
    'RTH',
    # SmartApplicationChain (https://coinmarketcap.com/currencies/smart-application-chain/)
    # is not in cryptocompare but is in paprika
    'SAC',
    # snowball (https://etherscan.io/address/0x198A87b3114143913d4229Fb0f6D4BCb44aa8AFF)
    # is not in cryptocompare but is in paprika
    'SNBL',
    # Soniq (https://coinmarketcap.com/currencies/soniq/)
    # is not in cryptocompare but is in paprika
    'SONIQ',
    # CryptoSoul (https://coinmarketcap.com/currencies/cryptosoul/)
    # is not in cryptocompare but is in paprika
    'SOUL-2',
    # Spin Protocol (https://coinmarketcap.com/currencies/spin-protocol/)
    # is not in cryptocompare but is in paprika
    'SPIN',
    # Staker (https://coinmarketcap.com/currencies/staker/)
    # is not in cryptocompare but is in paprika
    'STR',
    # TigerCash (https://coinmarketcap.com/currencies/tigercash/)
    # is not in cryptocompare but is in paprika
    'TCH',
    # TercetNetwork (https://etherscan.io/address/0x28d7F432d24ba6020d1cbD4f28BEDc5a82F24320)
    # is not in cryptocompare but is in paprika
    'TCNX',
    # Temco (https://coinmarketcap.com/currencies/temco/)
    # is not in cryptocompare but is in paprika
    'TEMCO',
    # ThingsChain (https://coinmarketcap.com/currencies/thingschain/)
    # is not in cryptocompare but is in paprika
    'TIC',
    # Tokok (https://coinmarketcap.com/currencies/tokok/)
    # is not in cryptocompare but is in paprika
    'TOK',
    # Uchain (https://coinmarketcap.com/currencies/uchain/)
    # is not in cryptocompare but is in paprika
    'UCN',
    # Veriblock (https://coinmarketcap.com/currencies/veriblock/)
    # is not in cryptocompare but is in paprika
    'VBK',
    # Bitcoin Card (https://etherscan.io/address/0x9a9bB9b4b11BF8eccff84B58a6CCCCD4058A7f0D)
    # is not in cryptocompare but is in paprika
    'VD',
    # VeriDocGlobal (https://coinmarketcap.com/currencies/veridocglobal/)
    # is not in cryptocompare but is in paprika
    'VDG',
    # Vikky Token (https://coinmarketcap.com/currencies/vikkytoken/)
    # is not in cryptocompare but is in paprika
    'VIKKY',
    # Wibson (https://coinmarketcap.com/currencies/wibson/)
    # is not in cryptocompare but is in paprika
    'WIB',
    # Winchain Token (https://coinmarketcap.com/currencies/wintoken/)
    # is not in cryptocompare but is in paprika
    'WIN',
    # Yggdrash (https://coinmarketcap.com/currencies/yeed/)
    # is not in cryptocompare but is in paprika
    'YEED',
    # ZeusNetwork (https://coinmarketcap.com/currencies/zeusnetwork/)
    # is not in cryptocompare but is in paprika
    'ZEUS',
    # BlockCat (https://coinmarketcap.com/currencies/blockcat/)
    # is not in cryptocompare but is in paprika
    'CAT-2',
)
