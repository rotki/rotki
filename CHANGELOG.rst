=========
Changelog
=========

* :feature:`153` Add a ``version`` command to display the rotkehlchen version
* :bug:`159` Gracefully exit if an invalid argument is provided
* :bug:`151` If an asset stored at Bittrex does not have a BTC market rotkehlchen no longer crashes.
* :feature:`148` Add icons for all tokens to the UI
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

