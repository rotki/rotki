Rotki API
##################################################
.. toctree::
  :maxdepth: 2


Introduction
*************

When the Rotki backend runs it exposes an HTTP Rest API that is accessed by either the electron front-end or a web browser. The endpoints accept and return JSON encoded objects. All queries have the following prefix: ``/api/<version>/`` where ``version`` is the current version. The current version at the moment is ``1``.


Response Format
*****************

All endpoints have their response wrapped in the following JSON object

::

    {
        "result": 42,
	"message": ""
    }


In the case of a succesful response the ``"result"`` attribute is populated and is not ``null`` and the ``"message"`` is empty.

::

    {
        "result": null,
	"message": "An error happened"
    }

In the case of a failed response the ``"result"`` attribute is going to be ``null`` and the ``"message"`` attribute will optionally contain information about the error.

Async Queries
==============

Some endpoint queries can accept the argument ``"async_query": true``. When that is done the query is no longer synchronous but will instead immediately return a task id in the following format::

  {
      "result": {"task_id": 10},
      "message": ""
  }

The consumer of the API can later query the `ongoing backend task endpoint <#query-the-result-of-an-ongoing-backend-task>`_ with that id and obtain the outcome of the task when it's ready.

Endpoints
***********

In this section we will see the information about the individual endpoints of the API and detailed explanation of how each one can be used to interact with Rotki.

Handling user creation, sign-in, log-out and querying
==================================================

.. http:get:: /api/(version)/users

   By doing a ``GET`` at this endpoint you can see all the currently existing users and see who if any is logged in.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/users HTTP/1.1
      Host: localhost:5042
      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"john": "loggedin", "maria": "loggedout"},
	  "message": ""
      }

   :statuscode 200: Users query is succesful
   :statuscode 500: Internal Rotki error

.. http:put:: /api/(version)/users

   By doing a ``PUT`` at this endpoint you can create a new user

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/users HTTP/1.1
      Host: localhost:5042

      {
          "name": "john",
	  "password": "supersecurepassword",
	  "sync_approval": "unknown"
	  "premium_api_key": "dasdsda",
	  "premium_api_secret": "adsadasd",
      }

      :reqjson string name: The name to give to the new user
      :reqjson string password: The password with which to encrypt the database for the new user
      :reqjson string sync_approval: A string denoting if the user approved an initial syncing of data from premium when premium keys are given. Valid values are ``"unknown"``, ``"yes"`` and ``"no"``.Should always be ``"unknown"`` at first and only if the user approves should creation with approval as ``"yes`` be sent. If he does not approve a creation with approval as ``"no"`` should be sent. If there is the possibility of data sync from the premium server and this is ``"unknown"`` the creation will fail with an appropriate error asking the consumer of the api to set it to ``"yes"`` or ``"no"``.
      :reqjson string premium_api_key: An optional api key if the user has a Rotki premium account.
      :reqjson string premium_api_secret: An optional api secret if the user has a Rotki premium account.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "exchanges": ["kraken", "poloniex", "binance"],
	      "premium": True,
	      "settings": {
                  "version": "6",
                  "last_write_ts": 1571552172,
                  "premium_should_sync": true,
                  "include_crypto2crypto": true,
                  "anonymized_logs": true,
                  "last_data_upload_ts": 1571552172,
                  "ui_floating_precision": 2,
                  "taxfree_after_period": 31536000,
                  "balance_save_frequency": 24,
                  "include_gas_costs": true,
                  "historical_data_start": "01/08/2015",
                  "eth_rpc_endpoint": "http://localhost:8545",
                  "main_currency": "USD",
                  "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
                  "last_balance_save": 1571552172
	      }
	  },
	  "message": ""
      }

   :statuscode 200: Adding the new user was succesful
   :statuscode 300: Possibility of syncing exists and the creation was sent with sync_approval set to ``"unknown"``. Consumer of api must resend with ``"yes"`` or ``"no"``.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User already exists. Another user is already logged in.
   :statuscode 500: Internal Rotki error

   For succesful requests, result contains the currently connected exchanges, whethere the user has premium activated and the user's settings.

   For failed requests, the resulting dictionary object has ``"result": None, "message": "error"``  where ``"error"`` explains what went wrong.

.. http:patch:: /api/(version)/users/(username)

   By doing a ``PATCH`` at this endpoint with action ``'login'`` you can login to the user with ``username``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/users/john HTTP/1.1
      Host: localhost:5042

      {
          "action": "login"
	  "password": "supersecurepassword",
	  "sync_approval": "unknown",
      }

      :reqjson string action: The action to perform. Can only be one of ``"login"`` or ``"logout"`` and for the login case has to be ``"login"``
      :reqjson string password: The password that unlocks the account
      :reqjson bool sync_approval: A string denoting if the user approved an initial syncing of data from premium. Valid values are ``"unknown"``, ``"yes"`` and ``"no"``.Should always be ``"unknown"`` at first and only if the user approves should an login with approval as ``"yes`` be sent. If he does not approve a login with approval as ``"no"`` should be sent. If there is the possibility of data sync from the premium server and this is ``"unknown"`` the login will fail with an appropriate error asking the consumer of the api to set it to ``"yes"`` or ``"no"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "exchanges": ["kraken", "poloniex", "binance"],
	      "premium": True,
	      "settings": {
                  "version": "6",
                  "last_write_ts": 1571552172,
                  "premium_should_sync": true,
                  "include_crypto2crypto": true,
                  "anonymized_logs": true,
                  "last_data_upload_ts": 1571552172,
                  "ui_floating_precision": 2,
                  "taxfree_after_period": 31536000,
                  "balance_save_frequency": 24,
                  "include_gas_costs": true,
                  "historical_data_start": "01/08/2015",
                  "eth_rpc_endpoint": "http://localhost:8545",
                  "main_currency": "USD",
                  "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
                  "last_balance_save": 1571552172
	      }
	  },
	  "message": ""
      }

   :statuscode 200: Logged in succesfully
   :statuscode 300: Possibility of syncing exists and the login was sent with sync_approval set to ``"unknown"``. Consumer of api must resend with ``"yes"`` or ``"no"``.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Another user is already logged in. User does not exist, password is wrong or some other authentication error.
   :statuscode 500: Internal Rotki error

   The result is the same as creating a new user.

   For succesful requests, result contains the currently connected exchanges, whethere the user has premium activated and the user's settings.

   For failed requests, the resulting dictionary object has ``"result": None, "message": "error"``  where ``"error"`` explains what went wrong.

.. http:patch:: /api/(version)/users/(username)

   By doing a ``PATCH`` at this endpoint with action ``'logout'`` you can logout from your currently logged in account assuming that is ``username``. All user related data will be saved in the database, memory cleared and encrypted database connection closed.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/users/john HTTP/1.1
      Host: localhost:5042

      {
          "action": "logout"
      }

      :reqjson string action: The action to perform. Can only be one of ``"login"`` or ``"logout"`` and for the logout case has to be ``"logout"``

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
	  "message": ""
      }

   :statuscode 200: Logged out succesfully
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in, or user does not exist
   :statuscode 500: Internal Rotki error

.. http:patch:: /api/(version)/users/(username)

   By doing a ``PATCH`` at this endpoint without any action but by providing api_key and api_secret you can set the premium api key and secret pair for the user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/users/john HTTP/1.1
      Host: localhost:5042

      {
          "premium_api_key": "dadsfasdsd",
          "premium_api_secret": "fdfdsgsdmf"
      }

      :reqjson string premium_api_key: The new api key to set for Rotki premium
      :reqjson string premium_api_secret: The new api secret to set for Rotki premium

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
	  "message": ""
      }

   :statuscode 200: API key/secret set succesfully
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: Provided API key/secret does not authenticate or is invalid.
   :statuscode 409: User is not logged in, or user does not exist
   :statuscode 500: Internal Rotki error

Getting or modifying settings
==============================

.. http:get:: /api/(version)/settings

   By doing a GET on the settings endpoint you can get all the user settings for
   the currently logged in account

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/settings HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "version": "6",
	      "last_write_ts": 1571552172,
	      "premium_should_sync": true,
	      "include_crypto2crypto": true,
	      "anonymized_logs": true,
	      "last_data_upload_ts": 1571552172,
	      "ui_floating_precision": 2,
	      "taxfree_after_period": 31536000,
	      "balance_save_frequency": 24,
	      "include_gas_costs": true,
	      "historical_data_start": "01/08/2015",
	      "eth_rpc_endpoint": "http://localhost:8545",
	      "main_currency": "USD",
	      "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
	      "last_balance_save": 1571552172
	  },
	  "message": ""
      }

   :statuscode 200: Querying of settings was succesful
   :statuscode 409: There is no logged in user
   :statuscode 500: Internal Rotki error

   :reqjson int version: The database version
   :reqjson int last_write_ts: The unix timestamp at which an entry was last written in the database
   :reqjson bool premium_should_sync: A boolean denoting whether premium users database should be synced from/to the server
   :reqjson bool include_crypto2crypto: A boolean denoting whether crypto to crypto trades should be counted.
   :reqjson bool anonymized_logs: A boolean denoting whether sensitive logs should be anonymized.
   :reqjson int last_data_upload_ts: The unix timestamp at which the last data upload to the server happened.
   :reqjson int ui_floating_precision: The number of decimals points to be shown for floating point numbers in the UI
   :reqjson int taxfree_after_period: The number of seconds after which holding a crypto in FIFO order is considered no longer taxable. The default is 1 year, as per current german tax rules. Can also be 0 which means there is no taxfree period.
   :reqjson int balance_save_frequency: The number of hours after which user balances should be saved in the DB again. This is useful for the statistics kept in the DB for each user. Default is 24 hours.
   :reqjson bool include_gas_costs: A boolean denoting whether gas costs should be counted as loss in profit/loss calculation.
   :reqjson string historical_data_start: A date in the DAY/MONTH/YEAR format at which we consider historical data to have started.
   :reqjson string eth_rpc_endpoint: A URL denoting the rpc endpoint for the ethereum node to use when contacting the ethereum blockchain. If it can not be reached or if it is invalid etherscan is used instead.
   :reqjson string main_currency: The FIAT currency to use for all profit/loss calculation. USD by default.
   :reqjson string date_display_format: The format in which to display dates in the UI. Default is ``"%d/%m/%Y %H:%M:%S %Z"``.
   :reqjson int last_balance_save: The timestamp at which the balances were last saved in the database.

.. http:put:: /api/(version)/settings

   By doing a PUT on the settings endpoint you can set/modify any settings you need

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/settings HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
          "ui_floating_precision": 4,
          "include_gas_costs": false
      }

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "version": "6",
	      "last_write_ts": 1571552172,
	      "premium_should_sync": true,
	      "include_crypto2crypto": true,
	      "anonymized_logs": true,
	      "last_data_upload_ts": 1571552172,
	      "ui_floating_precision": 4,
	      "taxfree_after_period": 31536000,
	      "balance_save_frequency": 24,
	      "include_gas_costs": false,
	      "historical_data_start": "01/08/2015",
	      "eth_rpc_endpoint": "http://localhost:8545",
	      "main_currency": "USD",
	      "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
	      "last_balance_save": 1571552172
	  },
	  "message": ""
      }

   :statuscode 200: Modifying settings was succesful
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Invalid input, e.g. not the correct type for a setting. Or no user is logged in.
   :statuscode 500: Internal Rotki error

Query the result of an ongoing backend task
===========================================

.. http:get:: /api/(version)/task_result

   By querying this endpoint with a particular task identifier you can get the result of the task if it has finished and the result has not yet been queried. If the result is still in progress or if the result is not found appropriate responses are returned.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/logout HTTP/1.1
      Host: localhost:5042

      {"task_id": 42}

   **Example Completed Response**:

   The following is an example response of an async query to blockchain balances.

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "status": "completed",
	      "outcome": {
	          "per_account": {"BTC": {
	              "1Ec9S8KSw4UXXhqkoG3ZD31yjtModULKGg": {
	          	      "amount": "10",
	          	      "usd_value": "70500.15"
	          	  }
	          }},
	          "totals": {"BTC": {"amount": "10", "usd_value": "70500.15"}}
	      }
	  },
	  "message": ""
      }

   **Example Pending Response**:

   The following is an example response of an async query that is still in progress.

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "status": "pending",
	      "outcome": null
	  },
	  "message": ""
      }

   **Example Not Found Response**:

   The following is an example response of an async query that is still in progress.

   .. sourcecode:: http

      HTTP/1.1 404 OK
      Content-Type: application/json

      {
          "result": {
	      "status": "not found",
	      "outcome": null
	  },
	  "message": "No task with the task id 42 found"
      }

   :statuscode 200: The task's outcome is succesfully returned or pending
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 404: There is no task with the given task id
   :statuscode 409: No user is currently logged in
   :statuscode 500: Internal Rotki error

Query the current fiat currencies exchange rate
===============================================

.. http:get:: /api/(version)/fiat_exchange_rates

   Querying this endpoint with a list of strings representing FIAT currencies will return a dictionary of their current exchange rates compared to USD.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/logout HTTP/1.1
      Host: localhost:5042

      ["EUR", "CNY", "GBP"]

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"EUR": "0.8973438622", "CNY": "7.0837221823", "GBP": "0.7756191673"},
	  "message": ""
      }

   :statuscode 200: The exchange rates have been sucesfully returned
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 500: Internal Rotki error

Setup or remove an exchange
============================

.. http:put:: /api/(version)/exchanges

   Doing a PUT on this endpoint with an exchange's name, api key and secret will setup the exchange for the current user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/exchanges HTTP/1.1
      Host: localhost:5042

      {"name": "kraken", "api_key": "ddddd", "api_secret": "ffffff"}

   :reqjson string name: The name of the exchange to setup
   :reqjson string api_key: The api key with which to setup the exchange
   :reqjson string api_secret: The api secret with which to setup the exchange

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
	  "message": ""
      }

   :statuscode 200: The exchange has been sucesfully setup
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in. The exchange has already been registered or some other error.
   :statuscode 500: Internal Rotki error

.. http:delete:: /api/(version)/exchanges

   Doing a DELETE on this endpoint for a particular exchange name will delete the exchange from the database for the current user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/exchanges HTTP/1.1
      Host: localhost:5042

      {"name": "kraken"}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
	  "message": ""
      }

   :statuscode 200: The exchange has been sucesfully delete
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in. The exchange is not registered or some other error
   :statuscode 500: Internal Rotki error

Querying the balances of an exchange
====================================

.. http:get:: /api/(version)/exchanges/(name)/balances

   Doing a GET on the appropriate exchange endpoint will return the balances of all assets currently help in that exchange.

.. note::
   This endpoint can also be queried asynchronouly by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/exchanges/binance/balances HTTP/1.1
      Host: localhost:5042

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "BTC": {"amount": "1", "usd_value": "7540.15"},
	      "ETH": {"amount": "10", "usd_value": "1650.53"}
	  },
	  "message": ""
      }

   :statuscode 200: Balances succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in.Exchange is not registered or some other exchange query error. Check error message for details.
   :statuscode 500: Internal Rotki error

Querying onchain balances
==========================

.. http:get:: /api/(version)/balances/blockchains/(blockchain_name)/

   Doing a GET on the blockchains balances endpoint will query on-chain balances for the accounts of the user. Doing a GET on a specific blockchain name will query balances only for that chain. Available blockchain names are: ``btc`` and ``eth``.

.. note::
   This endpoint can also be queried asynchronouly by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/balances/blockchains/ HTTP/1.1
      Host: localhost:5042

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "per_account": {
	          "BTC": { "3Kb9QPcTUJKspzjQFBppfXRcWew6hyDAPb": {
		       "amount": "0.5", "usd_value": "3770.075"
		   }. "33hjmoU9XjEz8aLxf44FNGB8TdrLkAVBBo": {
		       "amount": "0.5", "usd_value": "3770.075"
		   }},
		   "ETH": { "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B": {
		       "amount": "10", "usd_value": "1650.53"
		  }}
	      }
	      "totals": {
	          "BTC": {"amount": "1", "usd_value": "7540.15"},
	          "ETH": {"amount": "10", "usd_value": "1650.53"}
	      }
	  },
	  "message": ""
      }

   :reqjson dict per_account: The blockchain balances per account per asset
   :reqjson dict total: The blockchain balances in total per asset

   :statuscode 200: Balances succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in. Invalid blockchain, or problems querying the given blockchain
   :statuscode 500: Internal Rotki error

Querying FIAT balances
==========================

.. http:get:: /api/(version)/balances/fiat/

   Doing a GET on the FIAT balances endpoint will query the FIAT balances of the user.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/balances/fiat/ HTTP/1.1
      Host: localhost:5042

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "EUR": {"amount": "150", "usd_value": "166.21"},
	      "CNY": {"amount": "10500", "usd_value": "1486.05"}
	  },
	  "message": ""
      }


   :statuscode 200: Balances succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal Rotki error

Settings FIAT balances
======================

.. http:get:: /api/(version)/balances/fiat/

   Doing a PATCH on the FIAT balances endpoint will edit the FIAT balances of the given currencies for the currently logged in user. If the balance for an asset is set to 0 then that asset is removed from the database.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/balances/fiat/ HTTP/1.1
      Host: localhost:5042

      {"EUR": "5000", "USD": "3000"}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "EUR": {"amount": "5000", "usd_value": "6130"},
              "USD": {"amount": "3000", "usd_value": "3000"},
	      "CNY": {"amount": "10500", "usd_value": "1486.05"}
	  },
	  "message": ""
      }


   :statuscode 200: Balances succesfully edited.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal Rotki error

Querying owned assets
======================

.. http:get:: /api/(version)/assets/

   Doing a GET on the assets endpoint will return a list of all assets ever owned.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/ HTTP/1.1
      Host: localhost:5042

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["EUR", "USD", "ETH", "BTC"],
	  "message": ""
      }


   :statuscode 200: Assets succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal Rotki error

Statistics for netvalue over time
================================

.. http:get:: /api/(version)/statistics/netvalue/

.. note::
   This endpoint is only available for premium users

   Doing a GET on the statistics netvalue over time endpoint will return all the saved historical data points with user's history


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/netvalue/ HTTP/1.1
      Host: localhost:5042

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "times": [1571992200, 1572078657],
	      "data": ["15000", "17541.23"]
	  },
	  "message": ""
      }

   :reqjson list(int) times: A list of timestamps for the returned data points
   :reqjson list(str) data: A list of net usd value for the corresponding timestamps. They are matched by list index.

   :statuscode 200: Netvalue statistics succesfuly queries.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal Rotki error.

Statistics for asset balance over time
====================================

.. http:get:: /api/(version)/statistics/balance/(asset name)

.. note::
   This endpoint is only available for premium users

   Doing a GET on the statistics asset balance over time endpoint will return all saved balance entries for an asset. Optionally you can filter for a specific time range by providing appropriate arguments.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/balance/BTC HTTP/1.1
      Host: localhost:5042

      {"from_timestamp": 1514764800, "to_timestamp": 1572080165}

   :reqjson int from_timestamp: The timestamp after which to return saved balances for the asset. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return saved balances for the asset. If not given all balances until now are returned.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
              "time": 1571992200,
	      "amount": "1.1",
	      "usd_value": "8901.1"
	      }, {
              "time": 15720001,
	      "amount": "1.2",
	      "usd_value": "9501.3"
	  }],
	  "message": ""
      }

   :reqjson list(object) result: A list of asset balance entries. Each entry contains the timestamp of the entry, the amount in asset and the equivalent usd value at the time.

   :statuscode 200: Single asset balance statistics succesfuly queried
   :statuscode 400: Provided JSON is in some way malformed or data is invalid.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal Rotki error

Statistics for value distribution
==============================

.. http:get:: /api/(version)/statistics/value_distribution/

   Doing a GET on the statistics value distribution endpoint with the ``"distribution_by": "location"`` argument will return the distribution of netvalue across all locations.

.. note::
   This endpoint is only available for premium users


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/value_distribution/ HTTP/1.1
      Host: localhost:5042

      {"distribution_by": "location"}

   :reqjson str distribution_by: The type of distribution to return. It can only be ``"location"`` or ``"asset"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
              "time": 1571992200,
	      "location": "kraken",
	      "usd_value": "8901.1"
	      }, {
              "time": 1571992200,
	      "location": "binance",
	      "usd_value": "9501.3"
	  }],
	  "message": ""
      }

   :reqjson list(object) result: A list of location data entries. Each entry contains the timestamp of the entry, the location and the equivalent usd value at the time.

   :statuscode 200: Value distribution succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed or data is invalid.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal Rotki error.

.. http:get:: /api/(version)/statistics/value_distribution/

.. note::
   This endpoint is only available for premium users

   Doing a GET on the statistics value distribution endpoint with the ``"distribution_by": "asset"`` argument will return the distribution of netvalue across all assets.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/value_distribution/ HTTP/1.1
      Host: localhost:5042

      {"distribution_by": "asset"}

   :reqjson str distribution_by: The type of distribution to return. It can only be ``"location"`` or ``"asset"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
              "time": 1571992200,
	      "asset": "BTC",
	      "amount": "1.2"
	      "usd_value": "8901.1"
	      }, {
              "time": 1571992200,
	      "asset": "ETH",
	      "amount": "80.44",
	      "usd_value": "9501.3"
	  }],
	  "message": ""
      }

   :reqjson list(object) result: A list of asset balance data entries. Each entry contains the timestamp of the entry, the assets, the amount in asset and the equivalent usd value at the time.

   :statuscode 200: Value distribution succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed or data is invalid.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal Rotki error.

Statistics rendering code
================================

.. http:get:: /api/(version)/statistics/renderer/

   Doing a GET on the statistics renderer will return the code to render the statistics if the currently logged in user is a premium user.

.. note::
   This endpoint is only available for premium users


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/netvalue/ HTTP/1.1
      Host: localhost:5042

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": "code goes here"
	  "message": ""
      }


   :statuscode 200: Rendering code succesfully returned.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. There is a problem reaching the Rotki server.
   :statuscode 500: Internal Rotki error.

Dealing with trades
===================

.. http:get:: /api/(version)/trades

   Doing a GET on this endpoint will return all trades of the current user. They can be further filtered by time range and/or location.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/trades HTTP/1.1
      Host: localhost:5042

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "location": "external"}

   :reqjson int from_timestamp: The timestamp from which to query. Can be missing inwhich case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string location: Optionally filter trades by location. A valid location name has to be provided. If missing location filtering does not happen.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
	      "trade_id": "dsadfasdsad",
	      "timestamp": 1491606401,
	      "location": "external",
	      "pair": "BTC_EUR",
	      "trade_type": "buy",
	      "amount": "0.5541",
	      "rate": "8422.1",
	      "fee": "0.55",
	      "fee_currency": "USD",
	      "link": "Optional unique trade identifier"
	      "notes": "Optional notes"
	  }]
	  "message": ""
      }

   :statuscode 200: Trades are succesfully returned
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal Rotki error

.. http:put:: /api/(version)/trades

   Doing a PUT on this endpoint adds a new trade to Rotki's currently logged in user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/trades HTTP/1.1
      Host: localhost:5042

      {
          "timestamp": 1491606401,
          "location": "external",
          "pair": "BTC_EUR",
          "trade_type": "buy",
          "amount": "0.5541",
          "rate": "8422.1",
          "fee": "0.55",
          "fee_currency": "USD",
          "link": "Optional unique trade identifier"
          "notes": "Optional notes"
      }

   :reqjson int timestamp: The timestamp at which the trade occured
   :reqjson string location: A valid location at which the trade happened
   :reqjson string pair: The pair for the trade. e.g. ``"BTC_EUR"``
   :reqjson string trade_type: The type of the trade. e.g. ``"buy"`` or ``"sell"``
   :reqjson string amount: The amount that was bought or sold
   :reqjson string rate: The rate at which 1 unit of ``base_asset`` was exchanges for 1 unit of ``quote_asset``
   :reqjson string fee: The fee that was paid, if anything, for this trade
   :reqjson string fee_currency: The currency in which ``fee`` is denominated in
   :reqjson string link: Optional unique trade identifier or link to the trade. Can be an empty string
   :reqjson string notes: Optional notes about the trade. Can be an empty string

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
	      "trade_id": "dsadfasdsad",
	      "timestamp": 1491606401,
	      "location": "external",
	      "pair": "BTC_EUR",
	      "trade_type": "buy",
	      "amount": "0.5541",
	      "rate": "8422.1",
	      "fee": "0.55",
	      "fee_currency": "USD",
	      "link": "Optional unique trade identifier"
	      "notes": "Optional notes"
	  }]
	  "message": ""
      }

   :statuscode 200: Trades was succesfully added.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal Rotki error

.. http:patch:: /api/(version)/trades

   Doing a PATCH on this endpoint edits an existing trade in Rotki's currently logged in user using the ``trade_identifier``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/trades HTTP/1.1
      Host: localhost:5042

      {
          "trade_id" : "dsadfasdsad",
          "timestamp": 1491606401,
          "location": "external",
          "pair": "BTC_EUR",
          "trade_type": "buy",
          "amount": "1.5541",
          "rate": "8422.1",
          "fee": "0.55",
          "fee_currency": "USD",
          "link": "Optional unique trade identifier"
          "notes": "Optional notes"
      }

   :reqjson string trade_id: The ``trade_id`` of the trade to edit
   :reqjson int timestamp: The new timestamp
   :reqjson string location: The new location
   :reqjson string pair: The new pair
   :reqjson string trade_type: The new trade type
   :reqjson string rate: The new trade rate
   :reqjson string fee: The new fee
   :reqjson string fee_currency: The new fee currency
   :reqjson string link: The new link attribute
   :reqjson string notes: The new notes attribute

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "trade_id": "sdfhdjskfha",
	      "timestamp": 1491606401,
	      "location": "external",
	      "pair": "BTC_EUR",
	      "trade_type": "buy",
	      "amount": "1.5541",
	      "rate": "8422.1",
	      "fee": "0.55",
	      "fee_currency": "USD",
	      "link": "Optional unique trade identifier"
	      "notes": "Optional notes"
	  }
	  "message": ""
      }

   :statuscode 200: Trades was succesfully edited.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The given trade identifier to edit does not exist.
   :statuscode 500: Internal Rotki error.

.. http:delete:: /api/(version)/trades

   Doing a DELETE on this endpoint deletes an existing trade in Rotki's currently logged in user using the ``trade_identifier``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/trades HTTP/1.1
      Host: localhost:5042

      { "trade_id" : "dsadfasdsad"}

   :reqjson string trade_id: The ``trade_id`` of the trade to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
	  "message": ""
      }

   :statuscode 200: Trades was succesfully deleted.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The given trade identifier to delete does not exist.
   :statuscode 500: Internal Rotki error.

Querying messages to show to the user
=====================================

.. http:get:: /api/(version)/messages/

   Doing a GET on the messages endpoint will pop all errors and warnings from the message queue and return them. The message queue is a queue where all errors and warnings that are supposed to be see by the user are saved and are supposed to be popped and read regularly.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/messages/ HTTP/1.1
      Host: localhost:5042

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "errors": ["Something bad happened", "Another bad thing happened"],
	      "warnings": ["An asset could not be queried", "Can not reach kraken"]
	  },
	  "message": ""
      }

   :reqjson list(str) errors: A list of strings denoting errors that need to be shown to the user.
   :reqjson list(str) warnings: A list of strings denoting warnings that need to be shown to the user.

   :statuscode 200: Messages popped and read succesfully.
   :statuscode 500: Internal Rotki error.
