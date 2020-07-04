=========
Changelog
=========

* :feature: `530` You can now add ethereum addresses by ENS name. Simply use an ENS name in the ETH address field and if it can be resolved it will be appended to the tracked accounts.
* :bug: `1110` DSR Dai balance will now not be recounted with every force refresh querying of blockchain balances
* :feature: `-` Support TUSD, KNC, ZRX and the special USDC-B collateral types for makerdao vaults.
* :feature: `-` Support Australian Dollar (AUD) as fiat currency
* :feature: `-` Count Kraken `off-chain staked assets <https://support.kraken.com/hc/en-us/articles/360039879471-What-is-Asset-S-and-Asset-M->`__ as normal Kraken balance.

* :feature:`-` Added support for the following tokens

  - `Aave Interest bearing BAT (aBAT) <https://www.coingecko.com/en/coins/aave-bat>`__
  - `Aave Interest bearing Binance USD (aBUSD) <https://www.coingecko.com/en/coins/aave-busd>`__
  - `Aave Interest bearing ETH (aETH) <https://www.coingecko.com/en/coins/aave-eth>`__
  - `Aave Interest bearing KNC (aKNC) <https://www.coingecko.com/en/coins/aave-knc>`__
  - `Aave Interest bearing LEND (aLEND) <https://www.coingecko.com/en/coins/aave-lend>`__
  - `Aave Interest bearing LINK (aLINK) <https://www.coingecko.com/en/coins/aave-link>`__
  - `Aave Interest bearing MANA (aMANA) <https://www.coingecko.com/en/coins/aave-mana>`__
  - `Aave Interest bearing MKR (aMKR) <https://www.coingecko.com/en/coins/aave-mkr>`__
  - `Aave Interest bearing REP (aREP) <https://www.coingecko.com/en/coins/aave-rep>`__
  - `Aave Interest bearing SNX (aSNX) <https://www.coingecko.com/en/coins/aave-snx>`__
  - `Aave Interest bearing SUSD (aSUSD) <https://www.coingecko.com/en/coins/aave-susd>`__
  - `Aave Interest bearing TUSD (aTUSD) <https://www.coingecko.com/en/coins/aave-tusd>`__
  - `Aave Interest bearing USDC (aUSDC) <https://www.coingecko.com/en/coins/aave-usdc>`__
  - `Aave Interest bearing USDT (aUSDT) <https://www.coingecko.com/en/coins/aave-usdt>`__
  - `Aave Interest bearing WBTC (aWBTC) <https://www.coingecko.com/en/coins/aave-wbtc>`__
  - `Aave Interest bearing ZRX (aZRX) <https://www.coingecko.com/en/coins/aave-zrx>`__
  - `Compound USDT (cUSDT) <https://www.coingecko.com/en/coins/compound-usdt>`__
  - `Compound (COMP) <https://coinmarketcap.com/currencies/compound/>`__
  - `ALQO (ALQO) <https://coinmarketcap.com/currencies/alqo/>`__

* :release:`1.5.0 <2020-06-10>`
* :bug: `986` Allows the unsetting of the RPC endpoint
* :feature: `918` Premium users can now set watchers for their vaults. When the watched vault gets below or above a certain collateralization ratio they get an email alert.
* :bug: `836` Allows the use of non-checksummed eth addresses in the frontend.
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
