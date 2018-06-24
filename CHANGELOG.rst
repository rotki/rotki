=========
Changelog
=========

* :bug: Thanks to `introducing typing <https://github.com/rotkehlchenio/rotkehlchen/pull/89>`_ to many of the modules 3 bugs were found and fixed
* :feature: `90` Add configuration option for it and periodically save balances data in the database
* :bug: `83` Fix a bug that did not allow adding or removing ethereum tokens from the tracker
* :feature: `79` Do not crash with exception if an exchange is unresponsive, but instead warn the user.
* :bug: `77` Fix bug caused by reading `taxfree_after_period` from the database

* :release:`0.2.2 <2018-06-05>`

* :bug: `73` Fixer.io api switched to be subscription based and its endpoints are now locked, so we switch to a different currency converter api.
* :bug: `68` All kraken pairs should now work properly. Users who hold XRP, ZEC, USD, GP, CAD, JPY, DASH, EOSD and USDT in kraken will no longer have any problems.

* :release:`0.2.1 <2018-05-26>`

* :bug: `66` Persist all eth accounts in the database as checksummed. Upgrade all existing DB accounts.
* :bug: `63` Unlocking a user account for an application is no longer slow if you have lots of historical price cache files.
* :bug: `61` Overcome etherscan's limit of 20 accounts per query by splitting the accounts list

* :release:`0.2.0 <2018-05-13>`

* :feature:`51` Add customization for the period of time after which trades are tax free.
* :bug:`50` rotkehlchen --help now works again
* :feature:`45` Add option to customize including crypto to crypto trades.
* :feature:`42` Move the accounting settings to their own page.

* :release:`0.1.1 <2018-04-27>`

* :bug:`37` Fix a bug where adding an ethereum account was throwing an exception in the UI.

* :release:`0.1.0 <2018-04-23>`

