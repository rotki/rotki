Rotkehlchen Usage Guide
##################################################
.. toctree::
  :maxdepth: 2


Introduction
============ 

In this section we are going to see how to use various parts of the Rotkehlchen application.

Sign-in/Signup
===============

When you start Rotkehlchen you are greeted with a sign-in/signup prompt.

If you have never created an account before press "Create New Account". Provide a username and a password. Don't forget this password. It will be used to encrypt all your local files. If you have purchased a premium subscription you can also add the API Key and secret here.

If you already have an account just write the name and the password here.

All accounts are created in the rotkehlchen directory which is located in: ``$HOME/.rotkehlchen``. Each user has their own subdirectory.

Changing the Profit Currency
=============================

Rotkehlchen calculates everything, including your profit/loss for your tax report into a given FIAT currency. This is what we call the ``profit_currency``. By default this is the US Dollar. You can easily change this setting by clicking on the currency icon the top right menu and changing it to the currency you are using.

Connecting to an Ethereum Client
==================================

When Rotkehlchen begins it tries to connect to a local ethereum node running with an rpc port set at the default port ``8545``. If no client is running then all blockchain queries will use etherscan and this will be rather slower.

If you want to connect to an ethereum client running in a non-default port you can set that through the settings. Click the person icon on the top right menu and select "Settings" from the drop down menu. This will take you to the settings page. Write the desired url/port port in ETH RPC endpoing textbox.

Adding an Exchange
=====================

You can integrate many different exchanges with Rotkehlchen. Currently supported exchanges are: Kraken, Poloniex, Bittrex, Bitmex and Binance.

To do so you have to go to your exchange and create an API key. If the exchange allows it make sure that the API Key only has reading/querying permissions to your account and nothing else since that is all the permissions needed by Rotkehlchen.

Click the Person Icon on the top right menu and then choose "User Settings". This will take you to your user settings page. Under the exchange settings sections, select your exchange from the dropdown menu. Then copy and paste the ``API Key`` and the ``API Secret`` in the respective text fields and press submit.

If all went well, then you will get a confirmation that the connection was successful. If not please doublecheck that the key and secret are correct.

Adding Fiat Balances
=====================

Rotkehlchen is an asset analytics application. Thus you can track all your assets in one place including the FIAT balances you have.

To add or modify the amount of an owned FIAT currency, go to the user settings page, scroll down to the "Fiat Balances" section and choose the currency from the dropdown menu. Input the modified balance in the text box and press the Modify button.

Adding and Removing Blockchain Accounts
============================================

Rotkehlchen allows to track balances of blockchain accounts.

To track an account go to the user settings page, scroll down to the "Blockchain Balances" section and choose the blockchain from the dropdown menu. For now only Bitcoin and Ethereum chains are supported. Then type or paste the address in the "Account" textbox and press the "Add" Button.

To stop tracking a particular account scroll down to the accounts tables and simply right click on the account you want to stop tracking and select "Delete" from the context menu.

Adding and Removing Ethereum Tokens
=========================================

Rotkehlchen will check all of your ethereum accounts for balances of a given list of tokens. This list can be provided and modified by you.

To do so go to the user settings page, scroll down to the "Blockchain Balances" section and look at the "Select Eth Tokens to Track" multiselection widget.

In order to add a token to the tracked tokens find it on the left menu and click it so that it gets added to your tokens.

In order to stop tracking a tocken, find it on the right menu and click it to stop tracking it.

All account balances will be updated at this point.

Manually Adding Trades Or Taxable Events
============================================

Rotkehlchen will pull all your trade history from the exchanges whenever it needs it. But most of us have probably also done some OTC trades or taxable events at some point. Such events could even just be mining tokens, depending on your jurisdiction, participating in an ICO or getting paid in crypto.

On the left menu click on the trades button and select "OTC Trades" from the dropdown menu. This will take you to the OTC Trades page.

To add a new trade or taxable event, fill in all the field and press the "Add Trade" button.

Some very important things to note. All pairs should be in the form of ``BASECURRENCY_QUOTECURRENCY``. For a ``buy`` this means you are buying ``amount`` of the ``BASE`` currency at a price of ``rate`` ``QUOTE`` currency per ``BASE``. For a ``sell`` this means you are selling ``amount`` of the ``BASE`` currency at a price of ``rate`` ``QUOTE`` currency per ``BASE``.

If there was a fee for the trade you should input it in the corresponding box and also enter the currency the fee was paid in. Fee can also be 0.

You can provide additional notes or even links to blockchain explorers for each trade.

At the bottom of this page you can see a table of all your OTC trades.

Creating a Tax Report
======================

Rotkehlchen creates a tax report for you based on your trades and some settings which you can configure at the user settings page. This is essentially a calculation of profit or loss for all your trades based on the given dates.

The default settings are at the moment set for the German tax jurisdiction. For example all profit/loss calculation is done for trades on a first-in/first-out basis and profits from selling crypto assets after 1 year are non taxable. These settings can be adjusted.


To create a tax report click on the "Tax Report" button from the left menu. Choose a start and an end date for the report and then click the "Generate Report" button.

The calculation may take some time. Once done you have an overview of the profit/loss for the given period, how much of that is taxable, and how much each taxable event category contributes to the total.

Additionally below the overview you get a table containing all of the taxable events that were taken into account in the calculation along with how much of the ``profit_currency`` you lost or gained through that event.

Finally you can get a nice CSV export by pressing the "Export CSV" button. This export is meant to be imported into google sheets. Press the button and then choose a directory to write the CSV files to. Once done you can import the CSV files into google sheets via its import menu.


Analytics
=========

If you have a premium subscription you can get analytics on your all your assets and trades.

Click on the analytics page on the left sidebar to go to your analytics page.

Since Rotkehlchen is tracking all your assets over time the first thing you can see is a value/time graph of your entire net value.

Following that you can see a graph of quantity of an asset superimposed on its USD value over time.

Furthermore you can see a piechart of the distribution of your netvalue across different locations. So you can determine how exposed you are to having a big part of your net value in exchanges, in banks e.t.c.

Finally you can see a piechart of the distribution of your netvalue across all of the assets you own. This is an important analytics tool as it can help you determine your exposure on each asset and if some rebalancing of your portfolio is in order.
