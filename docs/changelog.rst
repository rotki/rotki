=========
Changelog
=========

* :bug:`1846` AMPL token balance should no longer be double counted

* :release:`1.9.1 <2020-11-29>`
* :feature:`1716` Rotki can now also query data from the following ethereum open nodes:
  - 1inch
  - my ether walet
  - cloudflare-eth
  - linkpool
* :bug:`1777` Free users will now be able to load uniswap LP balances properly again.
* :bug:`1726` When querying Compound history for COMP claimed around the start of COMP issuance, zero price warnings should no longer be emitted.
* :feature:`1804` Premium users: Eth2 staking balances (along with what is gained via staking) will now be shown along with an APR estimation of the gains by staking. 
* :feature:`369` Users can now import multiple addresses at once.
* :feature:`-` Users can now select predefined display date ranges for the premium statistics.
* :bug:`1801` Users that have the uniswap module deactivated will now see a proper message about the module status instead of a loading page.
* :bug:`1798` Log level settings now are properly saved and the users are not required to set them on every run.
* :bug:`1785` Inform the user when they try to setup Bittrex with their system clock not in sync.
* :bug:`1761` Retry GraphQL requests when the API server fails.
* :bug:`1809` Token balances should now always be saved in the balances snapshot. Also an edge case that rarely caused the ethereum balances to be queried twice should be now fixed.
* :bug:`1803` After 25/11/2020 Compound's claimable COMP stopped appearing in the app due to a change in a smart contract we depend on. This has now been fixed and they should be detected properly again.
* :bug:`1416` Request Binance deposits & withdraws using a 90 days window.
* :bug:`1787` After 24/11/2020 some Infura users started getting a "query returned more than 10000 results" error when querying their balances. This should no longer happen.
* :feature:`1774` Users now will only see the dashboard liabilities if there are liabilities to show.
* :feature:`1745` Users can now delete multiple blockchain accounts at once.
* :bug:`1778` Uniswap pool balances will now only be loaded when the user navigates to the Liquidity pools screen.

* :feature:`-` Added support for the following tokens:

  - `renBCH (renBCH) <https://www.coingecko.com/en/coins/renbch>`__
  - `renZEC (renZEC) <https://www.coingecko.com/en/coins/renzec>`__
  - `Swerve.fi DAI/USDC/USDT/TUSD (swUSD) <https://www.coingecko.com/en/coins/swusd>`__
  - `Golem (GLM) <https://www.coingecko.com/en/coins/golem>`__
  - `Hegic (HEGIC) <https://www.coingecko.com/en/coins/hegic>`__
  - `Prometeus (PROM) <https://www.coingecko.com/en/coins/prometeus>`__
  - `88mph (MPH) <https://www.coingecko.com/en/coins/88mph>`__
  - `zLOT (ZLOT) <https://www.coingecko.com/en/coins/zlot>`__
  - `tBTC (TBTC) <https://www.coingecko.com/en/coins/tbtc>`__
  - `Cornichon (CORN) <https://www.coingecko.com/en/coins/cornichon>`__

* :release:`1.9.0 <2020-11-20>`
* :feature:`717` Uniswap v2 LP balances are now detected by Rotki. Faster balance queries, swaps history and LP events history is also supported for premium users. Finally uniswap trades are now taken into account in the profit/loss report for premium users.
* :bug:`1664` Properly convert the given xpub to ypub if P2SH_P2WPKH and zpub if WPKH. This should address the problem of importing some types of xpubs for some users.
* :bug:`1740` SNX token and some other token balances should no longer be double counted.
* :feature:`1724` YFI and BAL are now supported as collateral for makerdao vaults.
* :feature:`1694` Users are now able to track their ETH deposited in Eth2 beacon chain. Premium users can see more details about the activity and their staking gains in the staking menu.
* :feature:`1660` Users will now be able to see and edit labels and tags for xpub addresses.
* :feature:`1227` Users can now see a net worth graph on the dashboard.
* :feature:`1400` Liabilities are now shown on the dashboard and subtracted from the total net value.
* :bug:`1668` Refreshing BTC balances now, will not clear any other assets from the state.
* :bug:`1669` Users will now see a loading indicator when balances are loading and proper non-zero values after loading.
* :bug:`1678` Selected type will now not be ignored, when adding an xpub that already contains an x/y/zpub prefix.
* :bug:`1686` Compound historical interest profit is now shown correctly if theuser still has assets locked in compound.
* :feature:`1414` Users will now be shown only the available locations when filtering trades.

* :feature:`-` Added support for the following tokens:

  - `Synthetix sBTC (sBTC) <https://www.coingecko.com/en/coins/sbtc>`__
  - `Synthetix sETH (sETH) <https://www.coingecko.com/en/coins/seth>`__
  - `Synthetix sLINK (sLINK) <https://www.coingecko.com/en/coins/slink>`__
  - `Synthetix sXAU (sXAU) <https://www.coingecko.com/en/coins/sxau>`__
  - `Synthetix sXAG (sXAG) <https://www.coingecko.com/en/coins/sxag>`__
  - `Synthetix iBTC (iBTC) <https://www.coingecko.com/en/coins/ibtc>`__
  - `Synthetix iETH (iETH) <https://www.coingecko.com/en/coins/ieth>`__
  - `Aave Interest bearing Uniswap (aUNI) <https://etherscan.io/address/0xB124541127A0A657f056D9Dd06188c4F1b0e5aab>`__
  - `Blockstack (STX) <https://www.coingecko.com/en/coins/blockstack>`__
  - `Axie Infinity Shard (AXS) <https://www.coingecko.com/en/coins/axie-infinity>`__
  - `Bitcoin ABC (BCHA) <https://www.coingecko.com/en/coins/bitcoin-cash-abc>`__
  - `Binance leveraged token BCHDOWN (BCHDOWN) <https://www.cryptocompare.com/coins/bchdown/overview>`__
  - `Binance leveraged token BCHUP (BCHUP) <https://www.cryptocompare.com/coins/bchup/overview>`__
  - `Frontier Token (FRONT) <https://www.coingecko.com/en/coins/frontier>`__
  - `HARD Protocol (HARD) <https://www.coingecko.com/en/coins/hard-protocol>`__
  - `Keep3rV1 (KP3R) <https://www.coingecko.com/en/coins/keep3rv1>`__
  - `Oasis Network (ROSE) <https://www.coingecko.com/en/coins/oasis-network>`__
  - `Small Love Potion (SLP) <https://www.coingecko.com/en/coins/small-love-potion>`__
  - `Stratis (STRAX) <https://www.coingecko.com/en/coins/stratis>`__
  - `Unifi Protocol DAO (UNFI) <https://www.coingecko.com/en/coins/unifi-protocol-dao>`__
  - `Akoin (AKN) <https://www.coingecko.com/en/coins/akoin>`__
  - `Camp (CAMP) <https://www.cryptocompare.com/coins/camp/overview>`__
  - `Gleec Coin (GLEEC) <https://www.coingecko.com/en/coins/gleec-coin>`__
  - `NerveNetwork (NVT) <https://www.coingecko.com/en/coins/nervenetwork>`__
  - `ShareToken (SHR) <https://www.coingecko.com/en/coins/sharetoken>`__

* :release:`1.8.3 <2020-10-30>`
* :bug:`1636` Users running earlier OSX versions than Catalina can again start the application properly.
* :bug:`1635` Application will now continue running when changing log level on Windows.
* :feature:`1642` Force pull/push buttons for premium sync are now accessible in the floppy disk icon on the toolbar.
* :bug:`1639` Native segwit xpubs will now properly query and display the balances of their derived addresses. Rotki switched to using blockstream's API instead of blockcypher for native segwit addresses.
* :bug:`1638` Balances displayed in dashboard cards should now be properly sorted by value in descending order.
* :bug:`-` If the DB has not been uploaded in this run of Rotki, the last upload time indicator now shows the last time data was uploaded and not "Never".
* :bug:`1641` Rotki only accepts derivation paths in the form of m/X/Y/Z... where ``X``, ``Y`` and ``Z`` are integers. Anything else is not processable and invalid. We now check that the given path is valid and reject the addition if not. Also the DB is upgraded and any xpubs with such invalid derivation path are automatically deleted.
* :bug:`1637` Loading ethereum transactions on the UI should work properly again now

* :feature:`-` Added support for the following tokens:

  - `Compound Collateral (cCOMP) <https://www.coingecko.com/en/coins/ccomp>`__
  - `Certik (CTK) <https://www.coingecko.com/en/coins/certik>`__
  - `Bounce Token (BOT) <https://www.coingecko.com/en/coins/bounce-token>`__

* :release:`1.8.2 <2020-10-27>`
* :bug:`1631` Fetching poloniex trades will now work properly again after they changed their trade date time format.
* :feature:`-` Support the following new MakerDAO vault collateral types: ``ETH-B``, ``USDT-A``, ``MANA-A``, ``PAXUSD-A``, ``COMP-A``, ``LRC-A``, ``LINK-A``.
* :feature:`1616` Support https://harvest.finance/ stablecoin vaults balance queries and claimable FARM token balance display.
* :feature:`1456` Take balances shown in DeFi overview into account in the total netvalue worth and in the dashboard and per account ethereum balances table.
* :feature:`1561` The application will now only log critical errors by default, allowing the user to change that on the log in screen.
* :feature:`1562` Add support for P2SH-P2WPKH and WPKH type of xPubs. User can now choose the xpub type when inputting from the UI.
* :bug:`1583` Users will not be taken to the reveal button when pressing tab in a form with a revealable input.
* :feature:`1122` Users can now import their metamask account addresses to rotki.
* :feature:`1458` Aave borrowing and liquidations are now also taken into account and displayed to the user. Also for historical aave queries a subgraph is used instead of blockchain event querying which makes the entire process considerably faster.
* :feature:`1194` Premium users can now manually backup or restore their databases.
* :bug:`1596` If the local DB of a premium user is both newer and bigger size than the remote, then do not ask the user whether to pull the remote DB or not.
* :feature:`1288` Users can now see the last premium database sync date in the save indicator when database sync is enabled.
* :bug:`1571` New user account with new premium keys will no longer fail to create an account the first time if premium keys are given at account creation time.
* :bug:`1559` Users can now properly refresh the blockchain balances in the Accounts & Balances page.
* :bug:`1564` Blockchain balances are now properly sorted by fiat currency value.
* :bug:`1558` Deleting an xPub that has no used derived addresses is now possible.
* :feature:`1560` Users can now see the total value of the accounts under an xpub.
* :feature:`-` Added support for the following tokens:

  - `Based Money ($BASED) <https://www.coingecko.com/en/coins/based-money>`__
  - `Filecoin (FIL) <https://www.coingecko.com/en/coins/filecoin>`__
  - `DefiPulse Index (DPI) <https://www.coingecko.com/en/coins/defipulse-index>`__
  - `renBTC (renBTC) <https://www.coingecko.com/en/coins/renbtc>`__
  - `Jarvis Reward Token (JRT) <https://www.coingecko.com/en/coins/jarvis-reward-token>`__
  - `Alpha Finance (ALPHA) <https://www.coingecko.com/en/coins/alpha-finance>`__
  - `Near Protocol (NEAR) <https://www.coingecko.com/en/coins/near>`__
  - `Venus (XVS) <https://www.coingecko.com/en/coins/venus>`__
  - `3x Short Cardano Token (ADABEAR) <https://www.coingecko.com/en/coins/3x-short-cardano-token>`__
  - `3x Long Cardano Token (ADABULL) <https://www.coingecko.com/en/coins/3x-long-cardano-token>`__
  - `DefiChain (DFI) <https://www.coingecko.com/en/coins/defichain>`__
  - `Ducato Protocol Token (DUCATO) <https://www.coingecko.com/en/coins/ducato-protocol-token>`__
  - `Consensus Cell Network (ECELL) <https://www.coingecko.com/en/coins/consensus-cell-network>`__
  - `Maro (MARO) <https://www.coingecko.com/en/coins/maro>`__
  - `Harvest Finance (FARM) <https://www.coingecko.com/en/coins/harvest-finance>`__
  - `PieDAO DOUGH v2 (DOUGH) <https://www.coingecko.com/en/coins/piedao-dough-v2>`__
  - `All Harvest finance stablecoin vault fAssets <https://github.com/harvest-finance/harvest#vaults>`__
  - `PickleToken (PICKLE) <https://www.coingecko.com/en/coins/pickle-finance>`__
  - `Curve.fi DAI/USDC/USDT Pool (3Crv) <https://etherscan.io/address/0x6c3f90f043a72fa612cbac8115ee7e52bde6e490>`__
  - `Curve.fi GUSD/3Crv (gusd3CRV) <https://etherscan.io/address/0xD2967f45c4f384DEEa880F807Be904762a3DeA07>`__
  - `Yearn Gemini USD vault (yGUSD) <https://etherscan.io/address/0xec0d8D3ED5477106c6D4ea27D90a60e594693C90>`__
  - `yearn Curve.fi DAI/USDC/USDT vault (y3Crv) <https://etherscan.io/address/0x9cA85572E6A3EbF24dEDd195623F188735A5179f>`__
  - `mStable USD (mUSD) <https://www.coingecko.com/en/coins/mstable-usd>`__
  - `Aave Interest bearing Aave Token (aAAVE) <https://etherscan.io/address/0xba3d9687cf50fe253cd2e1cfeede1d6787344ed5>`__
  - `Bidao (BID) <https://www.coingecko.com/en/coins/bidao>`__
  - `Audius (AUDIO) <https://www.coingecko.com/en/coins/audius>`__
  - `Easyfi (EASY) <https://www.coingecko.com/en/coins/easyfi>`__
  - `Binance leveraged token FILDOWN (FILDOWN) <https://www.cryptocompare.com/coins/fildown>`__
  - `Binance leveraged token FILUP (FILUP) <https://www.cryptocompare.com/coins/filup/>`__
  - `Binance leveraged token YFIDOWN (YFIDOWN) <https://www.cryptocompare.com/coins/yfidown>`__
  - `Binance leveraged token YFIUP (YFIUP) <https://www.cryptocompare.com/coins/yfiup/>`__
  - `Injective Token (INJ) <https://www.coingecko.com/en/coins/injective-protocol>`__
  - `Celo dollar (CUSD) <https://www.cryptocompare.com/coins/celousd/overview>`__
  - `Elastos (ELA) <https://www.coingecko.com/en/coins/elastos>`__
  - `KardiaChain Token (KAI) <https://www.coingecko.com/en/coins/kardiachain>`__

* :release:`1.8.1 <2020-10-05>`
* :feature:`1532` Users can now easily open links to external block explorers for their tracked blockchain addresses.
* :bug:`1530` Truncation of account addresses will now dynamically change based on the screen width.
* :feature:`224` Coingecko is now used for current price queries if cryptocompare fails. This will allow more tokens to be displayed.
* :feature:`1523` Trailing or leading whitespace in pasted addresses and api keys will now be properly removed.
* :feature:`1501` Assets that have been added to the ignore list will now be hidden from the dashboard.
* :bug:`1533` Premium Yearn vaults users should now be able to see a USD PNL per vault they used during the tax report.
* :bug:`1527` Premium Compound users should no longer get an exception during tax report.
* :feature:`808` Bitcoin xpubs are now supported. Given an xpub rotki derives all addresses locally and tracks those that have been used without compromising user privacy.

* :feature:`-` Added support for the following tokens:

  - `Compound Uni (cUNI) <https://www.coingecko.com/en/coins/compound-uniswap>`__
  - `YAMv3 (YAM) <https://www.coingecko.com/en/coins/yam>`__
  - `Avalanche (AVAX) <https://www.coingecko.com/en/coins/avalanche>`__
  - `BakeryToken (BAKE) <https://www.coingecko.com/en/coins/bakerytoken>`__
  - `Burger Swap (BURGER) <https://www.coingecko.com/en/coins/burger-swap>`__
  - `Pancake Swap (CAKE) <https://www.coingecko.com/en/coins/pancakeswap>`__
  - `Flamingo Finance (FLM) <https://www.coingecko.com/en/coins/flamingo-finance>`__
  - `Helium (HNT) <https://www.coingecko.com/en/coins/helium>`__
  - `New Bitshares (NBS) <https://www.coingecko.com/en/coins/new-bitshares>`__
  - `Sun Token (SUN) <https://www.coingecko.com/en/coins/sun-token>`__
  - `CBDao (BREE) <https://www.coingecko.com/en/coins/cbdao>`__
  - `Concentrated Voting Power (CVP) <https://www.coingecko.com/en/coins/powerpool-concentrated-voting-power>`__
  - `dHedge DAO Token (DHT) <https://www.coingecko.com/en/coins/dhedge-dao>`__
  - `Aavegotchi (GHST) <https://www.coingecko.com/en/coins/aavegotchi>`__
  - `Moji Experience Points (MEXP) <https://www.coingecko.com/en/coins/moji-experience-points>`__
  - `Polkastarter (POLS) <https://www.coingecko.com/en/coins/polkastarter>`__
  - `Rarible (RARI) <https://www.coingecko.com/en/coins/rarible>`__
  - `Rio DeFi (RFUEL) <https://www.coingecko.com/en/coins/rio-defi>`__
  - `Value Liquidity (VALUE) <https://www.coingecko.com/en/coins/value-liquidity>`__
  - `Beowulf (BWF) <https://www.coingecko.com/en/coins/beowulf>`__
  - `GSTCoin (GST) <https://www.coingecko.com/en/coins/gstcoin>`__
  - `Keep Token (KEEP) <https://www.coingecko.com/en/coins/keep-network>`__
  - `Aave Token (AAVE) <https://www.coingecko.com/en/coins/aave>`__

* :release:`1.8.0 <2020-09-23>`
* :feature:`1498` Users can now select the protocol(s) when resetting the DeFi history cache.
* :bug:`1504` Users can now properly start the application when the default backend port is used by another application.
* :feature:`1502` Add support for Binance lending assets.
* :feature:`1402` Yearn vaults historical data and total profit/loss per vault is now available. Also the ROI since inception is now visible next to each vault.
* :bug:`1491` All aave historical events should now be properly returned. Not only interest events.
* :bug:`1482` Use binance api server time to avoid clock skew error with the signatures
* :feature:`-` Users can now easily copy the address from the blockchain account view.
* :bug:`1453` Users will now see an validation error message when attempting to add an existing account.
* :feature:`804` Users can now track borrowing from Compound in the DeFi borrowing page.
* :feature:`597` Users can now track the interest earned by Compound loans in the DeFi lending page.
* :bug:`1462` ycrvRenWSBTC vault token should now properly appear in the dashboard and have its price calculated correctly.
* :bug:`1429` Pool together's plDAI and plUSDC are now correctly shown in the DeFi overview page.
* :bug:`1423` Fiat amounts in protocols details in the DeFi Overview are now correctly converted to the user's profit currency.
* :bug:`1430` Users can now delete manual balance entries where the label is an empty string.
* :feature:`1199` Users can now see the currency symbol next to the value for fiat currencies displayed in the UI.
* :feature:`1415` The navigation drawer has been re-ordered for better usability (the most-used pages have been floated up, and least-used moved to the bottom), and its icons have been updated to use Material Design Icons.
* :feature:`-` Added support for the following tokens:

  - `SushiToken (SUSHI) <https://www.coingecko.com/en/coins/sushi>`__
  - `Trustlines Network Token (TLN) <https://www.coingecko.com/en/coins/trustline-network>`__
  - `Uniswap (UNI) <https://www.coingecko.com/en/coins/uniswap>`__
  - `Crypto is Everywhere Around Me (CREAM) <https://www.coingecko.com/en/coins/cream>`__
  - `Bella Protocol (BEL) <https://www.coingecko.com/en/coins/bella-protocol>`__
  - `Elrond (EGLD) <https://www.coingecko.com/en/coins/elrond>`__
  - `Swerve DAO Token (SWRV) <https://www.coingecko.com/en/coins/swerve>`__
  - `Wing Finance (WING) <https://www.coingecko.com/en/coins/wing-finance>`__
  - `Akropolis Delphi (ADEL) <https://www.coingecko.com/en/coins/akropolis-delphi>`__
  - `AlphaLink (ANK) <https://www.coingecko.com/en/coins/alphalink>`__
  - `Corn (CORN) <https://www.coingecko.com/en/coins/corn>`__
  - `Salmon (SAL) <https://www.coingecko.com/en/coins/salmon>`__
  - `Carrot Finance (CRT) <https://www.coingecko.com/en/coins/carr-finance>`__
  - `FalconSwap Token (FSW) <https://www.coingecko.com/en/coins/falconswap>`__
  - `Unification (FUND) <https://www.coingecko.com/en/coins/unification>`__
  - `Hedget (HGET) <https://www.coingecko.com/en/coins/hedget>`__
  - `JackPool.Finance (JFI) <https://www.coingecko.com/en/coins/jackpool-finance>`__
  - `Pearl Finance (PEARL) <https://www.coingecko.com/en/coins/pearl-finance>`__
  - `tBridge Token (TAI) <https://www.coingecko.com/en/coins/tbridge-token>`__
  - `YF Link (YFL) <https://www.coingecko.com/en/coins/yf-link>`__
  - `YFValue (YFV) <https://www.coingecko.com/en/coins/yfvalue>`__
  - `Klaytn (KLAY) <https://www.coingecko.com/en/coins/klay>`__
  - `Klever (KLV) <https://www.coingecko.com/en/coins/klever>`__
  - `TerraKRW (KRT) <https://www.coingecko.com/en/coins/terra-krw>`__
  - `Latamcash (LMCH) <https://www.coingecko.com/en/coins/latamcash>`__
  - `Ravencoin Classic (RVC) <https://www.coingecko.com/en/coins/ravencoin-classic>`__
  - `Terra SDT (SDT) <https://www.coingecko.com/en/coins/terra-sdt>`__
  - `BiLira (TRYB) <https://www.coingecko.com/en/coins/bilira>`__
  - `Neutrino Dollar (USDN) <https://www.coingecko.com/en/coins/neutrino-dollar>`__
  - `Terra USD (UST) <https://www.cryptocompare.com/coins/ust/overview>`__
  - `Anyswap (ANY) <https://www.coingecko.com/en/coins/anyswap>`__
  - `Chi Gastoken (CHI) <https://www.coingecko.com/en/coins/chi-gastoken>`__
  - `Trump Wins Token (TRUMPWIN) <https://www.coingecko.com/en/coins/trump-wins-token>`__
  - `Trump Loses Token (TRUMPLOSE) <https://www.coingecko.com/en/coins/trump-loses-token>`__
  - `Binance leveraged token DOTDOWN (DOTDOWN) <https://www.cryptocompare.com/coins/dotdown>`__
  - `Binance leveraged token DOTUP (DOTUP) <https://www.cryptocompare.com/coins/dotup/>`__
  - `Binance leveraged token EOSDOWN (EOSDOWN) <https://www.cryptocompare.com/coins/eosdown>`__
  - `Binance leveraged token EOSUP (EOSUP) <https://www.cryptocompare.com/coins/eosup/>`__
  - `Binance leveraged token LTCDOWN (LTCDOWN) <https://www.cryptocompare.com/coins/ltcdown>`__
  - `Binance leveraged token LTCUP (LTCUP) <https://www.cryptocompare.com/coins/ltcup/>`__
  - `Binance leveraged token TRXDOWN (TRXDOWN) <https://www.cryptocompare.com/coins/trxdown>`__
  - `Binance leveraged token TRXUP (TRXUP) <https://www.cryptocompare.com/coins/trxup/>`__
  - `Binance leveraged token XRPDOWN (XRPDOWN) <https://www.cryptocompare.com/coins/xrpdown>`__
  - `Binance leveraged token XRPUP (XRPUP) <https://www.cryptocompare.com/coins/xrpup/>`__

* :release:`1.7.0 <2020-09-01>`
* :feature:`1092` Users can now refresh their manual balance entries.
* :feature:`1031` Users can now view their ethereum transactions in the history page.
* :feature:`1378` Support new OCEAN protocol token after token swap
* :feature:`1336` Balance of any of the user accounts in either yearn finance vaults or curve finance pools should now be auto-detected and displayed both in the dashboard and in the DeFi overview.
* :bug:`1393` When users set the "crypto to crypto trades" setting off, they will no longer see the USD equivalent part of crypto to crypto buys in the tax report history.
* :feature:`1085` Users can now view their exchange trades, along with there deposit and withdraw actions on the connected exchanges.
* :bug:`1321` CSV export formulas have now been fixed and should properly calculate profit/loss per different action type.
* :feature:`-` Add support for New Zealand Dollar (NZD) as a fiat currency
* :feature:`-` Add support for Brazilian Real (BRL) as a fiat currency
* :feature:`-` Rotki users can now import data from their Crypto.com mobile application. For more information go to the data import component of Rotki.
* :feature:`1361` Users of Rotki will now no longer need to wait until the next version is available to be able to access the newly supported assets. Rotki will pull newly available supported assets directly from Github.
* :bug:`1352` Defi cached state should now properly reset when an account is added or deleted.
* :bug:`1329` If aave historical data is queried in quick succession a UNIQUE constraint error will no longer be generated.
* :feature:`840` Add a new notification UI. Backend errors should now display a notification on the upper right corner.
* :feature:`983` The asset icons that are displayed in the rotki frontend have been revamped. We are now pulling icon data from coingecko so a lot more token/asset icons should be visible and up to date.
* :feature:`1235` Numerical displays can now be customized. Users can choose the thousands, the decimals separator. and the position of the currency symbol.
* :feature:`1186` Add tooltips to all app bar buttons (except drawer button)
* :bug:`1226` Fix "Get Rotki Premium" menu button on macOS
* :feature:`-` Added support for the following tokens:

  - `YAM (YAM) <https://coinmarketcap.com/currencies/yam/>`__
  - `YAMv2 (YAMv2) <https://www.coingecko.com/en/coins/yam-v2>`__
  - `Serum (SRM) <https://coinmarketcap.com/currencies/serum/>`__
  - `Orion Protocol (ORN) <https://www.coingecko.com/en/coins/orion-protocol>`__
  - `Polkadot (DOT) <https://coinmarketcap.com/currencies/polkadot-new/>`__
  - `Curve DAO Token (CRV) <https://www.coingecko.com/en/coins/curve-dao-token>`__
  - `DIAToken (DIA) <https://coinmarketcap.com/currencies/dia-data/>`__
  - `Binance leveraged token BNBDOWN (BNBDOWN) <https://www.cryptocompare.com/coins/bnbdown/>`__
  - `Binance leveraged token BNBUP (BNBUP) <https://www.cryptocompare.com/coins/bnbup/>`__
  - `Binance leveraged token XTZDOWN (XTZDOWN) <https://www.cryptocompare.com/coins/xtzdown/>`__
  - `Binance leveraged token XTZUP (XTZUP) <https://www.cryptocompare.com/coins/xtzup/>`__
  - `Reserve Rights (RSR) <https://www.coingecko.com/en/coins/reserve-rights-token>`__
  - `The Sandbox (SAND) <https://www.coingecko.com/en/coins/sand>`__
  - `Tellor Tributes (TRB) <https://www.coingecko.com/en/coins/tellor>`__
  - `Nexus Mutual (NXM) <https://www.coingecko.com/en/coins/nxm>`__
  - `Wrapped Nexus Mutual (wNXM) <https://www.coingecko.com/en/coins/wrapped-nxm>`__
  - `Blocery Token (BLY) <https://www.coingecko.com/en/coins/blocery>`__
  - `DEXTools (DEXT) <https://www.coingecko.com/en/coins/dextools>`__
  - `DMM: Governance Token (DMG) <https://www.coingecko.com/en/coins/dmm-governance>`__
  - `DOS Network Token (DOS) <https://www.coingecko.com/en/coins/dos-network>`__
  - `Geeq (GEEQ) <https://www.coingecko.com/en/coins/geeq>`__
  - `MCDext Token (MCB) <https://www.coingecko.com/en/coins/mcdex>`__
  - `Mantra DAO (OM) <https://www.coingecko.com/en/coins/mantra-dao>`__
  - `PeerEx Network (PERX) <https://www.coingecko.com/en/coins/peerex-network>`__
  - `Parsiq Token (PRQ) <https://www.coingecko.com/en/coins/parsiq>`__
  - `Synthetic CBDAO (SBREE) <https://www.coingecko.com/en/coins/cbdao>`__
  - `Swingby (SWINGBY) <https://www.coingecko.com/en/coins/swingby>`__
  - `Cache Gold Token (CGT) <https://www.coingecko.com/en/coins/cache-gold>`__
  - `Centric (CNS) <https://www.coingecko.com/en/coins/centric>`__
  - `Sensorium (SENSO) <https://www.coingecko.com/en/coins/senso>`__
  - `Aave interest bearing YFI (aYFI) <https://etherscan.io/tx/0x259efe3b78bda8cf736a4afb30654d2e365cb42dc2cbe1fa8c64137673d848fd>`__
  - `Ampleforth (AMPL) <https://www.coingecko.com/en/coins/ampleforth>`__
  - `YFII.finance (YFII) <https://www.coingecko.com/en/coins/dfi-money>`__

* :release:`1.6.2 <2020-08-11>`
* :bug:`1311` When user logs out the app bar is no longer visible.
* :feature:`1303` User can now purge cached ethereum transactions and exchange data (deposits/withdrawals/trades). The next time data is fetched, the respective source will be queried to repopulate the local database cache. This might take some time depending on the amount of entries that will be queried.
* :feature:`1265` Removed fiat balance tracking as it was unnecessary. All fiat balances have now been migrated to manually tracked balances. Each fiat balance entry you had is now migrated to a corresponding manually tracked entry with location being "bank". As an example if you had 1500 EUR Fiat balance entry you will now have a manually tracked balance entry with 1500 EUR called "My EUR bank" and having a location bank.
* :bug:`1298` Fix an issue where it was not possible to add a new manual balances after editing one.
* :bug:`1243` Fix a problem where the "Get Premium" menu entry would not disappear without restarting the application.
* :feature:`1201` Changing the password when premium sync is enabled, will now display a warning to users about the change affecting synced instances.
* :feature:`1178` Users can now select which accounts they want to track for the activated defi modules. If none are selected all accounts are queried.
* :feature:`1084` Users can now select which of the available defi modules they want to activate.
* :bug:`1285` Properly track SNX tokens by pointing to the `migrated <https://blog.synthetix.io/proxy-contract-cutover-on-may-10/`__ proxy contract
* :feature:`820` Multiple open ethereum nodes will be now also queried along with your own ethereum node or etherscan. But in smaller frequency so as not to spam those services. The additional nodes Rotki now queries are:
  - MyCrypto
  - Blockscout
  - Avado pool
* :feature:`1213` Taxable actions table in the tax report and in the CSV exports now include a location.
* :bug:`1249` Fix some amounts not being converted to user's main currency correctly (two components were affected: Account Asset Balances in Accounts & Balances, and the AssetBalances component which was used in both Blockchain Balances as well as Exchange Balances sub-pages that showed totals across an asset).
* :bug:`1247` Fix glitchy autocomplete component usage which caused select menus to not open properly if the "dropdown arrows" were clicked. This has fixed the following select menus throughout the app: Asset Select, Tag Input and Tag Filter, Owned Tokens.
* :bug:`1234` Bittrex history can now be properly queried again. Rotki uses bittrex v3 API from now and on.
* :bug:`-` ALQO historical price queries should now work properly again. Cryptocompare changed the mapping to XLQ and Rotki had to adjust.
* :feature:`-` Added support for the following tokens

  - `UMA (UMA) <https://coinmarketcap.com/currencies/uma/>`__
  - `Ocean Protocol (OCEAN) <https://coinmarketcap.com/currencies/ocean-protocol/>`__
  - `Kusama (KSM) <https://coinmarketcap.com/currencies/kusama/>`__
  - `Pirl (PIRL) <https://coinmarketcap.com/currencies/pirl/>`__
  - `Synth sUSD (sUSD) <https://coinmarketcap.com/currencies/susd/>`__
  - `FIO Protocol (FIO) <https://coinmarketcap.com/currencies/fio-protocol/>`__
  - `THORChain (RUNE) <https://coinmarketcap.com/currencies/thorchain/>`__
  - `Suterusu (SUTER) <https://coinmarketcap.com/currencies/suterusu/>`__
  - `Darico Ecosystem Coin (DEC) <https://coinmarketcap.com/currencies/darcio-ecosystem-coin/>`__
  - `Decentr (DEC) <https://coinmarketcap.com/currencies/decentr/>`__
  - `Plutus DeFi (PLT) <https://coinmarketcap.com/currencies/plutusdefi/>`__
  - `Darwinia Network (RING) <https://coinmarketcap.com/currencies/darwinia-network/>`__
  - `TrustSwap (SWAP) <https://coinmarketcap.com/currencies/trustswap/>`__
  - `SUKU (SUKU) <https://coinmarketcap.com/currencies/suku/>`__
  - `Tendies (TEND) <https://coinmarketcap.com/currencies/tendies/>`__
  - `Unitrade (TRADE) <https://coinmarketcap.com/currencies/unitrade/>`__
  - `Augur v2 (REPV2) <https://www.augur.net/blog/v2-launch/>`__


* :release:`1.6.1 <2020-07-25>`
* :bug:`1202` The Linux Rotki Appimage binary works properly again for Ubuntu <= 18.04. Rotki v1.6.0 was not able to run in those Ubuntu versions.
* :bug:`1203` The selected tab in Accounts & Balances is now readable again.
* :bug:`1172` Fix the ethereum addresses for ``CHAI`` and ``cUSDT`` token.

* :release:`1.6.0 <2020-07-23>`
* :bug:`1072` Tax report progress report percentage should now work properly and negative numbers should no longer appear.
* :feature:`921` A new DeFi overview component is added. There the user can get an overview of all their balances across all DeFi protocols. For protocols that are supported further the user can click and be taken to the protocol specific page to see more details and historical accounting for that protocol.
* :feature:`1160` The Accounts & Balances page layout has been updated to increase usability. It is now split across three sub-pages: Blockchain Balances, Exchange Balances, Manual Balances (includes Fiat Balances). Exchange Balances is a new page where you will be able to see all of your asset balances for each connected exchange (previously this was only accessible from the Dashboard by clicking on an exchange).
* :bug:`1140` The Accounts column in "Blockhain Balances" is now correctly sorted by label (if it exists) or the account address.
* :bug:`1154` Tag filtering in "Manual Balances" within Accounts & Balances now works correctly if any balances do not have any tags assigned.
* :bug:`1155` Fix the cryptocompate price queries of LUNA Terra
* :bug:`1151` Fix for bittrex users so that if bittrex returns dates without a millisecond component Rotki can still parse them properly.
* :feature:`1105` Rotki now uses a standard compliant directory per OS to store user data. If the directory does not exist it is created and at the same time the old directory is migrated by copying it to the new one. The new directories per OS are:
  - Linux: ``~/.local/share/rotki/data``
  - OSX: ``~/Library/Application Support/rotki/data``
  - Windows: ``%LOCALAPPDATA%/rotki/data``
* :feature:`1004` Aave Lending is now supported. Users can see their deposited balance for lending, the borrowed balances and the respective APY/APR. Premium users can also retrieve all events history and get a total amount earned by lending per aToken.
* :feature:`530` You can now add ethereum addresses by ENS name. Simply use an ENS name in the ETH address field and if it can be resolved it will be appended to the tracked accounts.
* :bug:`1110` DSR Dai balance will now not be recounted with every force refresh querying of blockchain balances
* :feature:`-` Support TUSD, KNC, ZRX and the special USDC-B collateral types for makerdao vaults.
* :feature:`-` Support Australian Dollar (AUD) as fiat currency
* :feature:`-` Count Kraken `off-chain staked assets <https://support.kraken.com/hc/en-us/articles/360039879471-What-is-Asset-S-and-Asset-M->`__ as normal Kraken balance.

* :feature:`-` Added support for the following tokens

  - `Aave Interest bearing BAT (aBAT) <https://www.coingecko.com/en/coins/aave-bat>`__
  - `Aave Interest bearing Binance USD (aBUSD) <https://www.coingecko.com/en/coins/aave-busd>`__
  - `Aave Interest bearing ENJ (aENJ) <https://www.coingecko.com/en/coins/aave-enj>`__
  - `Aave Interest bearing ETH (aETH) <https://www.coingecko.com/en/coins/aave-eth>`__
  - `Aave Interest bearing KNC (aKNC) <https://www.coingecko.com/en/coins/aave-knc>`__
  - `Aave Interest bearing LEND (aLEND) <https://www.coingecko.com/en/coins/aave-lend>`__
  - `Aave Interest bearing LINK (aLINK) <https://www.coingecko.com/en/coins/aave-link>`__
  - `Aave Interest bearing MANA (aMANA) <https://www.coingecko.com/en/coins/aave-mana>`__
  - `Aave Interest bearing MKR (aMKR) <https://www.coingecko.com/en/coins/aave-mkr>`__
  - `Aave Interest bearing REN (aREN) <https://www.coingecko.com/en/coins/aave-ren>`__
  - `Aave Interest bearing REP (aREP) <https://www.coingecko.com/en/coins/aave-rep>`__
  - `Aave Interest bearing SNX (aSNX) <https://www.coingecko.com/en/coins/aave-snx>`__
  - `Aave Interest bearing SUSD (aSUSD) <https://www.coingecko.com/en/coins/aave-susd>`__
  - `Aave Interest bearing TUSD (aTUSD) <https://www.coingecko.com/en/coins/aave-tusd>`__
  - `Aave Interest bearing USDC (aUSDC) <https://www.coingecko.com/en/coins/aave-usdc>`__
  - `Aave Interest bearing USDT (aUSDT) <https://www.coingecko.com/en/coins/aave-usdt>`__
  - `Aave Interest bearing WBTC (aWBTC) <https://www.coingecko.com/en/coins/aave-wbtc>`__
  - `Aave Interest bearing ZRX (aZRX) <https://www.coingecko.com/en/coins/aave-zrx>`__
  - `Compound USDT (cUSDT) <https://www.coingecko.com/en/coins/compound-usdt>`__
  - `Compound SAI (cSAI) <https://www.coingecko.com/en/coins/compound-sai>`__
  - `Compound (COMP) <https://coinmarketcap.com/currencies/compound/>`__
  - `ALQO (ALQO) <https://coinmarketcap.com/currencies/alqo/>`__
  - `Solana (SOL) <https://coinmarketcap.com/currencies/solana/>`__
  - `Harmony (ONE) <https://coinmarketcap.com/currencies/harmony/>`__
  - `Binance leveraged token ADAUP (ADAUP) <https://www.cryptocompare.com/coins/adaup/overview>`__
  - `Binance leveraged token ADADOWN (ADADOWN) <https://www.cryptocompare.com/coins/adadown/overview>`__
  - `Binance leveraged token BTCUP (BTCUP) <https://www.cryptocompare.com/coins/btcup/overview>`__
  - `Binance leveraged token BTCDOWN (BTCDOWN) <https://www.cryptocompare.com/coins/btcdown/overview>`__
  - `Binance leveraged token ETHUP (ETHUP) <https://www.cryptocompare.com/coins/ethup/overview>`__
  - `Binance leveraged token ETHDOWN (ETHDOWN) <https://www.cryptocompare.com/coins/btcdown/overview>`__
  - `Binance leveraged token LINKUP (LINKUP) <https://www.cryptocompare.com/coins/linkup/overview>`__
  - `Binance leveraged token LINKDOWN (LINKDOWN) <https://www.cryptocompare.com/coins/linkdown/overview>`__
  - `Binance IDR Stable Coin (Binance IDR Stable Coin) <https://www.cryptocompare.com/coins/bidr/overview>`__
  - `Everipedia (IQ) <https://coinmarketcap.com/currencies/everipedia/>`__
  - `IQ.Cash (IQ) <https://coinmarketcap.com/currencies/iqcash/>`__
  - `pNetwork Token (PNT) <https://coinmarketcap.com/currencies/pnetwork/>`__
  - `Penta Network Token (PNT) <https://coinmarketcap.com/currencies/penta/>`__
  - `StormX (STMX) <https://coinmarketcap.com/currencies/stormx/>`__
  - `Arweave (AR) <https://coinmarketcap.com/currencies/arweave/>`__
  - `Celo (CELO) <https://coinmarketcap.com/currencies/celo/>`__
  - `Velas (VLX) <https://coinmarketcap.com/currencies/velas/>`__
  - `Kadena (KDA) <https://coinmarketcap.com/currencies/kadena/>`__
  - `All.me (ME) <https://www.cryptocompare.com/coins/me/overview>`__
  - `Dawn protocol (DAWN) <https://coinmarketcap.com/currencies/dawn-protocol/>`__
  - `Lucy (LUCY) <https://coinmarketcap.com/currencies/lucy/>`__
  - `BTEcoin (BTE) <https://www.coingecko.com/en/coins/btecoin>`__
  - `King DAG (KDAG) <https://coinmarketcap.com/currencies/king-dag/>`__
  - `The Force Protocol (FOR) <https://coinmarketcap.com/currencies/the-force-protocol/>`__
  - `Balancer (BAL) <https://coinmarketcap.com/currencies/balancer/>`__
  - `Bitchery (BCHC) <https://coinmarketcap.com/currencies/bitcherry/>`__
  - `bZx protocol (BZRX) <https://coinmarketcap.com/currencies/bzx-protocol/>`__
  - `Meta (MTA) <https://coinmarketcap.com/currencies/meta/>`__
  - `WazirX token (WRX) <https://coinmarketcap.com/currencies/wazirx/>`__
  - `xDAI STAKE (STAKE) <https://coinmarketcap.com/currencies/xdai/>`__
  - `yearn.finance (YFI) <https://coinmarketcap.com/currencies/yearn-finance/>`__
  - `MimbleWimbleCoin (MWC) <https://coinmarketcap.com/currencies/mimblewimblecoin/>`__

* :release:`1.5.0 <2020-06-10>`
* :bug:`986` Allows the unsetting of the RPC endpoint
* :feature:`918` Premium users can now set watchers for their vaults. When the watched vault gets below or above a certain collateralization ratio they get an email alert.
* :bug:`836` Allows the use of non-checksummed eth addresses in the frontend.
* :bug:`1016` Rotki users can now delete their rotki premium API keys via API Keys -> Rotki Premium.
* :feature:`1015` Rotki now lets the user manually refresh and take a snapshot of their balances, even if the balance save frequency has not lapsed. This functionality is accessible through the Save Indicator (floppy disk icon on the app bar).
* :feature:`707` Rotki now supports makerdao vaults. The vaults of the user are autodetected and they can see all details of each
  vault in the DeFi borrowing section. Premium users can also see historical information and total interest owed or USD lost to liquidation.
* :feature:`917` Rotki now has a new and improved Dashboard. Users can view their total net worth as well as totals per source of balances (exchanges, blockchains, and manual entries), as well as filter the full asset listing.
* :bug:`995` Importing from cointracking.info should now work again. Adjust to the latest cointracking.info CSV export format.
* :feature:`971` Rotki's initial loading and welcome screens are now integrated with an improved UI and a scrolling robin in the background to welcome the user.
* :feature:`988` General and Accounting settings have been consolidated into one Settings page, accessed via the User Menu, where users can access them as separate tabs.
* :feature:`763` Rotki users can now change their password in the app's settings in the "User & Security" tab.
* :bug:`962` Fix infinite loop in Coinbase trades query
* :feature:`-` Rotki users now have two options to further enhance their privacy. If a user wants to temporarily obscure values in the application, they can do so by turning `Privacy Mode` on and off in the User Menu. Additionally, if a user wants to scramble their data (e.g. before sharing screenshots or videos), they can do so via the `Scramble Data` setting in the application's General Settings.
* :bug:`966` Rotki now supports the new Kraken LTC and XRP trade pairs
* :feature:`-` Added support for the following tokens

  - `Aave Interest bearing DAI (aDAI) <https://www.coingecko.com/en/coins/aave-dai>`__
  - `Loki (LOKI) <https://coinmarketcap.com/currencies/loki/>`__
  - `HyperDAO (HDAO) <https://coinmarketcap.com/currencies/hyperdao/>`__
  - `VeChain Thor (VTHO) <https://www.cryptocompare.com/coins/vtho/overview>`__
  - `JUST (JST) <https://coinmarketcap.com/currencies/just/>`__
  - `3x Short Bitcoin Cash Token (BCHBEAR) <https://coinmarketcap.com/currencies/3x-short-bitcoin-cash-token/>`__
  - `3x Long Bitcoin Cash Token (BCHBULL) <https://coinmarketcap.com/currencies/3x-long-bitcoin-cash-token/>`__
  - `3x Short Bitcoin SV Token (BSVBEAR) <https://coinmarketcap.com/currencies/3x-short-bitcoin-sv-token/>`__
  - `3x Long Bitcoin SV Token (BSVBULL) <https://coinmarketcap.com/currencies/3x-long-bitcoin-sv-token/>`__
  - `Connectome (CNTM) <https://www.coingecko.com/en/coins/connectome>`__
  - `Loon Network (LOON) <https://www.cryptocompare.com/coins/loon/overview>`__
  - `Celo Gold (CGLD) <https://coinmarketcap.com/currencies/celo/>`__
  - `TNC Coin (TNC) <https://coinmarketcap.com/currencies/tnc-coin/>`__
  - `Handshake (HNS) <https://coinmarketcap.com/currencies/handshake/>`__
  - `DEAPcoin (DEP) <https://coinmarketcap.com/currencies/deapcoin/>`__
  - `VideoCoin (VID) <https://coinmarketcap.com/currencies/videocoin/>`__
  - `Unicorn Technology International (UTI) <https://www.cryptocompare.com/coins/uti/overview>`__

* :release:`1.4.2 <2020-04-29>`
* :bug:`927` Rotki should no longer fail to handle HTTP Rate limiting if your web3 providing node rate limits you.
* :bug:`950` If too many BTC accounts are used Rotki will no longer delay for a long time due to balance query rate limiting. Proper batching of queries to both bitcoin.info and blockcypher is now happening.
* :bug:`942` Properly save all historical balances to the DB when a user has input manually tracked balances.
* :bug:`946` Handle the malformed response by kraken that is sent if a Kraken user has no balances.
* :bug:`943` If Kraken sends a malformed response Rotki no longer raises a 500 Internal server error. Also if such an error is thrown during setup of any exchange and a stale object is left in the Rotki state, trying to setup the exchange again should now work and no longer give an error that the exchange is already registered.
* :bug:`930` Etherscan API keys are now properly included in all etherscan api queries. Also etherscan API key is no longer compulsory.
* :feature:`922` Speed up ethereum chain balance queries by utilizing the eth-scan contract to batch multiple ether and token balance queries into a single call.
* :bug:`928` Action buttons in overlays ('Sign In', 'Create', etc.) are now never hidden by the privacy dialog regardless of resolution, app scaling, or zoom.
* :feature:`908` Adds the ability to view the full amount on tables when hovering over a hint (asterisk) indicating that the display number has been rounded.
* :bug:`924` LINK is now properly supported for Gemini balance and trade queries.
* :feature:`912` Adds total net value to the dashboard, fiat, and manual balances table. Makes account balance totals to reflect the filtered results.

* :feature:`-` Added support for the following tokens

  - `Cartesi token (CTSI) <https://coinmarketcap.com/currencies/cartesi/>`__
  - `Revain (REV) <https://coinmarketcap.com/currencies/revain/>`__
  - `Ubique chain of things (UCT) <https://coinmarketcap.com/currencies/ubique-chain-of-things/>`__
  - `YOU COIN (YOU) <https://coinmarketcap.com/currencies/you-coin/>`__

* :release:`1.4.1 <2020-04-22>`
* :bug:`-` Improve internal DSR mechanics so that even with hardly anyone using the DSR as of this release, Rotki can still find DSR chi values to provide historical reports of DSR profit.
* :bug:`904` For Kraken users take into account the worst-case API call counter and make sure the maximum calls are not reached to avoid prolonged API bans.
* :bug:`895` Fixes manually tracked balances value column header not updating properly.
* :bug:`899` If a user's ethereum account held both old and new REP the new REP's account balance should now be properly automatically detected.
* :bug:`896` If the current price of an asset of a manually tracked balance can not be found, a value of zero is returned instead of breaking all manually tracked balances.
* :feature:`838` Added additional information about API Keys that can be set up by the user and grouped the API connections page into 3 categories: Rotki Premium / Exchanges / External Services.
* :feature:`-` Added support for the following tokens

  - `Rupiah token (IDRT) <https://coinmarketcap.com/currencies/rupiah-token/>`__
  - `Exchange Union (XUC) <https://coinmarketcap.com/currencies/exchange-union/>`__
  - `Compound DAI (cDAI) <https://coinmarketcap.com/currencies/compound-dai/>`__
  - `Compound BAT (cBAT) <https://etherscan.io/address/0x6c8c6b02e7b2be14d4fa6022dfd6d75921d90e4e>`__
  - `Compound ETH (cETH) <https://etherscan.io/address/0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5>`__
  - `Compound Augur (cREP) <https://www.coingecko.com/en/coins/compound-augur>`__
  - `Compound USD coin (cUSDC) <https://www.coingecko.com/en/coins/compound-usd-coin>`__
  - `Compound Wrapped BTC (cWBTC) <https://www.coingecko.com/en/coins/compound-wrapped-btc>`__
  - `Compound 0x (cZRX) <https://www.coingecko.com/en/coins/compound-0x>`__

* :release:`1.4.0 <2020-04-16>`
* :feature:`807` Enables the addition and querying of manually tracked balances.
* :bug:`874` Fixed a bug where if invalid credentials were given to setup an exchange a 500 error was returned. The error is now handled gracefully.
* :bug:`852` PUT or DELETE on ``/api/1/blockchains/eth`` without etherscan keys configured no longer results in 500 internal server error.
* :feature:`869` The application menu now has some customized menu items. Users can now access the `Usage Guide`, `FAQ`, `Issues & Feature Requests`, and `Logs Directory` from within the Help menu. Additionally, there is a `Get Rotki Premium` menu item for easy access to the premium subscription purchase page. Finally, both backend and frontend logs (``rotkehlchen.log`` and ``rotki-electron.log`` respectively) are now found in these standard locations per OS:

  * Linux: ``~/.config/rotki/logs``
  * OSX: ``~/Library/Application Support/rotki/logs``
  * Windows: ``<WindowsDrive>:\Users\<User>\Roaming\rotki\logs\``
* :feature:`862` Added a new API endpoint ``/api/1/ping`` as quick way to query API status for client/frontend initialization.
* :feature:`860` Added a new API endpoint ``/api/1/assets/all`` to query information about all supported assets.
* :bug:`848` Querying ``/api/1/balances/blockchains/btc`` with no BTC accounts tracked no longer results in a 500 Internal server error.
* :bug:`837` If connected to an ethereum node, the connection status indicator should now properly show that to the user.
* :bug:`830` If using alethio detecting tokens from an address that contains more than 10 tokens should now work properly
* :bug:`805` Rotki can now accept passwords containing the " character
* :feature:`764` Gemini exchange is now supported. Trades, deposits, withdrawals and balances from that exchange can now be queried.
* :feature:`-` Add support for the South African Rand  (ZAR - R) as a fiat currency
* :feature:`-` Added support for the following tokens

  - `Standard Tokenization Protocol (STPT) <https://coinmarketcap.com/currencies/standard-tokenization-protocol/>`__
  - `IRISnet (IRIS) <https://coinmarketcap.com/currencies/irisnet/>`__
  - `Hive (HIVE) <https://coinmarketcap.com/currencies/hive-blockchain/>`__
  - `Hive dollar (HBD) <https://coinmarketcap.com/currencies/hive-dollar/>`__
  - `Swipe (SXP) <https://coinmarketcap.com/currencies/swipe/>`__
  - `Elamachain (ELAMA) <https://coinmarketcap.com/currencies/elamachain/>`__
  - `Starchain (STC) <https://coinmarketcap.com/currencies/starchain/>`__
  - `3X Short Bitcoin Token (BEAR) <https://coinmarketcap.com/currencies/3x-short-bitcoin-token/>`__
  - `3X Long Bitcoin Token (BULL) <https://coinmarketcap.com/currencies/3x-long-bitcoin-token/>`__
  - `3X Short Ethereum Token (ETHBEAR) <https://coinmarketcap.com/currencies/3x-short-ethereum-token/>`__
  - `3X Long Ethereum Token (ETHBULL) <https://coinmarketcap.com/currencies/3x-long-ethereum-token/>`__
  - `3X Short TRX Token (TRXBEAR) <https://coinmarketcap.com/currencies/3x-short-trx-token/>`__
  - `3X Long TRX Token (TRXBULL) <https://coinmarketcap.com/currencies/3x-long-trx-token/>`__
  - `3X Short EOS Token (EOSBEAR) <https://www.cryptocompare.com/coins/eosbear/overview>`__
  - `3X Long EOS Token (EOSBULL) <https://www.cryptocompare.com/coins/eosbull/overview>`__
  - `3X Short XRP Token (XRPBEAR) <https://www.cryptocompare.com/coins/xrpbear/overview>`__
  - `3X Long XRP Token (XRPBULL) <https://www.cryptocompare.com/coins/xrpbull/overview>`__
  - `3X Short BNB Token (BNBBEAR) <https://coinmarketcap.com/currencies/3x-short-bnb-token/>`__
  - `3X Long BNB Token (BNBBULL) <https://coinmarketcap.com/currencies/3x-long-bnb-token/>`__
  - `HEX (HEX) <https://www.coingecko.com/en/coins/hex>`__
  - `Binance KRW (BKRW) <https://www.cryptocompare.com/coins/bkrw/overview>`__


* :release:`1.3.0 <2020-03-20>`
* :feature:`779` OSX: User can now exit the application by simply pressing [X]
* :bug:`794` If etherscan rate limits the user it should now be handled correctly after their new changes ... again
* :feature:`643` Rotki will now autodetect the tokens owned by each of your ethereum accounts. Integration with alethio is possible, and you can add an Alethio API key.
* :bug:`790` SegWit addresses (Bech32) can now be added to BTC balances.
* :feature:`-` Rotki should now remember your window size, position, and maximized state after closing the app.
* :bug:`783` Fixes the update indicator to indicate to users if their client is out of date.
* :feature:`-` Added support for the following tokens

  - `Bosagora (BOA) <https://coinmarketcap.com/currencies/bosagora/>`__
  - `Nervos Network (CKB) <https://coinmarketcap.com/currencies/nervos-network/>`__
  - `Molecular Future Token (MOF) <https://coinmarketcap.com/currencies/molecular-future/>`__
* :feature:`-` Add support for the newly added kraken FX trade pairs

* :release:`1.2.1 <2020-03-10>`
* :bug:`770` Adds loading screen while waiting for the backend to start.
* :bug:`772` Getting a rate limit error from Etherscan should be now handled properly.
* :feature:`-` Support TRX in kraken, since it got listed.

* :release:`1.2.0 <2020-03-01>`
* :feature:`705` Support MakerDAO's DAI Savings Rate (DSR)
* :bug:`502` The OSX rotki app icon should no longer be blurry.
* :bug:`698` Rotki should now also display the version in the UI for Windows and OSX.
* :bug:`709` Rotki no longer crashes after second time of opening the application in Windows.
* :bug:`716` The rotki logs for linux now go into a proper directory: ``~/.config/rotki/logs``
* :feature:`461` You can now label your blockchain accounts and tag them with any numer of custom tags to group them into categories. Tags can be customized.
* :bug:`739` If there is an error during DBUpgrade or if the user uses old software to run a new DB we don't crash and burn with a 500 error but instead show a proper message.
* :bug:`731` Fixed cointracking file import.
* :bug:`726` Fail gracefully and don't throw a 500 server error if blockchain balance query fails.
* :bug:`724` If latest block remote query fails do not revert to etherscan but persist with using the provided ethereum node after warning the user.
* :feature:`-` Added support for the following tokens

  - `LTO Network (LTO) <https://coinmarketcap.com/currencies/lto-network/>`__
  - `Verasity (VRA) <https://coinmarketcap.com/currencies/verasity/>`__
  - `Chai (CHAI) <https://etherscan.io/token/0x06af07097c9eeb7fd685c692751d5c66db49c215/>`__
  - `Coti (COTI) <https://coinmarketcap.com/currencies/coti/>`__
  - `MovieBloc (MBL) <https://coinmarketcap.com/currencies/moviebloc/>`__
  - `Alibaba Coin (ABBC) <https://coinmarketcap.com/currencies/abbc-coin/>`__
  - `WaykiChain (WICC) <https://coinmarketcap.com/currencies/waykichain/>`__

* :release:`1.1.1 <2020-02-06>`
* :bug:`693` Fix crash in OSX .dmg package version that occured with v1.1.0

* :release:`1.1.0 <2020-02-05>`
* :feature:`626` Rotki now accepts addition of API keys for external services such as etherscan or cryptocompare.
* :feature:`46` Coinbase Pro is now supported. Trades, deposits, withdrawals and balances in that exchange can now be queried.
* :feature:`583` The UI's notifications can finally be copy pasted.
* :feature:`168` Users can now force-refresh exchange/blockchain balances via the UI and ignore the cache.
* :feature:`354` Introduces a modern, easily extendable material design UI based on Vue.js and Vuetify.
* :feature:`404` Removed ZMQ as the messaging layer between backend - frontend and introduced a full-fledged REST API instead.
* :bug:`465` Asset icons and names show consistently in the UI after the vue.js rewrite.
* :feature:`-` Added support for the following tokens

  - `Orchid (OXT) <https://coinmarketcap.com/currencies/orchid/>`__
  - `DREP (DREP) <https://coinmarketcap.com/currencies/drep/>`__
  - `Origin Protocol (OGN) <https://coinmarketcap.com/currencies/origin-protocol/>`__
  - `Token Club (TCT) <https://coinmarketcap.com/currencies/tokenclub/>`__
  - `Tap (XTP) <https://coinmarketcap.com/currencies/tap/>`__
  - `Xensor (XSR) <https://coinmarketcap.com/currencies/xensor/>`__

* :release:`1.0.7 <2020-01-04>`
* :bug:`605` Adding a premium API key via the front-end now works properly again.
* :bug:`602` Fixed a bug that lead to the coinbase exchange integration not working.

* :release:`1.0.6 <2019-12-31>`
* :bug:`589` If there is an error an unexpected error during sign-in properly catch it and add a log entry.
* :bug:`588` The electron log is now written in the proper directory depending on the Operating system.
* :bug:`587` If a user has a disabled taxfree period setting rotki no longer fails to sign the user in.
* :bug:`561` Export unique asset symbols during CSV exporting and not long name descriptions.
* :feature:`-` Add support for the Turkish Lyra  (TRY - ₺) as a fiat currency
* :feature:`-` Add support for the Russian ruble (RUB - ‎₽) as a fiat currency
* :feature:`-` Add support for the Swiss Franc (CHF - Fr.) as a fiat currency
* :feature:`-` Added support for the following tokens

  - `Troy (TROY) <https://coinmarketcap.com/currencies/troy/>`__
  - `Hycon (HYC) <https://coinmarketcap.com/currencies/hycon/>`__

* :release:`1.0.5 <2019-11-30>`
* :feature:`547` Support Multicollateral DAI upgrade and Single Collateral DAI renaming to SAI.
* :bug:`545` Trades from all Kraken pairs should now be processed properly again. For example all SC trade pairs should now work again.
* :bug:`543` User will not get unexpected balance results in the same Rotki run due to same cache being used for different arguments.
* :feature:`541` If the user allows anonymous usage analytics are submitted to a server for analysis of the application's active users.
* :feature:`-` Rebranding Rotkehlchen to Rotki inside the application. All website and api links should now target rotki.com
* :bug:`534` Old external trades can now be edited/deleted properly again.
* :bug:`527` If cryptocompare query returns an empty object Rotki client no longer crashes.

* :feature:`-` Added support for the following tokens

  - `ArpaChain (ARPA) <https://coinmarketcap.com/currencies/arpa-chain/>`__
  - `Kava (KAVA) <https://coinmarketcap.com/currencies/kava/>`__
  - `Medibloc (MED) <https://coinmarketcap.com/currencies/medibloc/>`__
  - `FNB Protocol (FNB) <https://coinmarketcap.com/currencies/fnb-protocol/>`__
  - `Pledge coin (PLG) <https://coinmarketcap.com/currencies/pledge-coin/>`__
  - `SIX Network (SIX) <https://coinmarketcap.com/currencies/six/>`__
  - `W Green Pay (WGP) <https://coinmarketcap.com/currencies/w-green-pay/>`__
  - `FLETA (FLETA) <https://coinmarketcap.com/currencies/fleta/>`__
  - `PAX Gold (PAXG) <https://coinmarketcap.com/currencies/pax-gold/>`__
  - `Hdac (HDAC) <https://coinmarketcap.com/currencies/hdac/>`__

* :release:`1.0.4 <2019-10-04>`
* :feature:`498` Users can now import data from Cointracking into Rotki. Create a CSV export from Cointracking and import it from the Import Data menu.
* :bug:`500` Fix cryptocompare price queries for LBRY credits.
* :feature:`505` Support the new cryptocompare v2 historical price [API](https://blog.cryptocompare.com/historical-data-api-update-4ee44c549a8f).
* :feature:`499` All actions (trades, deposits, withdrawals, ethereum transactions, margin positions) are now saved in the DB.
* :feature:`-` Support WorldWideAssetExchange token for Bittrex after it got renamed to `WAXP <https://international.bittrex.com/Market/Index?MarketName=BTC-WAXP>`__ in that exchange.
* :feature:`-` Added support for the following tokens

  - `Perling (PERL) <https://coinmarketcap.com/currencies/perlin/>`__
  - `HedgeTrade (HEDG) <https://coinmarketcap.com/currencies/hedgetrade/>`__
  - `Hedera Hashgraph (HBAR) <https://coinmarketcap.com/currencies/hedera-hashgraph/>`__
  - `Morpheus Network (MRPH) <https://coinmarketcap.com/currencies/morpheus-network/>`__
  - `Chiliz (CHZ) <https://coinmarketcap.com/currencies/chiliz/>`__
  - `Binance USD (BUSD) <https://coinmarketcap.com/currencies/binance-usd/>`__
  - `Band Protcol (BAND) <https://coinmarketcap.com/currencies/band-protocol/>`__
  - `Beam Token (BEAM) <https://coinmarketcap.com/currencies/beam/>`__

* :release:`1.0.3 <2019-08-30>`
* :feature:`453` If a newer version exists the user is notified at the start of the application and is given a link to download it.
* :feature:`487` USDT can now also be monitored as an ethereum token.
* :feature:`26` Rotki is now available as a .dmg installer for OSX.
* :bug:`426` Opening the Rotki electron app in OSX now works properly the first time.
* :feature:`296` Add support for the Coinbase exchange.
* :bug:`480` Calculating accounting with empty history no longer throws an exception.
* :bug:`469` Fixes error with OTC trades.
* :bug:`463` Converts tax report start and end time to local time.
* :bug:`467` Removing ETH tokens for which a cryptocompare query failed to find a price now work properly.
* :feature:`458` Binance users now also have their deposit/withdrawal history taken into account during profit/loss calculation.
* :feature:`457` Bittrex users now also have their deposit/withdrawal history taken into account during profit/loss calculation.
* :bug:`451` An assertion will no longer stop balances from being saved for some FIAT assets.

* :feature:`-` Added support for the following tokens

  - `Pixel <https://coinmarketcap.com/currencies/pixel/>`__
  - `Bittrex Credit Tokens <https://bittrex.zendesk.com/hc/en-us/articles/360032214811/>`__
  - `Cocos-BCX <https://coinmarketcap.com/currencies/cocos-bcx/>`__
  - `Akropolis <https://coinmarketcap.com/currencies/akropolis/>`__

* :release:`1.0.2 <2019-08-04>`
* :feature:`-` Added support for the following tokens

  - `Contentos <https://coinmarketcap.com/currencies/contentos/>`__
* :feature:`442` If a user provides a Kraken API key with insufficient permissions we no longer accept it and also provide them with a proper error message.
* :bug:`443` Fix bug in deserialization of non-exact floating point kraken timestamp values which could lead to a crash during tax report generation.

* :release:`1.0.1 <2019-08-02>`
* :feature:`425` Users can now provide arguments to the backend via a config file. For more information check the `docs <https://rotkehlchen.readthedocs.io/en/latest/usage_guide.html#set-the-backend-s-arguments`__.
* :feature:`-` Added support for the following tokens

  - `Luna Coin <https://coinmarketcap.com/currencies/luna-coin/>`__
  - `Luna Terra <https://coinmarketcap.com/currencies/terra/>`__
  - `Spin Protocol <https://coinmarketcap.com/currencies/spin-protocol/>`__
  - `Blockcloud <https://coinmarketcap.com/currencies/blockcloud/>`__
  - `Bloc.Money <https://coinmarketcap.com/currencies/bloc-money/>`__
  - `Chromia  <https://coinmarketcap.com/currencies/chromia/>`__
* :feature:`428` Better handle unexpected data from external sources.
* :bug:`76` Handle poloniex queries returning null for the fee field.
* :bug:`432` If historical price for a trade is not found gracefully skip the trade. Also handle cryptocompare query edge case.
* :bug:`429` Properly handle 429 http response from blockchain.info by backing off by the suggested number of seconds and then trying again.

* :release:`1.0.0 <2019-07-22>`
* :bug:`420` There are no more negative percentages at tax report generation progress
* :bug:`392` Revisiting usersettings properly updates per account tables if an account has been deleted before.
* :bug:`325` Tracking accounts/tokens in user settings will now be immediately reflected on the dashboard.
* :bug:`368` Fixes broken navigation after visiting Statistics page.
* :bug:`361` Rotkehlchen no longer misses the last trade when processing history inside a timerange.
* :bug:`349` Copy paste should now work on OSX.
* :feature:`332` Add notifications area for actionable warnings/errors.
* :feature:`350` Add support for remote ethereum nodes and not just local ones.
* :feature:`329` Maintain a list of supported assets and converters from/to each exchange or service.
* :feature:`194` Add setting for date display format.
* :bug:`334` Handle too many requests error for the exchangerates api.
* :bug:`323` Properly display usd value For JPY and some other assets in kraken where XXBT is the quote asset.
* :bug:`320` The user settings pane is now always responsive, even when loaded a second time.
* :feature:`313` Premium feature: The statistic pane now has two different graphs to explore the distribution of value of the user. One shows the distribution of the total net value across different locations and the other across all assets the user holds.
* :feature:`312` Premium feature: The statistic pane now has a graph where users can check how any asset's amount and total usd value progresses over time.
* :bug:`314` Exchangerates api is now queried with priority and as such there are no more delays at the startup of the application due to unresponsive FOREX api calls.
* :feature:`272` Added a statistics pane. Premium users can now see a graph of their net value over time there.
* :bug:`299` IOTA historical price queries now work properly.
* :bug:`288` After a user re-login querying fiat prices will no longer throw exceptions.
* :bug:`273` Fallback to fetching NANO Price using XRB (Raiblocks) symbol before the rebranding.
* :bug:`283` OTC Trades table is now properly rendered again
* :feature:`268` Version name is now included in rotkehlchen binaries and other artifacts.

* :release:`0.6.0 <2019-01-21>`
* :feature:`92` Cache and have multiple APIs to query for fiat price queries.
* :feature:`222` Add a progress indicator during the tax report generation.
* :bug:`134` When rotkehlchen makes too many requests to Binance and gets a 429 response it now backs off and waits a bit.
* :bug:`241` When incurring margin trade loss the lost asset's available amount is now also reduced.
* :bug:`240` Poloniex settlement buys now incur the correct amount of BTC loss when processed.
* :bug:`218` Tax report details in the UI should no longer show NaN values in some columns.
* :bug:`231` Selling an asset that will fork, before it does now also reduces the forked asset amount.
* :bug:`232` Multiple rotkehlchen users will no longer share same cache files.
* :feature:`229` Rotkehlchen can now work and migrate to sqlcipher v4.
* :bug:`206` Fixes an error when adding a bitcoin account for the first time.
* :bug:`209` Fixes error during login due to invalid date being saved.
* :bug:`223` Fix error in profit/loss calculation due to bugs in the search of the FIFO queue of buy events.
* :feature:`221` Rotkehlchen is now shielded against incosistencies of cryptocompare FIAT data.
* :bug:`219` Poloniex BTC settlement loss calculation is now correct.
* :bug:`217` Tax report CSV exports should now agree with the app report.
* :bug:`211` Handle the BCHSV fork in Kraken properly.

* :release:`0.5.0 <2018-11-10>`
* :bug:`201` Having ICN in Kraken from 31/10 to 31/11 2018 will not lead rotkehlchen to crash.
* :feature:`186` Pressing Enter at signin/create new account and other popups will submit them just like clicking the form button.
* :bug:`197` Rotkehlchen no longer crashes at restart if a "No" tax_free_period is given
* :bug:`185` Ethereum node connection indicator should always properly indicate the connection status to the underlying ethereum node
* :bug:`184` If Rotkehlchen brand name in top left is clicked, open browser to rotkehlchen.io instead of showing the sign-in popup
* :bug:`187` Exchange balance tables no longer become unresponsive if visited multiple times.
* :feature:`178` New logout api call. Users can now logout of a rotkehlchen session.
* :bug:`181` Take 0 net balance into account when doing balance queries and not crash.
* :bug:`156` Overflow should now scroll completely and properly on mac.
* :feature:`138` Add an option to allow for anonymizing of all sensitive rotkehlchen logs.
* :feature:`132` Added a UI widget showing if rotkehlchen is connected to an ethereum node
* :bug:`173` Price querying for IOTA should now work properly with cryptocompare

* :release:`0.4.0 <2018-09-23>`
* :feature:`144` Rotkehlchen now starts fully supporting Bitmex and allows querying Bitmex history for tax calculations.
* :bug:`163` Properly handle errors in the tax report calculation and in other asynchronous tasks.
* :bug:`155` Check if the local ethereum node is synced before querying balances from it.
* :feature:`153` Add a ``version`` command to display the rotkehlchen version.
* :bug:`159` Gracefully exit if an invalid argument is provided.
* :bug:`151` If an asset stored at Bittrex does not have a BTC market rotkehlchen no longer crashes.
* :feature:`148` Add icons for all tokens to the UI.
* :feature:`74` Add experimental support for Bitmex. Supporting only simple balance query for now.
* :bug:`135` Fix bug in converting binance sell trades to the common rotkehlchen format
* :bug:`140` Don't log an error if the manual margin file is not found

* :release:`0.3.2 <2018-08-25>`
* :feature:`95` Add a UI widget to display the last time the balance data was saved in the DB.
* :bug:`126` Refuse to generate a new tax report if one is in progress and also clean previous report before generating a new one.
* :bug:`123` Return USD as default main currency if DB is new
* :bug:`101` Catch the web3 exception if using a local client with an out of sync chain and report a proper error in the UI
* :bug:`86` Fixed race condition at startup that could result in the banks balance displaying as NaN.
* :bug:`103` After removing an exchange's API key the new api key/secret input form is now properly re-enabled
* :bug:`99` Show proper error if kraken or binance api key validation fails due to an invalid key having been provided.

* :release:`0.3.1 <2018-06-25>`
* :bug:`96` Periodic balance data storage should now also work from the UI.

* :release:`0.3.0 <2018-06-24>`
* :feature:`90` Add configuration option for it and periodically save balances data in the database
* :bug:`91` Provide more accurate name for the setting for the date from which historical data starts
* :bug:`89` Many typing bugs were found and fixed
* :bug:`83` Fix a bug that did not allow adding or removing ethereum tokens from the tracker
* :feature:`79` Do not crash with exception if an exchange is unresponsive, but instead warn the user.
* :bug:`77` Fix bug caused by reading `taxfree_after_period` from the database

* :release:`0.2.2 <2018-06-05>`
* :bug:`73` Fixer.io api switched to be subscription based and its endpoints are now locked, so we switch to a different currency converter api.
* :bug:`68` All kraken pairs should now work properly. Users who hold XRP, ZEC, USD, GP, CAD, JPY, DASH, EOSD and USDT in kraken will no longer have any problems.

* :release:`0.2.1 <2018-05-26>`
* :bug:`66` Persist all eth accounts in the database as checksummed. Upgrade all existing DB accounts.
* :bug:`63` Unlocking a user account for an application is no longer slow if you have lots of historical price cache files.
* :bug:`61` Overcome etherscan's limit of 20 accounts per query by splitting the accounts list

* :release:`0.2.0 <2018-05-13>`
* :feature:`51` Add customization for the period of time after which trades are tax free.
* :bug:`50` rotkehlchen --help now works again
* :feature:`45` Add option to customize including crypto to crypto trades.
* :feature:`42` Move the accounting settings to their own page.

* :release:`0.1.1 <2018-04-27>`
* :bug:`37` Fix a bug where adding an ethereum account was throwing an exception in the UI.

* :release:`0.1.0 <2018-04-23>`
