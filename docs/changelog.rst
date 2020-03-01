=========
Changelog
=========

* :bug:`502 major` The OSX rotki app icon should no longer be blurry.
* :bug:`698 major` Rotki should now also display the version in the UI for Windows and OSX.
* :bug:`709 major` Rotki no longer crashes after second time of opening the application in Windows.
* :bug:`716 major` The rotki logs for linux now go into a proper directory: ``~/.config/rotki/logs``
* :feature:`461` You can now label your blockchain accounts and tag them with any numer of custom tags to group them into categories. Tags can be customized.
* :bug:`739 major` If there is an error during DBUpgrade or if the user uses old software to run a new DB we don't crash and burn with a 500 error but instead show a proper message.
* :bug:`731` Fixed cointracking file import.
* :bug:`726 major` Fail gracefully and don't throw a 500 server error if blockchain balance query fails.
* :bug:`724 major` If latest block remote query fails do not revert to etherscan but persist with using the provided ethereum node after warning the user.
* :feature:`99987` Added support for the following tokens

  - `LTO Network (LTO) <https://coinmarketcap.com/currencies/lto-network/>`__
  - `Verasity (VRA) <https://coinmarketcap.com/currencies/verasity/>`__
  - `Chai (CHAI) <https://etherscan.io/token/0x06af07097c9eeb7fd685c692751d5c66db49c215/>`__
  - `Coti (COTI) <https://coinmarketcap.com/currencies/coti/>`__
    
* :release:`1.1.1 <2020-02-06>` 693
* :bug:`693 major` Fix crash in OSX .dmg package version that occured with v1.1.0

* :release:`1.1.0 <2020-02-05>` 626, 46, 583, 168, 354, 404, 465, 99999
* :feature:`626` Rotki now accepts addition of API keys for external services such as etherscan or cryptocompare.
* :feature:`46` Coinbase Pro is now supported. Trades, deposits, withdrawals and balances in that exchange can now be queried.
* :feature:`583` The UI's notifications can finally be copy pasted.
* :feature:`168` Users can now force-refresh exchange/blockchain balances via the UI and ignore the cache.
* :feature:`354` Introduces a modern, easily extendable material design UI based on Vue.js and Vuetify.
* :feature:`404` Removed ZMQ as the messaging layer between backend - frontend and introduced a full-fledged REST API instead.
* :bug:`465 major` Asset icons and names show consistently in the UI after the vue.js rewrite.
* :feature:`99999` Added support for the following tokens

  - `Orchid (OXT) <https://coinmarketcap.com/currencies/orchid/>`__
  - `DREP (DREP) <https://coinmarketcap.com/currencies/drep/>`__
  - `Origin Protocol (OGN) <https://coinmarketcap.com/currencies/origin-protocol/>`__
  - `Token Club (TCT) <https://coinmarketcap.com/currencies/tokenclub/>`__
  - `Tap (XTP) <https://coinmarketcap.com/currencies/tap/>`__
  - `Xensor (XSR) <https://coinmarketcap.com/currencies/xensor/>`__

* :release:`1.0.7 <2020-01-04>`
* :bug:`605` Adding a premium API key via the front-end now works properly again.
* :bug:`602` Fixed a bug that lead to the coinbase exchange integration not working.

* :release:`1.0.6 <2019-12-31>` 589, 588, 587, 561, 99998, 99997, 99996, 99995
* :bug:`589` If there is an error an unexpected error during sign-in properly catch it and add a log entry.
* :bug:`588` The electron log is now written in the proper directory depending on the Operating system.
* :bug:`587` If a user has a disabled taxfree period setting rotki no longer fails to sign the user in.
* :bug:`561` Export unique asset symbols during CSV exporting and not long name descriptions.
* :feature:`99998` Add support for the Turkish Lyra  (TRY - ₺) as a fiat currency
* :feature:`99997` Add support for the Russian ruble (RUB - ‎₽) as a fiat currency
* :feature:`99996` Add support for the Swiss Franc (CHF - Fr.) as a fiat currency
* :feature:`99995` Added support for the following tokens

  - `Troy (TROY) <https://coinmarketcap.com/currencies/troy/>`__
  - `Hycon (HYC) <https://coinmarketcap.com/currencies/hycon/>`__

* :release:`1.0.5 <2019-11-30>` 547, 545, 543, 541, 99994, 99993, 534, 527
* :feature:`547` Support Multicollateral DAI upgrade and Single Collateral DAI renaming to SAI.
* :bug:`545` Trades from all Kraken pairs should now be processed properly again. For example all SC trade pairs should now work again.
* :bug:`543` User will not get unexpected balance results in the same Rotki run due to same cache being used for different arguments.
* :feature:`541` If the user allows anonymous usage analytics are submitted to a server for analysis of the application's active users.
* :feature:`99994` Rebranding Rotkehlchen to Rotki inside the application. All website and api links should now target rotki.com
* :bug:`534` Old external trades can now be edited/deleted properly again.
* :bug:`527` If cryptocompare query returns an empty object Rotki client no longer crashes.

* :feature:`99993` Added support for the following tokens

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

* :release:`1.0.4 <2019-10-04>` 498, 500, 505, 499, 99992, 99991
* :feature:`498` Users can now import data from Cointracking into Rotki. Create a CSV export from Cointracking and import it from the Import Data menu.
* :bug:`500` Fix cryptocompare price queries for LBRY credits.
* :feature:`505` Support the new cryptocompare v2 historical price [API](https://blog.cryptocompare.com/historical-data-api-update-4ee44c549a8f).
* :feature:`499` All actions (trades, deposits, withdrawals, ethereum transactions, margin positions) are now saved in the DB.
* :feature:`99992` Support WorldWideAssetExchange token for Bittrex after it got renamed to `WAXP <https://international.bittrex.com/Market/Index?MarketName=BTC-WAXP>`__ in that exchange.
* :feature:`99991` Added support for the following tokens

  - `Perling (PERL) <https://coinmarketcap.com/currencies/perlin/>`__
  - `HedgeTrade (HEDG) <https://coinmarketcap.com/currencies/hedgetrade/>`__
  - `Hedera Hashgraph (HBAR) <https://coinmarketcap.com/currencies/hedera-hashgraph/>`__
  - `Morpheus Network (MRPH) <https://coinmarketcap.com/currencies/morpheus-network/>`__
  - `Chiliz (CHZ) <https://coinmarketcap.com/currencies/chiliz/>`__
  - `Binance USD (BUSD) <https://coinmarketcap.com/currencies/binance-usd/>`__
  - `Band Protcol (BAND) <https://coinmarketcap.com/currencies/band-protocol/>`__
  - `Beam Token (BEAM) <https://coinmarketcap.com/currencies/beam/>`__

* :release:`1.0.3 <2019-08-30>` 453, 487, 26, 426, 296, 480, 469, 463, 467, 458, 457, 451, 99990
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

* :feature:`99990` Added support for the following tokens

  - `Pixel <https://coinmarketcap.com/currencies/pixel/>`__
  - `Bittrex Credit Tokens <https://bittrex.zendesk.com/hc/en-us/articles/360032214811/>`__
  - `Cocos-BCX <https://coinmarketcap.com/currencies/cocos-bcx/>`__
  - `Akropolis <https://coinmarketcap.com/currencies/akropolis/>`__

* :release:`1.0.2 <2019-08-04>` 99989, 442, 443
* :feature:`99989` Added support for the following tokens

  - `Contentos <https://coinmarketcap.com/currencies/contentos/>`__
* :feature:`442` If a user provides a Kraken API key with insufficient permissions we no longer accept it and also provide them with a proper error message.
* :bug:`443` Fix bug in deserialization of non-exact floating point kraken timestamp values which could lead to a crash during tax report generation.

* :release:`1.0.1 <2019-08-02>` 425, 99988, 428, 76, 432, 429
* :feature:`425` Users can now provide arguments to the backend via a config file. For more information check the `docs <https://rotkehlchen.readthedocs.io/en/latest/usage_guide.html#set-the-backend-s-arguments`__.
* :feature:`99988` Added support for the following tokens

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
