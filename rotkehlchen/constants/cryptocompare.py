WORLD_TO_CRYPTOCOMPARE = {
    'DATAcoin': 'DATA',
    'IOTA': 'MIOTA',
    'XRB': 'NANO',
    'AIR-2': 'AIR*',
    # In Rotkehlchen Bitswift is BITS-2 but in cryptocompare it's BITSW
    'BITS-2': 'BITSW',
    # In Rotkehlchen BTM is Bitmark and BTM-2 is Bytom but in
    # Cryptocompare Bytom is BTM and Bitmark is BTMK
    'BTM': 'BTMK',
    'BTM-2': 'BTM',
    # In Rotkehlchen CCN-2 is Cannacoin and CCN is CustomContractNetwork
    'CCN-2': 'CCN',
    # In Rotkehlchen FAIR-2 is FairGame and FAIR is FairCoin, but in
    # cryptocompare FairGame is FAIRG
    'FAIR-2': 'FAIRG',
    # Almosst 100% certain that GPUC (https://coinmarketcap.com/currencies/gpucoin/)
    # is GPU in cryptocompare (https://www.cryptocompare.com/coins/gpu/overview)
    'GPUC': 'GPU',
    # In Rotkehlchen we got 3 coins with KEY symbol. Cryptocompare does not have
    # data for KEY-2
    # KEY -> Selfkey
    # KEY-2 -> KEY
    # KEY-3 -> KeyCoin
    'KEY-3': 'KEYC',
    # In Rotkehlchen KNC is KyberNetwork and KNC-2 is KingN coin. In cryptocompare
    # KNGN is KingN coin
    'KNC-2': 'KNGN',
    # Liquidity network is LQD in Rotkehlchen but LQDN in Cryptocompare
    'LQD': 'LQDN',
    # Monetaverde is as MNV in cryptocompare while it should be MCN
    # https://www.cryptocompare.com/coins/mnv/overview
    'MCN': 'MNV',
    # Marscoin is as MRS in cryptocompare
    # https://www.cryptocompare.com/coins/mrs/overview
    'MARS': 'MRS',
    # Marginless is not in cryptocompare. Asking for MRS will return MARScoin
    'MRS': None,
    # Mazacoin is as MZC in cryptocompare
    'MAZA': 'MZC',
    # NuBits is NBT in cryptocompare
    'USNBT': 'NBT',
    # Polymath is POLY in Rotkehlchen and POLYN in cryptocompare
    'POLY': 'POLYN',
    # Polybit is POLY-2 in Rotkehlchen and POLY in cryptocompare
    'POLY-2': 'POLY',
    # YacCoin is YAC in cryptocompare
    'YACC': 'YAC',
    # GoldCoin is GLD in cryptocompare, but GLC in most other places including Rotkehlcen
    'GLC': 'GLD',
    # In Rotkehlchen we have GlobalCoin as GLC-2. In Cryptocompare it's GLC
    'GLC-2': 'GLC',
    # In Rotkehlchen and everywhere else Bitbean is BITB but in cryptocompare BEAN
    'BITB': 'BEAN',
    # For Rotkehlchen RCN is Ripio Credit Network and RCN-2 is Rcoin
    # Rcoin is RCOIN in cryptocompare
    'RCN-2': 'RCOIN',
    # EDR is Endor Protocol in Rotkehlchen and EPT in cryptocompare
    'EDR': 'EPT',
    # EDR-2 is E-Dinar coin in Rotkehlchen and EDR in cryptocompare
    'EDR-2': 'EDR',
    # SPC is Spacechain in Rotkehlchen but APCC in cryptocompare.
    'SPC': 'APCC',
    # Blocktrade is BTT-2 in Rotkehlchen but BKT in cryptocompare.
    'BTT-2': 'BKT',
    # Ontology gas is ONG in Rotkehlchen but ONGAS in cryptocompare
    'ONG': 'ONGAS',
    # SoMee.Social is ONG-2 in Rotkehlchen but ONG in cryptocompare
    'ONG-2': 'ONG',
    # SLT is Smartlands in Rotkehlchen but SLST in cryptocompare
    'SLT': 'SLST',
    # SLT-2 is Social Lending Network in Rotkehlchen but SLT in cryptocompare
    'SLT-2': 'SLT',
    # PAI is Project Pai in Rotkehlchen but PPAI in cryptocompare
    'PAI': 'PPAI',
    # PAI-2 is PCHAIN in Rotkehlchen but PAI in cryptocompare
    'PAI-2': 'PAI',
    # CMT-2 is CometCoin in Rotkehlchen but CMTC in cryptocompare
    'CMT-2': 'CMTC',
    # GXChain is GXC in Rotkehlcen and GXS in cryptocompare
    'GXC': 'GXS',
    # Harvest Masternode Coin is in HC-2 in Rotkehlchen and HMN in cryptocompare
    'HC-2': 'HMN',
    # For Rotkehlchen HOT is Holochain and HOT-2 is Hydro Protocol
    # But for cryptocompare HOT is Hydro Protocol and HOLO is HoloChain
    'HOT': 'HOLO',
    'HOT-2': 'HOT',
    # For Rotkehlchen YOYO is YOYOW but it's YOYOW in cryptocompare
    'YOYOW': 'YOYOW',
    # For Rotkehlchen 0xBTC is 0xBTC but in cryptocompare it's capitalized
    '0xBTC': '0XBTC',
    # For Rotkehlchen ACC is AdCoin, ACC-2 is ACChain and ACC-3 is Accelerator network
    # In cryptocompare Accelerator Network is ACCN
    'ACC-3': 'ACCN',
    # For Rotkehlchen ARB is Arbitrage coin and ARB-2 is ARbit but in cryptocompare
    # ARBT is arbitrage and ARB is ARbit
    'ARB': 'ARBT',
    'ARB-2': 'ARB',
    # For Rotkehlchen ARC is Advanced Technology Coin (Arctic) and ARC-2 is ArcadeCity
    # In Cryptocompare ARC* is ArcadeCity
    'ARC-2': 'ARC*',
    # For Rotkehlchen ATX is Astoin Coin and ATX-2 is ArtexCoin but in
    # cryptocompare ASTO is Astoin Coin and ATX is ArtexCoin
    'ATX': 'ASTO',
    'ATX-2': 'ATX',
    # For Rotkehlchen AVA is Travala and AVA-2 is Avalon but in
    # cryptocompare AVALA is Travala and AVA is Avalon
    'AVA': 'AVALA',
    'AVA-2': 'AVA',
    # Symbol for B2BX is B2B is cryptocompare so we need to specify it
    'B2BX': 'B2B',
    # For Rotkehlchen BBK is BrickBlock and BBK-2 is Bitblocks but in cryptocompare
    # BrickBlock is XBB and Bitblocks is BBK
    'BBK': 'XBB',
    'BBK-2': 'BBK',
    # For Rotkehlchen BBN is Banyan Network but in cryptocompare it's BNN
    'BBN': 'BNN',
    # For Rotkehlchen BET is Dao.Casino and BET-2 is BetaCoin but in cryptocompare
    # Dao.Casino is DAOC and BetaCoin is BET
    'BET': 'DAOC',
    'BET-2': 'BET',
    # Bollenum (https://coinmarketcap.com/currencies/bolenum/) is BLN
    # in rotkehlchen but BLNM in cryptocompare
    'BLN': 'BLNM',
    # ContentBox (https://coinmarketcap.com/currencies/contentbox/) is BOX-2
    # in rotkehlchen but BOX in cryptocompare
    'BOX-2': 'BOX',
    # Bytether (https://www.cryptocompare.com/coins/byther/overview) is BTH
    # in rotkehlchen but BYTHER in cryptocompare
    'BTH': 'BYTHER',
    # Bither (https://www.cryptocompare.com/coins/btr/overview) is BTR-2
    # in rotkehlchen but BTR in cryptocompare
    'BTR-2': 'BTR',
    # For Rotkehlchen CAN is CanYaCoin and CAN-2 is Content And Ad Network
    # In cryptocompare, it's CAN and CADN
    'CAN-2': 'CADN',
    # For Rotkehlchen CAT is Bitclave and CAT-2 is BlockCAT but in cryptocompare
    # Bitclave is BCAT and BlockCat is not supported
    'CAT': 'BCAT',
    # For Rotkehlchen CET is CoinEX and CET-2 is DiceMoney but in cryptocompare
    # CoinEX is CET and DiceMoney is DICEM
    'CET-2': 'DICEM',
    # For Rotkehlchen COS is Contentos but in cryptocompare it's CONT
    'COS': 'CONT',
    # For Rotkehlchen CPC is CPChain and CPC-2 is CapriCoin but in cryptocompare
    # CPChain is CPCH and CapriCoin is CPC
    'CPC': 'CPCH',
    'CPC-2': 'CPC',
    # For Rotkehlchen CRC is CryCash and CRC-2 is CrowdCoin but in cryptocompare
    # Crycash is CRYC and CrowdCoin is CRC
    'CRC': 'CRYC',
    'CRC-2': 'CRC',
    # For Rotkehlchen CS is Credits but it's CRDTS in cryptocompare
    'CS': 'CRDTS',
    # For Rotkehlchen CTX-2 is CarTaxi but it's CTX in cryptocompare
    'CTX-2': 'CTX',
    # For Rotkehlchen DOW is DOW Coin Chain but it's Dow in cryptocompare
    'DOW': 'Dow',
    # For Rotkehlchen EPY is Emphy Coin but it's EMPH in cryptocompare
    'EPY': 'EMPHY',
    # For Rotkehlchen ERT is Eristica Coin but it's ERIS in cryptocompare
    'ERT': 'ERIS',
    # For Rotkehlchen EVN is Envion and EVN-2 is EvenCoin, but in cryptocompare
    # Evencoin is EVENC
    'EVN-2': 'EVENC',
    # For Rotkehlchen EXC is ExcaliburCoin and EXC-2 is EximChain Token but in
    # cryptocompare EXC is EximChain Token ans ExcaliburCoin is not supported
    'EXC-2': 'EXC',
    # For Rotkehlchen FLX is Bitflux but it's FLX* in cryptocompare
    'FLX': 'FLX*',
    # For Rotkehlchen FORK is ForkCoin and FORK-2 is GastroAdvisor. For
    # cryptocompare only GastroAdvisor exists as FORK.
    'FORK-2': 'FORK',
    # For Rotkehlchen GBX is GoByte and GBX-2 is Globitex but in cryptocompare
    # Globitex is GBXT
    'GBX-2': 'GBXT',
    # For Rotkehlchen GEN is Daostack but it's GENS in cryptocompare
    'GEN': 'GENS',
    # For Rotkehlchen GENE is ParkGene and GENE-2 is Gene Source Code Chain,
    # in cryptocompare GENE-2 is GENE*
    'GENE-2': 'GENE*',
    # For Rotkehlchen GOT is Go Network Token and GOT-2 is ParkinGo, cryptocompare
    # does not have ParkinGO and Go Network Token is GTK
    'GOT': 'GTK',
    # For Rotkehlchen HMC is Hi Mutual Society and HMC-2 is Harmony Coin, in
    # cryptocompare HMC is the same but HMC* is (perhaps) Harmony Coin
    'HMC-2': 'HMC*',
    # For Rotkehlchen INV is Invacio but it's INVC in cryptocompare
    'INV': 'INVC',
    # For Rotkehlchen JOY is Joy but it's JOY* in cryptocompare
    'JOY': 'JOY*',
    # For Rotkehlchen LNC is Blocklancer  and LNC-2 is Linker Coin, but for
    # cryptocompare linker coin is LNKC
    'LNC-2': 'LNKC',
    # For Rotkehlchen LOC is LockTrip but in cryptocompare it's LOCK
    'LOC': 'LOCK',
    # For Rotkehlchen MAN is Matrix AI Network but in cryptocompare it's MXAI
    'MAN': 'MXAI',
    # For Rotkehlchen MDT is Measurable Data Token but in cryptocompare it's MSDT
    'MDT': 'MSDT',
    # For Rotkehlchen MNT is Media Network Token but in cryptocompare it's MNT*
    'MNT': 'MNT*',
    # For Rotkehlchen MRP is MoneyReel but in cryptocompare it's MNRB
    'MRP': 'MNRB',
    # For Rotkehlchen MTC is doc.com Token and MTC-2 is Mesh Network but in
    # cryptocompare Mesh Network is MTCMN
    'MTC-2': 'MTCMN',
    # For Rotkehlchen MTN is Medical Token but it's MDCL in cryptocompare
    'MTN': 'MDCL',
    # For Rotkehlchen OCC-2 is Original Cryptocoin but it's OCC in cryptocompare
    'OCC-2': 'OCC',
    # For Rotkehlchen ORS is OriginSport Token and ORS-2 is ORS group, but in
    # cryptocompare OriginSport Token is OGSP and ORS Group is ORS
    'ORS': 'OGSP',
    'ORS-2': 'ORS',
    # For Rotkehlchen PRE is Presearch but it's SRCH in cryptocompare
    'PRE': 'SRCH',
    # For Rotkehlchen PLA is Plair and PLA-2 is Playchip, but in cryptocompare
    # PLA is Playchip and Plair is PLAI
    'PLA': 'PLAI',
    'PLA-2': 'PLA',
    # For Rotkehlchen RDN is Raiden Network but it's RDNN in cryptocompare
    'RDN': 'RDNN',
    # For Rotkehlchen SKB is SakuraBloom but it's SKRB in cryptocompare
    'SKB': 'SKRB',
    # For Rotkehlchen SKR is SkrillaToken but it's SKR* in cryptocompare
    'SKR': 'SKRT',
    # For Rotkehlchen SMART is SmartCash, and SMART-2 is SmartBillions, but in
    # cryptocompare SmartBillions is SMART*
    'SMART-2': 'SMART*',
    # For Rotkehlchen SOUL is Phantasma and SOUL-2 is CryptoSoul. But cryptocompare
    # only has Phantasma as GOST
    'SOUL': 'GOST',
    # For Rotkehlchen SPD is Spindle and SPD-2 is Stipend, but in cryptocompare
    # Spindle is SPND and Stipend is SPD
    'SPD': 'SPND',
    'SPD-2': 'SPD',
    # For Rotkehlchen SPX is Sp8de Token but it's SPCIE in cryptocompare
    'SPX': 'SPCIE',
    # For Rotkehlchen STRC is Star Credits but it's SRC* in cryptocompare
    'STRC': 'SRC*',
    # For Rotkehlchen TCH is ThoreCash and TCH-2 is TigerCash but cryptocompare
    # only has TigerCash as TCH
    'TCH-2': 'TCH',
    # For Rotkehlchen TEAM is TokenStars Team but cryptocompare has it as TEAMT
    'TEAM': 'TEAMT',
    # For Rotkehlchen VSF is Verisafe but it's CPLO in cryptocompare (the old name)
    'VSF': 'CPLO',
    # For Rotkehlchen WEB is Webcoin and WEB-2 Webchain, but in cryptocompare
    # Webchain is WEBC
    'WEB-2': 'WEBC',
    # For Rotkehlchen WIN is Winchain Token and WIN-2 WCoin, but in cryptocompare
    # Wcoin is WIN and there is no Winchain Token
    'WIN-2': 'WIN',
    # For Rotkehlchen BlitzPredict is XBP  but it's BPX in cryptocompare
    'XBP': 'BPX',
    # For Cryptocompare PHX has not been updated to PHB
    'PHB': 'PHX',
}

# TODO: For the ones missing from cryptocompare make sure to also
# disallow price queries to cryptocompare for these assets
KNOWN_TO_MISS_FROM_CRYPTOCOMPARE = (
    # This is just kraken's internal fee token
    'KFEE',
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
    # LUNA Terra (https://coinmarketcap.com/currencies/terra/)
    # is not in cryptocompare but is in paprika
    'LUNA-2',
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
