rotki REST API
##################################################
.. toctree::
  :maxdepth: 2


Introduction
*************

When the rotki backend runs it exposes an HTTP Rest API that is accessed by either the electron front-end or a web browser. The endpoints accept and return JSON encoded objects. All queries have the following prefix: ``/api/<version>/`` where ``version`` is the current version. The current version at the moment is ``1``.


Request parameters
********************

All endpoints that take parameters accept a json body with said parameters. If the request is a ``GET`` request then it also accepts query parameters since for multiple implementations a JSON body will not work.

Response Format
*****************

All endpoints have their response wrapped in the following JSON object

::

    {
        "result": 42,
        "message": ""
    }


In the case of a successful response the ``"result"`` attribute is populated and is not ``null``. The message is almost always going to be empty but may at some cases also contain some informational message.

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
Please remember that if you send the ``"async_query": true`` parameter as the body of a ``GET`` request you also have to set the content type header to ``Content-Type: application/json;charset=UTF-8``.

Endpoints
***********

In this section we will see the information about the individual endpoints of the API and detailed explanation of how each one can be used to interact with rotki.

Handling user creation, sign-in, log-out and querying
=======================================================

.. http:get:: /api/(version)/users

   By doing a ``GET`` at this endpoint you can see all the currently existing users and see who if any is logged in.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/users HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"john": "loggedin", "maria": "loggedout"},
          "message": ""
      }

   :resjson object result: The result of the users query. Each element has a username as a key and either ``"loggedin"`` or ``"loggedout"`` values
   :statuscode 200: Users query is successful
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/users

   By doing a ``PUT`` at this endpoint you can create a new user

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/users HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript
      Content-Type: application/json;charset=UTF-8

      {
            "name": "john",
            "password": "supersecurepassword",
            "premium_api_key": "dasdsda",
            "premium_api_secret": "adsadasd",
            "sync_database": true,
            "initial_settings": {
                "submit_usage_analytics": false
            }
      }

   :reqjson string name: The name to give to the new user
   :reqjson string password: The password with which to encrypt the database for the new user
   :reqjson string[optional] premium_api_key: An optional api key if the user has a rotki premium account.
   :reqjson string[optional] premium_api_secret: An optional api secret if the user has a rotki premium account.
   :reqjson bool[optional] sync_database: If set to true rotki will try to download a remote database for premium users if there is any.
   :reqjson object[optional] initial_settings: Optionally provide DB settings to set when creating the new user. If not provided, default settings are used.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "exchanges": [
                   {"location": "kraken", "name": "kraken1", "kraken_account_type": "starter"},
                   {"location": "poloniex", "name": "poloniex1"},
                   {"location": "binance", "name": "binance1"}
               ],
              "settings": {
                  "have_premium": true,
                  "version": "6",
                  "last_write_ts": 1571552172,
                  "premium_should_sync": true,
                  "include_crypto2crypto": true,
                  "last_data_upload_ts": 1571552172,
                  "ui_floating_precision": 2,
                  "taxfree_after_period": 31536000,
                  "balance_save_frequency": 24,
                  "include_gas_costs": true,
                  "ksm_rpc_endpoint": "http://localhost:9933",
                  "main_currency": "USD",
                  "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
                  "last_balance_save": 1571552172,
                  "submit_usage_analytics": true,
                  "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"],
                  "current_price_oracles": ["cryptocompare", "coingecko"],
                  "historical_price_oracles": ["cryptocompare", "coingecko"],
                  "taxable_ledger_actions": ["income", "airdrop"],
                  "ssf_0graph_multiplier": 2,
                  "non_sync_exchanges": [{"location": "binance", "name": "binance1"}]
              }
          },
          "message": ""
      }

   :resjson object result: For successful requests, result contains the currently connected exchanges, and the user's settings. For details on the user settings refer to the `Getting or modifying settings`_ section.
   :statuscode 200: Adding the new user was successful
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User already exists. Another user is already logged in. Given Premium API credentials are invalid. Permission error while trying to access the directory where rotki saves data.
   :statuscode 500: Internal rotki error

.. http:post:: /api/(version)/users/(username)

   By doing a ``POST`` at this endpoint, you can login to the user with ``username``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/users/john HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "password": "supersecurepassword",
          "sync_approval": "unknown"
      }

   :reqjson string password: The password that unlocks the account
   :reqjson bool sync_approval: A string denoting if the user approved an initial syncing of data from premium. Valid values are ``"unknown"``, ``"yes"`` and ``"no"``. Should always be ``"unknown"`` at first and only if the user approves should a login with approval as ``"yes`` be sent. If he does not approve a login with approval as ``"no"`` should be sent. If there is the possibility of data sync from the premium server and this is ``"unknown"`` the login will fail with an appropriate error asking the consumer of the api to set it to ``"yes"`` or ``"no"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "exchanges": [
                   {"location": "kraken", "name": "kraken1", "kraken_account_type": "starter"},
                   {"location": "poloniex", "name": "poloniex1"},
                   {"location": "binance", "name": "binance1"}
               ],
              "settings": {
                  "have_premium": true,
                  "version": "6",
                  "last_write_ts": 1571552172,
                  "premium_should_sync": true,
                  "include_crypto2crypto": true,
                  "last_data_upload_ts": 1571552172,
                  "ui_floating_precision": 2,
                  "taxfree_after_period": 31536000,
                  "balance_save_frequency": 24,
                  "include_gas_costs": true,
                  "ksm_rpc_endpoint": "http://localhost:9933",
                  "main_currency": "USD",
                  "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
                  "last_balance_save": 1571552172,
                  "submit_usage_analytics": true,
                  "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"],
                  "current_price_oracles": ["cryptocompare", "coingecko"],
                  "historical_price_oracles": ["cryptocompare", "coingecko"],
                  "taxable_ledger_actions": ["income", "airdrop"],
                  "ssf_0graph_multiplier": 2,
                  "non_sync_exchanges": [{"location": "binance", "name": "binance1"}]
              }
          },
          "message": ""
      }

   :resjson object result: For successful requests, result contains the currently connected exchanges,and the user's settings. For details on the user settings refer to the `Getting or modifying settings`_ section.
   :statuscode 200: Logged in successfully
   :statuscode 300: Possibility of syncing exists and the login was sent with sync_approval set to ``"unknown"``. Consumer of api must resend with ``"yes"`` or ``"no"``. In this case the result will contain an object with a payload for the message under the ``result`` key and the message under the ``message`` key. The payload has the following keys: ``local_size``, ``remote_size``, ``local_last_modified``, ``remote_last_modified``.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: Provided password is wrong for the user or some other authentication error.
   :statuscode 409: Another user is already logged in. User does not exist. There was a fatal error during the upgrade of the DB. Permission error while trying to access the directory where rotki saves data.
   :statuscode 500: Generic internal rotki error
   :statuscode 542: Internal rotki error relating to the Database. Check message for more details.

.. http:patch:: /api/(version)/users/(username)

   By doing a ``PATCH`` at this endpoint with action ``'logout'`` you can logout from your currently logged in account assuming that is ``username``. All user related data will be saved in the database, memory cleared and encrypted database connection closed.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/users/john HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "action": "logout"
      }

   :reqjson string action: The action to perform. Can only be ``"logout"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: Logged out successfully
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in, or current logged in user is different to the one requested for logout.
   :statuscode 500: Internal rotki error


.. http:patch:: /api/(version)/users/(username)

   By doing a ``PATCH`` at this endpoint without any action but by providing api_key and api_secret you can set the premium api key and secret pair for the user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/users/john HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "premium_api_key": "dadsfasdsd",
          "premium_api_secret": "fdfdsgsdmf"
      }

   :reqjson string premium_api_key: The new api key to set for rotki premium
   :reqjson string premium_api_secret: The new api secret to set for rotki premium

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: API key/secret set successfully
   :statuscode 400: Provided JSON is in some way malformed. For example invalid API key format
   :statuscode 401: Provided API key/secret does not authenticate.
   :statuscode 409: User is not logged in, or user does not exist
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/premium

   By doing a ``DELETE`` at this endpoint you can delete the premium api key and secret pair for the logged-in user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/premium HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: API key/secret deleted successfully
   :statuscode 400: Provided call is in some way malformed.
   :statuscode 409: User is not logged in, or user does not exist, or db operation error
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/premium/sync

   By doing a ``PUT`` at this endpoint you can backup or restore the database for the logged-in user using premium sync.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/premium/sync HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "action": "download"
      }

   :reqjson string action: The action to perform. Can only be one of ``"upload"`` or ``"download"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: API key/secret deleted successfully
   :statuscode 400: Provided call is in some way malformed.
   :statuscode 401: The user does not have premium access.
   :statuscode 500: Internal rotki error
   :statuscode 502: The external premium service could not be reached or returned unexpected response.

Modify user password
========================

.. http:patch:: /api/(version)/users/(username)/password

   By doing a ``PATCH`` at this endpoint you can change the specific user's password as long as that user is logged in.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/users/john/password HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "current_password": "supersecret",
          "new_password": "evenmoresecret"
      }

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: Password changed successfully
   :statuscode 401: Password mismatch
   :statuscode 400: Provided call is in some way malformed. For example a user who is not logged in has been specified.
   :statuscode 409: User is not logged in, or user does not exist, or db operation error
   :statuscode 500: Internal rotki error

Getting or modifying external services API credentials
=======================================================

.. http:get:: /api/(version)/external_services

   By doing a GET on the external services endpoint you can get all the credentials
   that the user has set for external services such as etherscan, cryptocompare e.t.c.

   Entries are returned only for the services that have had an api key setup.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/external_services HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "etherscan": {"api_key": "foooooookey"},
              "cryptocompare": {"api_key": "boooookey"},
              "opensea": {"api_key": "goooookey"}
          },
          "message": ""
      }

   :resjson object result: The result object contains as many entries as the external services. Each entry's key is the name and the value is another object of the form ``{"api_key": "foo"}``
   :statuscode 200: Querying of external service credentials was successful
   :statuscode 409: There is no logged in user
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/external_services

   By doing a PUT on the external services endpoint you can save credentials
   for external services such as etherscan, cryptocompare e.t.c.
   If a credential already exists for a service it is overwritten.

   Returns external service entries after the additions.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/external_services HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
          "services": [{"name": "etherscan", "api_key": "goookey"}]
      }

   :reqjson list services: The services parameter is a list of services along with their api keys.
   :reqjsonarr string name: Each entry in the list should have a name for the service. Valid ones are ``"etherscan"``, ``"cryptocompare"``, ``"beaconchain"``, ``"loopring"``, ``"covalent"`` and ``"opensea"``.
   :reqjsonarr string api_key: Each entry in the list should have an api_key entry

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "etherscan": {"api_key": "goookey"},
              "cryptocompare": {"api_key": "boooookey"}
          },
          "message": ""
      }

   :resjson object result: The result object contains as many entries as the external services. Each entry's key is the name and the value is another object of the form ``{"api_key": "foo"}``
   :statuscode 200: Saving new external service credentials was successful
   :statuscode 400: Provided JSON is in some way malformed, of invalid value provided.
   :statuscode 409: There is no logged in user
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/external_services

   By doing a DELETE on the external services endpoint you can delete credential
   entries for external services such as etherscan, cryptocompare e.t.c.

   Accepts a list of names whose credentials to delete. If credentials do not exist
   for an entry then nothing happens and deletion for that entry is silently skipped.

   Returns external service entries after the deletion.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/external_services HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
          "services": ["etherscan"]
      }

   :reqjson list services: A list of service names to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "cryptocompare": {"api_key": "boooookey"}
          },
          "message": ""
      }

   :resjson object result: The result object contains as many entries as the external services. Each entry's key is the name and the value is another object of the form ``{"api_key": "foo"}``
   :statuscode 200: Deleting external service credentials was successful
   :statuscode 400: Provided JSON is in some way malformed, of invalid value provided.
   :statuscode 409: There is no logged in user
   :statuscode 500: Internal rotki error

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

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "have_premium": false,
              "version": "6",
              "last_write_ts": 1571552172,
              "premium_should_sync": true,
              "include_crypto2crypto": true,
              "last_data_upload_ts": 1571552172,
              "ui_floating_precision": 2,
              "taxfree_after_period": 31536000,
              "balance_save_frequency": 24,
              "include_gas_costs": true,
              "ksm_rpc_endpoint": "http://localhost:9933",
              "main_currency": "USD",
              "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
              "last_balance_save": 1571552172,
              "submit_usage_analytics": true,
              "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"],
              "current_price_oracles": ["coingecko"],
              "historical_price_oracles": ["cryptocompare", "coingecko"],
              "taxable_ledger_actions": ["income", "airdrop"],
              "ssf_0graph_multiplier": 2,
              "non_sync_exchanges": [{"location": "binance", "name": "binance1"}],
              "cost_basis_method": "fifo",
          },
          "message": ""
      }

   .. _balance_save_frequency:

   :resjson int version: The database version
   :resjson int last_write_ts: The unix timestamp at which an entry was last written in the database
   :resjson bool premium_should_sync: A boolean denoting whether premium users database should be synced from/to the server
   :resjson bool include_crypto2crypto: A boolean denoting whether crypto to crypto trades should be counted.
   :resjson int last_data_upload_ts: The unix timestamp at which the last data upload to the server happened.
   :resjson int ui_floating_precision: The number of decimals points to be shown for floating point numbers in the UI. Can be between 0 and 8.
   :resjson int taxfree_after_period: The number of seconds after which holding a crypto in FIFO order is considered no longer taxable. Must be either a positive number, or -1. 0 is not a valid value. The default is 1 year, as per current german tax rules. Can also be set to ``-1`` which will then set the taxfree_after_period to ``null`` which means there is no taxfree period.
   :resjson int balance_save_frequency: The number of hours after which user balances should be saved in the DB again. This is useful for the statistics kept in the DB for each user. Default is 24 hours. Can't be less than 1 hour.
   :resjson bool include_gas_costs: A boolean denoting whether gas costs should be counted as loss in profit/loss calculation.
   :resjson string ksm_rpc_endpoint: A URL denoting the rpc endpoint for the Kusama node to use when contacting the Kusama blockchain. If it can not be reached or if it is invalid any default public node (e.g. Parity) is used instead.
   :resjson string dot_rpc_endpoint: A URL denoting the rpc endpoint for the Polkadot node to use when contacting the Polkadot blockchain. If it can not be reached or if it is invalid any default public node (e.g. Parity) is used instead.
   :resjson string main_currency: The asset to use for all profit/loss calculation. USD by default.
   :resjson string date_display_format: The format in which to display dates in the UI. Default is ``"%d/%m/%Y %H:%M:%S %Z"``.
   :resjson int last_balance_save: The timestamp at which the balances were last saved in the database.
   :resjson bool submit_usage_analytics: A boolean denoting whether or not to submit anonymous usage analytics to the rotki server.
   :resjson list active_module: A list of strings denoting the active modules with which rotki is running.
   :resjson list current_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting current prices.
   :resjson list historical_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting historical prices.
   :resjson list taxable_ledger_actions: A list of strings denoting the ledger action types that will be taken into account in the profit/loss calculation during accounting. All others will only be taken into account in the cost basis and will not be taxed.
   :resjson int ssf_0graph_multiplier: A multiplier to the snapshot saving frequency for 0 amount graphs. Originally 0 by default. If set it denotes the multiplier of the snapshot saving frequency at which to insert 0 save balances for a graph between two saved values.
   :resjson string cost_basis_method: Defines which method to use during the cost basis calculation. Currently supported: fifo, lifo.

   :statuscode 200: Querying of settings was successful
   :statuscode 409: There is no logged in user
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/settings

   By doing a PUT on the settings endpoint you can set/modify any settings you need. Look for possible modifiable settings below.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/settings HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
          "settings": {
              "ui_floating_precision": 4,
              "include_gas_costs": false
          }
      }

   :reqjson bool[optional] premium_should_sync: A boolean denoting whether premium users database should be synced from/to the server
   :reqjson bool[optional] include_crypto2crypto: A boolean denoting whether crypto to crypto trades should be counted.
   :reqjson int[optional] ui_floating_precision: The number of decimals points to be shown for floating point numbers in the UI. Can be between 0 and 8.
   :reqjson int[optional] taxfree_after_period: The number of seconds after which holding a crypto in FIFO order is considered no longer taxable. Must be either a positive number, or -1. 0 is not a valid value. The default is 1 year, as per current german tax rules. Can also be set to ``-1`` which will then set the taxfree_after_period to ``null`` which means there is no taxfree period.
   :reqjson int[optional] balance_save_frequency: The number of hours after which user balances should be saved in the DB again. This is useful for the statistics kept in the DB for each user. Default is 24 hours. Can't be less than 1 hour.
   :reqjson bool[optional] include_gas_costs: A boolean denoting whether gas costs should be counted as loss in profit/loss calculation.
   :reqjson string[optional] ksm_rpc_endpoint: A URL denoting the rpc endpoint for the Kusama node to use when contacting the Kusama blockchain. If it can not be reached or if it is invalid any default public node (e.g. Parity) is used instead.
   :reqjson string[optional] dot_rpc_endpoint: A URL denoting the rpc endpoint for the Polkadot node to use when contacting the Polkadot blockchain. If it can not be reached or if it is invalid any default public node (e.g. Parity) is used instead.
   :reqjson string[optional] main_currency: The FIAT currency to use for all profit/loss calculation. USD by default.
   :reqjson string[optional] date_display_format: The format in which to display dates in the UI. Default is ``"%d/%m/%Y %H:%M:%S %Z"``.
   :reqjson bool[optional] submit_usage_analytics: A boolean denoting wether or not to submit anonymous usage analytics to the rotki server.
   :reqjson list active_module: A list of strings denoting the active modules with which rotki should run.
   :reqjson list current_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting current prices.
   :reqjson list historical_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting historical prices.
   :reqjson list taxable_ledger_actions: A list of strings denoting the ledger action types that will be taken into account in the profit/loss calculation during accounting. All others will only be taken into account in the cost basis and will not be taxed.
   :resjson int ssf_0graph_multiplier: A multiplier to the snapshot saving frequency for 0 amount graphs. Originally 0 by default. If set it denotes the multiplier of the snapshot saving frequency at which to insert 0 save balances for a graph between two saved values.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "have_premium": false,
              "version": "6",
              "last_write_ts": 1571552172,
              "premium_should_sync": true,
              "include_crypto2crypto": true,
              "last_data_upload_ts": 1571552172,
              "ui_floating_precision": 4,
              "taxfree_after_period": 31536000,
              "balance_save_frequency": 24,
              "include_gas_costs": false,
              "ksm_rpc_endpoint": "http://localhost:9933",
              "main_currency": "USD",
              "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
              "last_balance_save": 1571552172,
              "submit_usage_analytics": true,
              "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"],
              "current_price_oracles": ["cryptocompare"],
              "historical_price_oracles": ["coingecko", "cryptocompare"],
              "taxable_ledger_actions": ["income", "airdrop"],
              "ssf_0graph_multiplier": 2,
              "non_sync_exchanges": [{"location": "binance", "name": "binance1"}]
          },
          "message": ""
      }

   :resjson object result: Same as when doing GET on the settings

   :statuscode 200: Modifying settings was successful
   :statuscode 400: Provided JSON is in some way malformed, of invalid value for a setting.
   :statuscode 409: No user is logged in or tried to set eth rpc endpoint that could not be reached.
   :statuscode 500: Internal rotki error

Getting backend arguments
================================

.. http:get:: /api/(version)/settings/configuration

   By doing a GET, you can retrieve the parameters used to initialize the backend.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/settings/configuration HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
           "result": {
                   "max_size_in_mb_all_logs": {
                           "value": 300,
                           "is_default": true
                   },
                   "max_logfiles_num": {
                           "value": 3,
                           "is_default": true
                   },
                   "sqlite_instructions": {
                           "value": 5000,
                           "is_default": true
                   }
           },
           "message": ""
       }

   :resjson object max_size_in_mb_all_logs: Maximum size in megabytes that will be used for all rotki logs.
   :resjson object max_num_log_files: Maximum number of logfiles to keep.
   :resjson object sqlite_instructions: Instructions per sqlite context switch. 0 means disabled.
   :resjson int value: Value used for the configuration.
   :resjson bool is_default: `true` if the setting was not modified and `false` if it was.

   :statuscode 200: Querying of the backend configuration was successful
   :statuscode 500: Internal rotki error

Adding information for web3 nodes
=================================

.. http:get:: /api/(version)/blockchains/(blockchain)/nodes

   By querying this endpoint the information for the nodes in the database will be returned

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/nodes HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   The following is an example response of querying Ethereum nodes information.

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": [
            {
                "identifier": 1,
                "name": "etherscan",
                "endpoint": "",
                "owned": false,
                "weight": "40.00",
                "active": true,
                "blockchain": "ETH"
            },
            {
                "identifier": 2,
                "name": "mycrypto",
                "endpoint": "https://api.mycryptoapi.com/eth",
                "owned": false,
                "weight": "20.00",
                "active": true,
                "blockchain": "ETH"
            },
            {
                "identifier": 3,
                "name": "blockscout",
                "endpoint": "https://mainnet-nethermind.blockscout.com/",
                "owned": false,
                "weight": "20.00",
                "active": true,
                "blockchain": "ETH"
            },
            {
                "identifier": 4,
                "name": "avado pool",
                "endpoint": "https://mainnet.eth.cloud.ava.do/",
                "owned": false,
                "weight": "20.00",
                "active": true,
                "blockchain": "ETH"
            }
        ],
        "message": ""
      }

   :resjson list result: A list with information about the web3 nodes.
   :resjson string name: Name and primary key of the node.
   :resjson string endpoint: rpc endpoint of the node. Will be used to query it.
   :resjson string weight: Weight of the node in the range of 0 to 100 with 2 decimals.
   :resjson string owned: True if the user owns the node or false if is a public node.
   :resjson string active: True if the node should be used or false if it shouldn't.

   :statuscode 200: Querying was successful
   :statuscode 409: No user is logged.
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/blockchains/(blockchain)/nodes

   By doing a PUT on this endpoint you will be able to add a new node to the list of nodes.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/ETH/nodes HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
        "name": "my_node",
        "endpoint": "http://localhost:8385",
        "owned": true,
        "weight": "40.30",
        "active": true
      }

   :resjson string name: Name and primary key of the node. This field has to be unique. This field cannot be empty or use the key ``etherscan``.
   :resjson string endpoint: rpc endpoint of the node. Will be used to query it.
   :resjson string owned: True if the user owns the node or false if is a public node.
   :resjson string weight: Weight of the node in the range of 0 to 100 with 2 decimals.
   :resjson string active: True if the node should be used or false if it shouldn't.

   :statuscode 200: Insertion was successful.
   :statuscode 409: No user is logged or entrie couldn't be created.
   :statuscode 500: Internal rotki error

.. http:patch:: /api/(version)/blockchains/(blockchain)/nodes

   By doing a PATCH on this endpoint you will be able to edit an already existing node entry with the information provided.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/blockchains/ETH/nodes HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
        "identifier": 8,
        "name": "my_node",
        "endpoint": "http://localhost:8386",
        "owned": true,
        "weight": 80,
        "active": false
      }

   :resjson int identifier: Id of the node that will be edited.
   :resjson string name: Name of the node that will be edited.
   :resjson string endpoint: rpc endpoint of the node. Will be used to query it.
   :resjson string owned: True if the user owns the node or false if is a public node.
   :resjson string weight: Weight of the node in the range of 0 to 100 with 2 decimals.
   :resjson string active: True if the node should be used or false if it shouldn't.

   :statuscode 200: Update was successful.
   :statuscode 409: No user is logged or entrie couldn't be updated.
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/blockchains/(blockchain)/nodes

   By doing a DELETE on this endpoint you will be able to delete an already existing node.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/ETH/nodes HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
        "identifier": 8
      }

   :resjson int identifier: Id of the node that will be deleted.

   :statuscode 200: Deletion was successful.
   :statuscode 409: No user is logged or failed to delete because the node name is not in the database.
   :statuscode 500: Internal rotki error


Query the result of an ongoing backend task
===========================================

.. http:get:: /api/(version)/tasks

   By querying this endpoint without any given task id a list of all pending and all completed tasks is returned.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/tasks HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   The following is an example response of querying pending/completed tasks

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "pending": [4, 23],
              "completed": [2]
          },
          "message": ""
      }

   :resjson list result: A mapping of "pending" to a list of pending task ids, and of "completed" to completed task ids.

   :statuscode 200: Querying was successful
   :statuscode 500: Internal rotki error

.. http:get:: /api/(version)/tasks/(task_id)

   By querying this endpoint with a particular task identifier you can get the result of the task if it has finished and the result has not yet been queried. If the result is still in progress or if the result is not found appropriate responses are returned.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/tasks/42 HTTP/1.1
      Host: localhost:5042

   **Example Completed Response**:

   The following is an example response of an async query to blockchain balances.

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "status": "completed",
              "outcome": {
                  "per_account": {"BTC": { "standalone": {
                      "1Ec9S8KSw4UXXhqkoG3ZD31yjtModULKGg": {
                              "amount": "10",
                              "usd_value": "70500.15"
                          }}
                  }},
                  "totals": {"BTC": {"amount": "10", "usd_value": "70500.15"}},
                  "status_code": 200
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

   The following is an example response of an async query that does not exist.

   .. sourcecode:: http

      HTTP/1.1 404 OK
      Content-Type: application/json

      {
          "result": {
              "status": "not-found",
              "outcome": null
          },
          "message": "No task with the task id 42 found"
      }

   :resjson string status: The status of the given task id. Can be one of ``"completed"``, ``"pending"`` and ``"not-found"``.
   :resjson any outcome: IF the result of the task id is not yet ready this should be ``null``. If the task has finished then this would contain the original task response. Inside the response can also be an optional status_code entry which would have been the status code of the original endpoint query had it not been made async.

   :statuscode 200: The task's outcome is successfully returned or pending
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 404: There is no task with the given task id
   :statuscode 409: No user is currently logged in
   :statuscode 500: Internal rotki error
   :statuscode 502: Problem contacting a remote service

Query the latest price of assets
===================================

.. http:post:: /api/(version)/assets/prices/latest

   Querying this endpoint with a list of assets and a target asset will return a mapping of assets to their prices in the target asset and an integer representing the oracle the price was gotten from. Providing an empty list or no target asset is an error.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/prices/latest HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "assets": ["BTC", "ETH", "eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA", "USD", "EUR"],
          "target_asset": "USD",
          "ignore_cache": true
      }

   :reqjson list assets: A list of assets to query their latest price.
   :reqjson string target_asset: The target asset against which to return the price of each asset in the list.
   :reqjson bool async_query: A boolean denoting whether the query should be made asynchronously or not. Missing defaults to false.
   :reqjson bool ignore_cache: A boolean denoting whether to ignore the latest price query cache. Missing defaults to false.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "assets": {
                  "BTC": ["34758.11", 1],
                  "ETH": ["1302.62", 2],
                  "EUR": ["1.209", 8],
                  "GBP": ["1.362", 8],
                  "eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA": ["20.29", 1],
                  "USD": ["1", 8]
              },
              "target_asset": "USD",
              "oracles": {
                "coingecko": 1,
                "cryptocompare": 2,
                "uniswapv2": 3,
                "uniswapv3": 4,
                "saddle": 5,
                "manualcurrent": 6,
                "blockchain": 7,
                "fiat": 8
              }
          },
          "message": ""
      }

   :resjson object result: A JSON object that contains the price of the assets in the target asset currency and the oracle used to query it.
   :resjson object assets: A map between an asset and its price.
   :resjson string target_asset: The target asset against which to return the price of each asset in the list.
   :resjson object oracles: A mapping of oracles to their integer id used.
   :statuscode 200: The USD prices have been successfully returned
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as cryptocompare/coingecko could not be reached or returned unexpected response.


Get current price and custom price for NFT assets
==================================================

.. http:get:: /api/(version)/nfts/prices

   Get current prices and whether they have been manually input or not for NFT assets.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/nfts/prices HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [
              {
                  "asset": "nft_uniqueid1",
                  "manually_input": true,
                  "price_asset": "ETH",
                  "price_in_asset": "1",
                  "usd_price": "2505.13"
              }, {
                  "asset": "nft_uniqueid2",
                  "manually_input": false,
                  "price_asset": "USD",
                  "price_in_asset": "155.13",
                  "usd_price": "155.13"
              }]
          "message": ""
      }

   :resjson object result: A list of results of assets along with their uds prices
   :statuscode 200: Successful query
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: Nft module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as cryptocompare/coingecko could not be reached or returned unexpected response.


Get all manually input latest prices
====================================

.. http:post:: /api/(version)/assets/prices/latest/all

   Retrieve all the manually input latest prices stored in the database.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/prices/latest/all HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"to_asset": "EUR"}

   :reqjson string from_asset: Optional. Asset identifier to use as filter in the `from` side of the prices.
   :reqjson string to_asset: Optional. Asset identifier to use as filter in the `to` side of the prices.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [
            {
              "from_asset": "ETH",
              "to_asset": "EUR",
              "price": "5"
            },
            {
              "from_asset": "USD",
              "to_asset": "EUR",
              "price": "25"
            }
          ]
          "message": ""
      }

   :resjson object result: A list of results with the prices along their `from_asset` and `to_asset`.
   :statuscode 200: Successful query
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error


Add manual current price for an asset
=============================================

.. http:put:: /api/(version)/assets/prices/current

   Giving a unique asset identifier and a price via this endpoint stores the current price for an asset. If given, this overrides all other current prices. At the moment this will only work for non fungible assets.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/prices/current HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "from_asset": "nft_unique_id",
          "to_asset": "EUR",
          "price": "150.55"
      }

   :reqjson string from_asset: The asset for which the price is given.
   :reqjson string to_asset: The asset against which the price is given.
   :reqjson string price: Custom price for the asset.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :resjson bool result: boolean for success
   :statuscode 200: Price successfully added
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: Nft module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as cryptocompare/coingecko could not be reached or returned unexpected response.

Delete an asset that has manual price set
=============================================

.. http:delete:: /api/(version)/assets/prices/current

   Deletes an asset that has as manual price set. IF the asset is not found or a manual price is not set a 409 is returned. At the moment this only works for nfts.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/prices/current HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"asset": "uniquenftid1"}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :resjson bool result: boolean for success
   :statuscode 200: Successful deletion
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: Asset not found or no manual price exists or nft module not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as cryptocompare/coingecko could not be reached or returned unexpected response.

Query the current exchange rate for select assets
======================================================

.. http:get:: /api/(version)/exchange_rates

   Querying this endpoint with a list of strings representing some assets will return a dictionary of their current exchange rates compared to USD. If an asset's price could not be queried then zero will be returned as the price.

   .. note::
      This endpoint also accepts parameters as query arguments. List as a query argument here would be given as: ``?currencies=EUR,CNY,GBP``

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/exchange_rates HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": true, "currencies": ["EUR", "CNY", "GBP", "BTC"]}

   :query strings-list currencies: A comma separated list of currencies to query. e.g.: /api/1/fiat_exchange_rates?currencies=EUR,CNY,GBP
   :reqjson list currencies: A list of assets to query

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"EUR": "0.8973438622", "CNY": "7.0837221823", "GBP": "0.7756191673", "BTC": "19420.23"},
          "message": ""
      }

   :resjson object result: A JSON object with each element being an asset symbol and each value its USD exchange rate. If a particular asset could not have its price queried, it will return a zero price.
   :statuscode 200: The exchange rates have been successfully returned
   :statuscode 400: Provided JSON is in some way malformed. Empty currencies list given
   :statuscode 500: Internal rotki error

Query the historical price of assets
======================================

.. http:post:: /api/(version)/assets/prices/historical

   Querying this endpoint with a list of lists of asset and timestamp, and a target asset will return an object with the price of the assets at the given timestamp in the target asset currency. Providing an empty list or no target asset is an error.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/prices/historical HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

       {
          "assets_timestamp": [["BTC", 1579543935], ["BTC", 1611166335], ["GBP", 1579543935], ["EUR", 1548007935]],
          "target_asset": "USD"
       }

   :reqjson list assets_timestamp: A list of lists of asset and timestamp
   :reqjson string target_asset: The target asset against which to return the price of each asset in the list

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "assets": {
                  "BTC": {
                      "1579543935": "24361.55",
                      "1611166335": "34966.64"
                  },
                  "EUR": {
                      "1548007935": "1.1402"
                  },
                  "GBP": {
                      "1579543935": "1.2999120493"
                  }
              },
              "target_asset": "USD"
          },
          "message": ""
      }

   :resjson object result: A JSON object that contains the price of each asset for the given timestamp in the target asset currency.
   :resjson object assets: A map between an asset and a map that contains the asset price at the specific timestamp.
   :resjson string target_asset: The target asset against which to return the price of each asset in the list.
   :statuscode 200: The historical USD prices have been successfully returned
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as cryptocompare/coingecko could not be reached or returned unexpected response.



.. http:put:: /api/(version)/assets/prices/historical

    Manually adds the price of an asset against another asset at a certain timestamp to the database.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/prices/historical HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

       {
            "from_asset": "eip155:1/erc20:0xD71eCFF9342A5Ced620049e616c5035F1dB98620",
            "to_asset": "USD",
            "timestamp": 1611166335,
            "price": "1.20"
       }

   :reqjson string from_asset: The asset for which the price is given.
   :reqjson string to_asset: The asset against which the price is given.
   :reqjson int timestamp: The unix timestamp for which to save the price
   :reqjson string price: Price at the timestamp given.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson object result: true if the manual price was correctly stored in the database, false otherwise.
   :statuscode 200: Operation sent to database.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 500: Internal rotki error


.. http:patch:: /api/(version)/assets/prices/historical

    Edits price for a manually added price if it already exists in the database. Returns false
    if no entry was updated.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/prices/historical HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

       {
            "from_asset": "eip155:1/erc20:0xD71eCFF9342A5Ced620049e616c5035F1dB98620",
            "to_asset": "USD",
            "timestamp": 1611166335,
            "price": "1.20"
       }

   :reqjson string from_asset: The asset for which the price is given.
   :reqjson string to_asset: The asset against which the price is given.
   :reqjson int timestamp: The unix timestamp for which the price was saved
   :reqjson string price: New price at the timestamp given.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson object result: true if any entry was updated, false otherwise.
   :statuscode 200: Operation sent to database.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 500: Internal rotki error


.. http:get:: /api/(version)/assets/prices/historical

    Queries prices of an asset against another asset at a certain timestamp to the database.
    If none of the fields are provided returns all the prices manually added.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/prices/historical HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

       {
          "from_asset": "eip155:1/erc20:0xD71eCFF9342A5Ced620049e616c5035F1dB98620"
       }

   :reqjson string from_asset: Optional. The from_asset for which the price is retrieved.
   :reqjson string to_asset: Optional. The to_asset for which the price is retrieved.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [
            {
              "from_asset": "eip155:1/erc20:0xD533a949740bb3306d119CC777fa900bA034cd52",
              "to_asset": "USD",
              "timestamp": 1611166335,
              "price": "1.20"
            },
            {
              "from_asset": "eip155:1/erc20:0xD533a949740bb3306d119CC777fa900bA034cd52",
              "to_asset": "USD",
              "timestamp": 1611166340,
              "price": "1.40"
            }
          ],
          "message": ""
      }

   :resjson object result: List with information for each historical price.
   :statuscode 200: Operation executed.
   :statuscode 400: Provided information is in some way malformed.
   :statuscode 500: Internal rotki error


.. http:delete:: /api/(version)/assets/prices/historical

    Deletes price of an asset against another asset at a certain timestamp from the database.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/prices/historical HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

       {
        "from_asset": "eip155:1/erc20:0xD71eCFF9342A5Ced620049e616c5035F1dB98620",
        "to_asset": "USD",
        "timestamp": 1611166335
       }

   :reqjson string from_asset: The asset for which the price is given.
   :reqjson string to_asset: The asset against which the price is given.
   :reqjson int timestamp: The unix timestamp for which to save the price

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

   :statuscode 200: true if any entry was deleted, false otherwise.
   :statuscode 400: Provided information is in some way malformed.
   :statuscode 500: Internal rotki error



Get a list of setup exchanges
==============================

.. http:get:: /api/(version)/exchanges

   Doing a GET on this endpoint will return a list of which exchanges are currently setup for the logged in user and with which names.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/exchanges HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [
               {"location": "kraken", "name": "kraken1", "kraken_account_type": "starter"},
               {"location": "poloniex", "name": "poloniex1"},
               {"location": "binance", "name": "binance1"}
           ],
          "message": ""
      }

   :resjson list result: A list of exchange location/name pairs that have been setup for the logged in user.
   :statuscode 200: The exchanges list has been successfully setup
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error

Setup or remove an exchange
============================

.. http:put:: /api/(version)/exchanges

   Doing a PUT on this endpoint with an exchange's name, location, api key and secret will setup the exchange for the current user. Also for some exchanges additional optional info can be provided.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/exchanges HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"name": "my kraken key", "location": "kraken", "api_key": "ddddd", "api_secret": "ffffff", "passphrase": "secret", "binance_markets": ["ETHUSDC", "BTCUSDC"], "ftx_subaccount": "Dragon"}

   :reqjson string name: A name to give to this exchange's key
   :reqjson string location: The location of the exchange to setup
   :reqjson string api_key: The api key with which to setup the exchange
   :reqjson string api_secret: The api secret with which to setup the exchange
   :reqjson string passphrase: An optional passphrase, only for exchanges, like coinbase pro, which need a passphrase.
   :reqjson string kraken_account_type: An optional setting for kraken. The type of the user's kraken account. Valid values are "starter", "intermediate" and "pro".
   :reqjson list binance_markets: An optional setting for binance and binanceus. A list of string for markets that should be queried.
   :reqjson string ftx_subaccount: An optional setting for FTX. This sets the subaccount that will be queried from FTX.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :resjson bool result: A boolean indicating success or failure
   :statuscode 200: The exchange has been successfully setup
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in. The exchange has already been registered. The API key/secret is invalid or some other error.
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/exchanges

   Doing a DELETE on this endpoint for a particular exchange name will delete the exchange from the database for the current user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/exchanges HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"name": "my kraken key", "location": "kraken"}

   :reqjson string name: The name of the exchange whose key to delete
   :reqjson string location: The location of the exchange to delete

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :resjson bool result: A boolean indicating success or failure
   :statuscode 200: The exchange has been successfully deleted
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in. The exchange is not registered or some other error
   :statuscode 500: Internal rotki error

Edit an exchange entry
========================

.. http:patch:: /api/(version)/exchanges

   Doing a PATCH on this endpoint with an exchange's name and location and the various attributes will result in editing it.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/exchanges HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"name": "my kraken key", "location": "kraken", "new_name": "my_kraken", "api_key": "my_new_api_key", "api_secret": "my_new_api_secret", "passphrase": "my_new_passphrase", "kraken_account_type": "intermediate"}

   :reqjson string name: The name of the exchange key to edit
   :reqjson string location: The location of the exchange to edit
   :reqjson string new_name: Optional. If given this will be the new name for the exchange credentials.
   :reqjson string api_key: Optional. If given this will be the new api key for the exchange credentials.
   :reqjson string api_secret: Optional. If given this will be the new api secret for the exchange credentials.
   :reqjson string passphrase: Optional. If given this will be the new passphrase. Only for exchanges, like coinbase pro, which need a passphrase.
   :reqjson string kraken_account_type: Optional. An optional setting for kraken. The type of the user's kraken account. Valid values are "starter", "intermediate" and "pro".

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :resjson bool result: A boolean indicating success if all went well. If there is an error then the usual result: null and message having a value format is followed.
   :statuscode 200: The exchange has been successfully edited
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in. The exchange can not be found. The new exchange credentials were invalid.
   :statuscode 500: Internal rotki error

Querying the balances of exchanges
====================================

.. http:get:: /api/(version)/exchanges/balances/(location)

   Doing a GET on the appropriate exchanges balances endpoint will return the balances of all assets currently held in that exchange. If no name is provided then the balance of all exchanges is returned.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``. Passing it as a query argument here would be given as: ``?async_query=true``.

   .. note::
      This endpoint uses a cache. If queried within the ``CACHE_TIME`` the cached value will be returned. If you want to skip the cache add the ``ignore_cache: true`` argument. Can also be passed as a query argument.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/exchanges/balances/binance HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.
   :param bool async_query: Boolean denoting whether this is an asynchronous query or not
   :param bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.

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

   :resjson object result: If successful contains the balances of each asset held in the exchange. Each key of the object is an asset's symbol. Then the value is another object.  In the ``"amount"`` key of that object is the amount held in the asset. And in the ``"usd_value"`` key is the equivalent $ value as of this moment.
   :statuscode 200: Balances successfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in.Exchange is not registered or some other exchange query error. Check error message for details.
   :statuscode 500: Internal rotki error

.. http:get:: /api/(version)/exchanges/balances/

   Doing a GET on the exchanges balances endpoint will return the balances of all assets currently held in all exchanges.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/exchanges/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :param bool async_query: Boolean denoting whether this is an asynchronous query or not

   .. _balances_result:

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "kraken": {
                  "BTC": {"amount": "1", "usd_value": "7540.15"},
                  "ETH": {"amount": "10", "usd_value": "1650.53"}
              },
              "binance": {
                  "ETH": {"amount": "20", "usd_value": "3301.06"},
              }
          },
          "message": ""
      }

   :resjson object result: If successful contains the balances of each asset held in the exchange. Each key of the object is an asset's symbol. Then the value is another object.  In the ``"amount"`` key of that object is the amount held in the asset. And in the ``"usd_value"`` key is the equivalent $ value as of this moment.
   :statuscode 200: Balances successfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in. Some exchange query error. Check error message for details.
   :statuscode 500: Internal rotki error


Purging locally saved data for exchanges
=========================================

.. http:delete:: /api/(version)/exchanges/data/(location)

   Doing a DELETE on the appropriate exchanges trades endpoint will delete the cached trades, deposits and withdrawals for that exchange. If no exchange is given then all exchanges will be affected. Next time exchange history is queried, everything will be queried again, and may take some time.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/exchanges/delete/binance HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Data successfully purged.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in. Exchange is not registered or some other error. Check error message for details.
   :statuscode 500: Internal rotki error

Purging locally saved ethereum transactions
===========================================

.. http:delete:: /api/(version)/blockchains/ETH/transactions

   Doing a DELETE on the transactions endpoint for ETH will purge all locally saved transaction data. Next time transactions are queried all of them will be queried again for all addresses and may take some time.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/ETH/transactions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Data successfully purged.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error


Purging locally saved data for ethereum modules
====================================================

.. http:delete:: /api/(version)/blockchains/ETH/modules/(name)/data

   Doing a DELETE on the data of a specific ETH module will purge all locally saved data for the module. Can also purge all module data by doing a ``DELETE`` on ``/api/(version)/blockchains/ETH/modules/data`` in which case all module data will be purged.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/ETH/modules/uniswap/data HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {}

   :reqjson string name: The name of the module whose data to delete. Can be one of the supported ethereum modules. The name can be omitted by doing a ``DELETE`` on ``/api/(version)/blockchains/ETH/modules/data`` in which case all module data will be purged.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Data successfully purged.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error


Getting all available counterparties
=====================================

.. http:get:: /api/(version)/blockchains/ETH/modules/data/counterparties

    Doing a GET on the counterparties endpoint will return all known counterparties

    **Example Request**

    .. http:example:: curl wget httpie python-requests

    GET /api/(version)/blockchains/ETH/modules/data/counterparties HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

    {}

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {"result": ["gas", "gnosis-chain"], "message": ""}

    :resjson object result: Contains all counterparties known to the app
    :statuscode 200: Success
    :statuscode 500: Internal rotki error

Request creation of oracle price cache
====================================================

.. http:post:: /api/(version)/oracles/(name)/cache

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a POST on this endpoint with the appropriate arguments will request the creation of a price cache for the oracle. If it already exists it will be appended to or recreated depending on the given arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/oracles/cryptocompare/cache HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_asset": "ETH", "to_asset": "EUR", "purge_old": false, "async_query": true}

   :reqjson string name: The name of the oracle for which to create the cache. Valid values are ``"cryptocompare"`` and ``"coingecko"``.
   :reqjson string from_asset: The from asset of the pair for which to generate the cache
   :reqjson string to_asset: The to asset of the pair for which to generate the cache
   :reqjson bool purge_old: If true, and an old cache exists it will be completely removed and the whole cache recreated. If false, only the parts of the time range for which no cache exists will be queried. By default this is false.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Cache successfully created.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: The oracle could not be queried due to an error on their side.

Delete an oracle price cache
================================

.. http:delete:: /api/(version)/oracles/(name)/cache

   Doing a delete on this endpoint with the appropriate arguments will request delete a specific pair's price cache for an oracle.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/oracles/cryptocompare/cache HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_asset": "ETH", "to_asset": "EUR"}

   :reqjson string name: The name of the oracle for which to create the cache. Valid values are ``"cryptocompare"`` and ``"coingecko"``.
   :reqjson string from_asset: The from asset of the pair for which to generate the cache
   :reqjson string to_asset: The to asset of the pair for which to generate the cache


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Cache successfully delete.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error

Get oracle price cache data
=============================

.. http:get:: /api/(version)/oracles/(name)/cache

   Doing a GET on this endpoint will return information on all cached prices and pairs for the given oracle.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/oracles/cryptocompare/cache HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": true}

   :reqjson string name: The name of the oracle for which to create the cache. Valid values are ``"cryptocompare"`` and ``"coingecko"``.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
              "from_asset": "ETH",
              "to_asset": "EUR",
              "from_timestamp": "1417447629",
              "to_timestamp": "1611848905",
          }, {
              "from_asset": "BTC",
              "to_asset": "USD",
              "from_timestamp": "1437457629",
              "to_timestamp": "1601348905",
          }],
          "message": ""
      }

   :resjson list result: A list of cache results. Each entry contains the from/to asset of the cache pair and the range of the cache.
   :resjson string from_asset: The identifier of the from asset.
   :resjson string to_asset: The identifier of the to asset.
   :resjson int from_timestamp: The timestamp at which the price cache for the pair starts
   :resjson int to_timestamp: The timestamp at which the price cache for the pair ends

   :statuscode 200: Cache successfully delete.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error

Get supported oracles
=======================

.. http:get:: /api/(version)/oracles/

   Doing a GET on this endpoint will return information on all supported oracles.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/oracles/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "history": [{
                  "id": "cryptocompare",
                  "name": "Cryptocompare"
              }, {
                  "id": "coingecko",
                  "name": "Coingecko"
              }],
              "current": [{
                  "id": "cryptocompare",
                  "name": "Cryptocompare"
              }, {
                  "id": "coingecko",
                  "name": "Coingecko"
              }],

          "message": ""
      }

   :resjson object result: A mapping of all supported current and historical oracles

   :statuscode 200: Oracles successfully queried
   :statuscode 500: Internal rotki error

Query supported ethereum modules
=====================================

.. http:get:: /api/(version)/blockchains/ETH/modules

   Doing a GET on this endpoint will return all supported ethereum modules

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/ETH/modules HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": [{
              "id": "uniswap",
              "name": "Uniswap"
          }], [{
              "id": "yearn_vaults",
              "name": "Yearn Vaults"
          }], [{
              "id": "makerdao_dsr",
              "name": "MakerDAO DSR"
          }]
          "message": "" }

   :resjson object result: A list of all supported module each with its id and human readable name

   :statuscode 200: Data successfully purged.
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error

Querying ethereum transactions
=================================

.. http:get:: /api/(version)/blockchains/ETH/transactions/(address)

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a GET on the transactions endpoint for ETH will query all ethereum transactions for all the tracked user addresses. Caller can also specify an address to further filter the query as a from address. Also they can limit the queried transactions by timestamps and can filter transactions by related event's properties (asset, protocols and whether to exclude transactions with ignored assets). If the user is not premium and has more than the transaction limit then the returned transaction will be limited to that number. Any filtering will also be limited. Transactions are returned most recent first.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/transactions/0xdAC17F958D2ee523a2206206994597C13D831ec7/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1514764800, "to_timestamp": 1572080165, "only_cache": false}

   :reqjson int limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: This is the list of attributes of the transaction by which to order the results.
   :reqjson list[bool] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.
   :reqjson int from_timestamp: The timestamp after which to return transactions. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return transactions. If not given all transactions from ``from_timestamp`` until now are returned.
   :reqjson bool only_cache: If true then only the ethereum transactions in the DB are queried.
   :reqjson string asset: Optional. Serialized asset to filter by.
   :reqjson list protocols: Optional. Protocols (counterparties) to filter by. List of strings.
   :reqjson bool exclude_ignored_assets: Optional. Whether to exclude transactions with ignored assets. Default true.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "entries": [{
            "entry": {
              "tx_hash": "0x18807cd818b2b50a2284bda2dfc39c9f60607ccfa25b1a01143e934280675eb8",
              "timestamp": 1598006527,
              "block_number": 10703085,
              "from_address": "0x3CAdbeB58CB5162439908edA08df0A305b016dA8",
              "to_address": "0xF9986D445ceD31882377b5D6a5F58EaEa72288c3",
              "value": "0",
              "gas": "61676",
              "gas_price": "206000000000",
              "gas_used": "37154",
              "input_data": "0xa9059cbb0000000000000000000000001934aa5cdb0677aaa12850d763bf8b60e7a3dbd4000000000000000000000000000000000000000000000179b9b29a80ae20ca00",
              "nonce": 2720
            },
            "ignored_in_accounting": false,
            "decoded_events": [{
              "entry": {
                "identifier": 1,
                "asset": "ETH",
                "balance": {"amount": "0.00863351371344", "usd_value": "0"},
                "counterparty": "gas",
                "event_identifier": "0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
                "event_subtype": "fee",
                "event_type": "spend",
                "location": "blockchain",
                "location_label": "0x6e15887E2CEC81434C16D587709f64603b39b545",
                "notes": "Burned 0.00863351371344 ETH for gas",
                "sequence_index": 0,
                "timestamp": 1642802807
              },
              "customized": false
            }, {
              "entry": {
                "identifier": 2,
                "asset": "ETH",
                "balance": {"amount": "0.096809163374771208", "usd_value": "0"},
                "counterparty": "0xA090e606E30bD747d4E6245a1517EbE430F0057e",
                "event_identifier": "0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
                "event_subtype": null,
                "event_type": "spend",
                "location": "blockchain",
                "location_label": "0x6e15887E2CEC81434C16D587709f64603b39b545",
                "notes": "Send 0.096809163374771208 ETH 0x6e15887E2CEC81434C16D587709f64603b39b545 -> 0xA090e606E30bD747d4E6245a1517EbE430F0057e",
                "sequence_index": 1,
                "timestamp": 1642802807
              },
              "customized": true
            }]
          }, {
            "entry": {
              "tx_hash": "0x19807cd818b2b50a2284bda2dfc39c9f60607ccfa25b1a01143e934280635eb7",
              "timestamp": 1588006528,
              "block_number": 10700085,
              "from_address": "0x1CAdbe158CB5162439901edA08df0A305b016dA1",
              "to_address": "0xA9916D445ce1318A2377b3D6a5F58EaEa72288a1",
              "value": "56000300000000000000000",
              "gas": "610676",
              "gas_price": "106000000000",
              "gas_used": "270154",
              "input_data": "0x",
              "nonce": 55
            },
            "ignored_in_accounting": true,
            "decoded_events": [{
              "entry": {
                "identifier": 3,
                "asset": "ETH",
                "balance": {"amount": "0.00863351371344", "usd_value": "0"},
                "counterparty": "gas",
                "event_identifier": "0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
                "event_subtype": "fee",
                "event_type": "spend",
                "location": "blockchain",
                "location_label": "0x6e15887E2CEC81434C16D587709f64603b39b545",
                "notes": "Burned 0.00863351371344 ETH for gas",
                "sequence_index": 0,
                "timestamp": 1642802807
              },
              "customized": false
            }]
          }],
          "entries_found": 95,
          "entries_limit": 500,
          "entries_total": 1000

      },
        "message": ""
      }

   :resjson object result: A list of transaction entries to return for the given filter.
   :resjson object entry: A single transaction entry
   :resjson bool ignored_in_accounting: A boolean indicating whether this transaction should be ignored in accounting or not
   :resjson list decoded_events: A list of decoded events for the given transaction. Each even is an object comprised of the event entry and a boolean denoting if the event has been customized by the user or not.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_limit: The limit of entries if free version. -1 for premium.
   :resjson int entries_total: The number of total entries ignoring all filters.

   :statuscode 200: Transactions successfully queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Request transactions event decoding
=======================================

.. http:post:: /api/(version)/blockchains/ETH/transactions

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a POST on the transactions endpoint for ETH will request a decoding of the given transactions and generation of decoded events. That basically entails querying the transaction receipts for each transaction hash and then decoding all events. If events are already queried and ignore_cache is true they will be deleted and requeried.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/blockchains/ETH/transactions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": true, "tx_hashes": ["0xe33041d0ae336cd4c588a313b7f8649db07b79c5107424352b9e52a6ea7a9742", "0xed6e64021f960bb40f11f1c00ec1d5ca910471e75a080e42b347ba5af7e73516"], "ignore_cache": false}

   :reqjson list tx_hashes[optional]: The list of transaction hashes to request decoding for. If the list of transaction hashes is not passed then all transactions are decoded. Passing an empty list is not allowed.
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not. This is always false by default. If true is given then the decoded events will be deleted and requeried.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true,
        "message": ""
      }


   :statuscode 200: Transactions successfully decoded.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: One of the given hashes does not correspond to a transaction according to the nodes we contacted.
   :statuscode 500: Internal rotki error
   :statuscode 502: Problem contacting a remote service

Querying tags
=================

.. http:get:: /api/(version)/tags

   Doing a GET on the tags endpoint will query information about all the tags that are stored in the app


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/tags/ HTTP/1.1
      Host: localhost:5042

   .. _tags_response:

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "hw": {
                  "name": "hw",
                  "description": "Accounts that are stored in hardware wallets",
                  "background_color": "fafafa",
                  "foreground_color": "ffffff"
              },
              "mobile": {
                  "name": "mobile",
                  "description": "Accounts that are stored in mobile devices",
                  "background_color": "ffffff",
                  "foreground_color": "fafafa"
             }},
          "message": ""
      }

   :reqjson object result: A mapping of tag names to tag data.
   :reqjson string name: The tag's name. Is always lowercase.
   :reqjson string description: A description of what the tag is for.
   :resjson string background_color: The background color to render the tag in the frontend with.
   :resjson string foreground_color: The foreground color to render the tag in the frontend with.

   :statuscode 200: Tags successfully queried.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

Adding new tags
===================

.. http:put:: /api/(version)/tags

   Doing a PUT on the tags endpoint will add a new tag to the application


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/tags/ HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript
      Content-Type: application/json;charset=UTF-8

      {
            "name": "not public",
            "description": "Accounts that are not publicly associated with me",
            "background_color": "f8f8f8",
            "foreground_color": "f1f1f1"
      }

   :reqjson string name: The name to give to the new tag. The name of the tag (case insensitive check) must not already exist.
   :reqjson string description: The description for the new tag you are creating.
   :reqjson string background_color: The color with which the tag's background will be rendered. Format is RGB hexstring.
   :reqjson string foreground_color: The color with which the tag's foreground will be rendered. Format is RGB hexstring.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "hw": {
                  "name": "hw",
                  "description": "Accounts that are stored in hardware wallets",
                  "background_color": "fafafa",
                  "foreground_color": "ffffff"
              },
              "mobile": {
                  "name": "mobile",
                  "description": "Accounts that are stored in mobile devices",
                  "background_color": "ffffff",
                  "foreground_color": "fafafa"
             },
              "not public": {
                  "name": "not public",
                  "description": "Accounts that are not publicly associated with me",
                  "background_color": "f8f8f8",
                  "foreground_color": "f1f1f1"
             }
          },
          "message": ""
      }

   :reqjson object result: A mapping of the tags rotki knows about including our newly added tag. Explanation of the response format is seen `here <tags_response_>`_

   :statuscode 200: Tag successfully created.
   :statuscode 400: Provided request JSON is in some way malformed.
   :statuscode 409: User is not logged in. Tag with the same name already exists.
   :statuscode 500: Internal rotki error

Editing a tag
==============

.. http:patch:: /api/(version)/tags

   Doing a PATCH on the tags endpoint will edit an already existing tag


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/tags/ HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript
      Content-Type: application/json;charset=UTF-8

      {
            "name": "not public",
            "description": "Accounts that are private",
            "background_color": "f9f9f9",
            "foreground_color": "f2f2f2"
      }

   :reqjson string name: The name of the already existing tag. The name lookup will be a case-insensitive check.
   :reqjson string[optional] description: If given replaces the tag's description.
   :reqjson string[optional] background_color: If given replaces the tag's background color. Format is RGB hexstring.
   :reqjson string[optional foreground_color: If given replaces the tag's background color. Format is RGB hexstring.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "hw": {
                  "name": "hw",
                  "description": "Accounts that are stored in hardware wallets",
                  "background_color": "fafafa",
                  "foreground_color": "ffffff"
              },
              "mobile": {
                  "name": "mobile",
                  "description": "Accounts that are stored in mobile devices",
                  "background_color": "ffffff",
                  "foreground_color": "fafafa"
             },
              "not public": {
                  "name": "not public",
                  "description": "Accounts that are private",
                  "background_color": "f9f9f9",
                  "foreground_color": "f2f2f2"
             }
          },
          "message": ""
      }

   :reqjson object result: A mapping of the tags rotki knows about including our newly edited tag. Explanation of the response format is seen `here <tags_response_>`_

   :statuscode 200: Tag successfully created.
   :statuscode 400: Provided request JSON is in some way malformed. Or no field to edit was given.
   :statuscode 409: User is not logged in. Tag with the given name does not exist.
   :statuscode 500: Internal rotki error

Deleting a tag
==============

.. http:delete:: /api/(version)/tags

   Doing a DELETE on the tags endpoint will remove an existing tag


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/tags/ HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript
      Content-Type: application/json;charset=UTF-8

      {
            "name": "not public"
      }

   :reqjson string name: The name of the existing tag to remove. The name lookup will be a case-insensitive check.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "hw": {
                  "name": "hw",
                  "description": "Accounts that are stored in hardware wallets",
                  "background_color": "fafafa",
                  "foreground_color": "ffffff"
              },
              "mobile": {
                  "name": "mobile",
                  "description": "Accounts that are stored in mobile devices",
                  "background_color": "ffffff",
                  "foreground_color": "fafafa"
             }
          },
          "message": ""
      }

   :reqjson list result: A mapping of the tags rotki knows about, now without the tag we just deleted. Explanation of the response format is seen `here <tags_response_>`_

   :statuscode 200: Tag successfully removed.
   :statuscode 400: Provided request JSON is in some way malformed.
   :statuscode 409: User is not logged in. Tag with the given name does not exist.
   :statuscode 500: Internal rotki error

Querying onchain balances
==========================

.. http:get:: /api/(version)/balances/blockchains/(blockchain)/

   Doing a GET on the blockchains balances endpoint will query on-chain balances for the accounts of the user. Doing a GET on a specific blockchain will query balances only for that chain. Available blockchain names are: ``BTC``, ``ETH``, ``ETH2``, ``KSM``, ``DOT`` and ``AVAX``.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``. Passing it as a query argument here would be given as: ``?async_query=true``.

   .. note::
      This endpoint uses a cache. If queried within the ``CACHE_TIME`` the cached value will be returned. If you want to skip the cache add the ``ignore_cache: true`` argument. Can also be passed as a query argument.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/balances/blockchains/ HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.
   :param bool async_query: Boolean denoting whether this is an asynchronous query or not
   :param bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.

.. _blockchain_balances_result:

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "per_account": {
                  "BTC": {
                      "standalone": {
                          "3Kb9QPcTUJKspzjQFBppfXRcWew6hyDAPb": {
                              "amount": "0.5", "usd_value": "3770.075"
                          }, "33hjmoU9XjEz8aLxf44FNGB8TdrLkAVBBo": {
                              "amount": "0.5", "usd_value": "3770.075"
                      }},
                      "xpubs": [{
                              "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
                              "derivation_path": "m/0/0",
                              "addresses": {
                                  "1LZypJUwJJRdfdndwvDmtAjrVYaHko136r": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "1AMrsvqsJzDq25QnaJzX5BzEvdqQ8T6MkT": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}, {
                              "xpub": "zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q",
                              "derivation_path": "m",
                              "addresses": {
                                  "bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}]
                   },
                   "ETH": { "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B": {
                       "assets": {
                           "ETH": {"amount": "10", "usd_value": "1650.53"},
                           "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "15", "usd_value": "15.21"}
                       },
                       "liabilities": {
                           "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "20", "usd_value": "20.35"}
                       }
                  }},
                   "ETH2": { "0x9675faa8d15665e30d31dc10a332828fa15e2c7490f7d1894d9092901b139801ce476810f8e1e0c7658a9abdb9c4412e": {
                       "assets": {
                           "ETH2": {"amount": "33.12", "usd_value": "45243.21"},
                       },
                       "0x97bc980f17f42a994827899e0720cee288b538646292ce7c866a5a5c9d1002cd1fb7a80195445be2670b64cf4d1c215e": {
                       "assets": {
                           "ETH2": {"amount": "32.45", "usd_value": "40241.55"},
                       },
                  }},
              },
              "totals": {
                  "assets": {
                      "BTC": {"amount": "1", "usd_value": "7540.15"},
                      "ETH": {"amount": "10", "usd_value": "1650.53"},
                      "ETH2": {"amount": "65.57", "usd_value": "85484.76"},
                      "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "15", "usd_value": "15.21"}
                  },
                  "liabilities": {
                      "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "20", "usd_value": "20.35"}
                  }
              }
          },
          "message": ""
      }

   :resjson object per_account: The blockchain balances per account per asset. Each element of this object has a blockchain asset as its key. Then each asset has an address for that blockchain as its key and each address an object with the following keys: ``"amount"`` for the amount stored in the asset in the address and ``"usd_value"`` for the equivalent $ value as of the request. Ethereum accounts have a mapping of tokens owned by each account. ETH accounts may have an optional liabilities key. This would be the same as assets. BTC accounts are separated in standalone accounts and in accounts that have been derived from an xpub. The xpub ones are listed in a list under the ``"xpubs"`` key. Each entry has the xpub, the derivation path and the list of addresses and their balances.
   :resjson object total: The blockchain balances in total per asset. Has 2 keys. One for assets and one for liabilities. The liabilities key may be missing if no liabilities exist.

   :statuscode 200: Balances successfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in. Invalid blockchain, or problems querying the given blockchain
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan or blockchain.info could not be reached or returned unexpected response.

Querying all balances
==========================

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint uses a cache. If queried within the ``CACHE_TIME`` the cached value will be returned. If you want to skip the cache add the ``ignore_cache: true`` argument. Can also be passed as a query argument.

.. http:get:: /api/(version)/balances

   Doing a GET on the balances endpoint will query all balances/debt across all locations for the user. That is exchanges, blockchains and all manually tracked balances. And it will return an overview of all queried balances. This also includes any debt/liabilities.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/balances HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": true}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.
   :reqjson bool save_data: Boolean denoting whether to force save data even if the balance save frequency has not lapsed (see `here <balance_save_frequency_>`_ ).
   :reqjson bool ignore_error: Boolean denoting whether to still save a snapshot of balances even if there is an error. Off by default. So if for example Binance exchange errors out and this is true then a snapshot will be taken. Otherwise it won't.
   :param bool async_query: Boolean denoting whether this is an asynchronous query or not
   :param bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.
   :param bool save_data: Boolean denoting whether to force save data even if the balance save frequency has not lapsed (see `here <balance_save_frequency_>`_ ).


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "assets": {
                  "ETH": {
                      "amount": "1",
                      "percentage_of_net_value": "9.5%",
                      "usd_value": "180"
                   },
                   "BTC": {
                      "amount": "0.5",
                      "percentage_of_net_value": "90%",
                      "usd_value": "4000"
                   },
                   "EUR": {
                      "amount": "2",
                      "percentage_of_net_value": "0.5%",
                      "usd_value": "2.8"
                   }
               },
               "liabilities": {
                   "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                       "amount": "100",
                       "usd_value": "102.5",
                       "percentage_of_net_value": "1%"
                   }
               },
               "location": {
                   "banks": {
                       "percentage_of_net_value": "0.5%",
                       "usd_value": "2.8"
                   },
                   "binance": {
                       "percentage_of_net_value": "9.5%",
                       "usd_value": "180"
                   },
                   "blockchain": {
                       "percentage_of_net_value": "90%",
                       "usd_value": "4000"
                   }
               }

          },
          "message": ""
      }

   :resjson object result: The result object has two main subkeys. Assets and liabilities. Both assets and liabilities value is another object with the following keys. ``"amount"`` is the amount owned in total for that asset or owed in total as a liablity. ``"percentage_of_net_value"`` is the percentage the user's net worth that this asset or liability represents. And finally ``"usd_value"`` is the total $ value this asset/liability is worth as of this query. There is also a ``"location"`` key in the result. In there are the same results as the rest but divided by location as can be seen by the example response above.
   :statuscode 200: Balances successfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

Querying all supported assets
================================

.. http:post:: /api/(version)/assets/all

   Doing a POST on the all assets endpoint will return a list of all supported assets and their details.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/all HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
        "asset_type": "own chain",
        "limit": 15,
        "offset": 0
      }

   :reqjson int limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: This is the list of attributes of the asset by which to order the results. By default we sort using ``name``.
   :reqjson list[bool] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.
   :reqjson string name: The name of asset to be used to filter the result data. Optional.
   :reqjson string symbol: An asset symbol to be used to filter the result data. Optional.
   :reqjson string asset_type: The category of an asset to be used to filter the result data. Optional.
   :reqjson bool show_user_owned_assets_only: A flag to specify if only user owned assets should be returned. Defaults to ``"false"``. Optional.
   :reqjson string ignored_assets_handling: A flag to specify how to handle ignored assets. Possible values are `'none'`, `'exclude'` and `'show_only'`. You can write 'none' in order to not handle them in any special way (meaning to show them too). This is the default. You can write 'exclude' if you want to exlude them from the result. And you can write 'show_only' if you want to only see the ignored assets in the result.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [
              {
                  "identifier": "eip155:1/erc20:0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
                  "evm_address": "0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
                  "chain":"ethereum",
                  "token_kind":"erc20",
                  "decimals": 8,
                  "name": "0xBitcoin",
                  "started": 1517875200,
                  "symbol": "0xBTC",
                  "type": "ethereum token"
                  "cryptocompare":"0xbtc",
                  "coingecko":"0xbtc",
                  "protocol":"None"
              },
              {
                  "identifier": "DCR",
                  "name": "Decred",
                  "started": 1450137600,
                  "symbol": "DCR",
                  "type": "own chain"
              },
              {
                  "identifier": "eip155:1/erc20:0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38",
                  "evm_address": "0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38",
                  "chain":"ethereum",
                  "token_kind":"erc20",
                  "decimals": 18,
                  "name": "DigitalDevelopersFund",
                  "started": 1498504259,
                  "symbol": "DDF",
                  "type": "ethereum token"
                  "cryptocompare":"DDF",
                  "coingecko":"ddf",
                  "protocol":"None"
              },
              {
                  "identifier": "ETC",
                  "forked": "ETH",
                  "name": "Ethereum classic",
                  "started": 1469020840,
                  "symbol": "ETC",
                  "type": "own chain"
              },
              {
                  "identifier": "KRW",
                  "name": "Korean won",
                  "symbol": "KRW",
                  "type": "fiat"
              },
              {
                  "identifier": "eip155:1/erc20:0xD850942eF8811f2A866692A623011bDE52a462C1",
                  "evm_address": "0xD850942eF8811f2A866692A623011bDE52a462C1",
                  "chain":"ethereum",
                  "token_kind":"erc20",
                  "decimals": 18,
                  "name": "Vechain Token",
                  "started": 1503360000,
                  "swapped_for": "VET",
                  "symbol": "VEN",
                  "type": "ethereum token",
                  "coingecko": "vechain"
                  "cryptocompare":"VET",
                  "coingecko":"vet",
                  "protocol":"None"
              }
          ],
          "message": ""
      }

   :resjson list result: A list of assets that match the query with their respective asset details.
   :resjson string type: The type of asset. Valid values are ethereum token, own chain, omni token and more. For all valid values check `here <https://github.com/rotki/rotki/blob/8387c96eb77f9904b44a1ddd0eb2acbf3f8d03f6/rotkehlchen/assets/types.py#L10>`_.
   :resjson integer started: An optional unix timestamp denoting when we know the asset started to have a price.
   :resjson string name: The long name of the asset. Does not need to be the same as the unique identifier.
   :resjson string forked: An optional attribute representing another asset out of which this asset forked from. For example ``ETC`` would have ``ETH`` here.
   :resjson string swapped_for: An optional attribute representing another asset for which this asset was swapped for. For example ``VEN`` tokens were at some point swapped for ``VET`` tokens.
   :resjson string symbol: The symbol used for this asset. This is not guaranteed to be unique.
   :resjson string evm_address: If the type is ``evm_token`` then this will be the hexadecimal address of the token's contract.
   :resjson string chain: If the type is ``evm_token`` then this will be the chain in the form of string in which the token is.
   :resjson string token_kind:  If the type is ``evm_token`` then this will be the token type, for example ``erc20``.
   :resjson integer decimals: If the type is ``evm_token`` then this will be the number of decimals the token has.
   :resjson string cryptocompare: The cryptocompare identifier for the asset. can be missing if not known. If missing a query by symbol is attempted.
   :resjson string coingecko: The coingecko identifier for the asset. can be missing if not known.
   :resjson string protocol: An optional string for evm tokens denoting the protocol they belong to. For example uniswap, for uniswap LP tokens.
   :resjson object underlying_tokens: Optional. If the token is an LP token or a token set or something similar which represents a pool of multiple other tokens, then this is a list of the underlying token addresses and a percentage(value in the range of 0 to 100) that each token contributes to the pool.
   :resjson string notes: If the type is ``custom_asset`` this is a string field with notes added by the user.
   :resjson string custom_asset_type: If the type is ``custom_asset`` this field contains the custom type set by the user for the asset.
   :statuscode 200: Assets successfully queried.
   :statuscode 409: One or more of the requested identifiers don't exist in the database.
   :statuscode 500: Internal rotki error


Get asset identifiers mappings
================================

.. http:post:: /api/(version)/assets/mappings

   Doing a POST on the assets mappings endpoint with a list of of identifiers will return a mapping of those identifiers to their respective name and symbols.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/mappings HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
        "identifiers": [
            "eip155:1/erc20:0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
            "DCR",
            "eip155:1/erc20:0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38"
        ]
      }

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "eip155:1/erc20:0xB6eD7644C69416d67B522e20bC294A9a9B405B31": {
                  "name": "0xBitcoin",
                  "symbol": "0xBTC",
                  "is_custom_asset": false
              },
              "DCR": {
                  "name": "Decred",
                  "symbol": "DCR",
                  "is_custom_asset": false
              },
              "eip155:1/erc20:0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38": {
                  "name": "DigitalDevelopersFund",
                  "symbol": "DDF",
                  "evm_chain": "ethereum",
                  "is_custom_asset": false
              }
          },
          "message": ""
      }

   :resjson object result: A mapping of identifiers to their name, symbol & chain(if available).
   :resjson string name: Name of the asset.
   :resjson string symbol: Symbol of the asset.
   :resjson string evm_chain: This value might not be included in all the results. Full name of the EVM chain where the asset is located if the asset is an EVM token.
   :resjson string custom_asset_type: This value might not be included in all the results. It represents the custom asset type for a custom asset.
   :resjson bool is_custom_asset: A boolean to represent whether the asset is a custom asset or not.
   :statuscode 200: Assets successfully queried.
   :statuscode 400: One of the identifiers is not valid. Provided JSON is in some way malformed.
   :statuscode 500: Internal rotki error.

Search for assets
===================

.. http:post:: /api/(version)/assets/search

   Doing a POST on the assets search endpoint will return a list of objects containing an asset's name, symbol and identifier in ascending order of the assets' names by default.
   The result returned is based on the search keyword and column specified to search.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/search HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
        "value": "bitcoin",
        "search_column": "name",
        "limit": 50,
        "order_by_attributes": ["symbol"],
        "ascending": [false]
      }

   :reqjson int limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: This is the list of attributes of the asset by which to order the results. By default we sort using ``name``.
   :reqjson list[bool] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.
   :reqjson string value: A string to be used search the assets. Required.
   :reqjson string search_column: A column on the assets table to perform the search on. One of ``"name"`` or ``"symbol"``. Required.
   :reqjson bool return_exact_matches: A flag that specifies whether the result returned should match the search keyword. Defaults to ``"false"``.
   :reqjson string[optional] evm_chain: A string representing the name of a supported EVM chain used to filter the result. e.g "ethereum", "optimism", "binance", etc.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [
              {
                  "identifier": "eip155:1/erc20:0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
                  "name": "0xBitcoin",
                  "symbol": "0xBTC"
                  "chain": "ethereum",
                  "is_custom_asset": false
              },
              {
                  "identifier": "BTC",
                  "name": "bitcoin",
                  "symbol": "BTC",
                  "is_custom_asset": false
              }
          ],
          "message": ""
      }

   :resjson object result: A list of objects that contain the asset details which match the search keyword.
   :resjson string identifier: Identifier of the asset.
   :resjson string name: Name of the asset.
   :resjson string symbol: Symbol of the asset.
   :resjson string evm_chain: This value might not be included in all the results. Full name of the EVM chain where the asset is located if the asset is an EVM token.
   :resjson string custom_asset_type: This value might not be included in all the results. It represents the custom asset type for a custom asset.
   :resjson bool is_custom_asset: A boolean to represent whether the asset is a custom asset or not.
   :statuscode 200: Assets successfully queried.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 500: Internal rotki error.


Search for assets(Levenshtein)
===============================

.. http:post:: /api/(version)/assets/search/levenshtein

   Doing a POST on the assets search endpoint will return a list of objects containing an asset's name, symbol and identifier based on the search keyword provided. This approach using Levenshtein distance for the search functionality and returns them by the closest match first.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/search/levenshtein HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
        "value": "bitcoin",
        "limit": 50
      }

   :reqjson int limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: This is the list of attributes of the asset by which to order the results. By default we sort using ``name``.
   :reqjson list[bool] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.
   :reqjson string value: A string to be used to search the assets. Required.
   :reqjson string[optional] evm_chain: A string representing the name of a supported EVM chain used to filter the result. e.g "ethereum", "optimism", "binance", etc.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [
              {
                  "identifier": "eip155:1/erc20:0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
                  "name": "0xBitcoin",
                  "symbol": "0xBTC"
                  "evm_chain": "ethereum",
                  "is_custom_asset": false
              }
          ],
          "message": ""
      }

   :resjson object result: A list of objects that contain the asset details which match the search keyword ordered by distance to search keyword.
   :resjson string identifier: Identifier of the asset.
   :resjson string name: Name of the asset.
   :resjson string symbol: Symbol of the asset.
   :resjson string evm_chain: This value might not be included in all the results. Full name of the EVM chain where the asset is located if the asset is an EVM token.
   :resjson string custom_asset_type: This value might not be included in all the results. It represents the custom asset type for a custom asset.
   :resjson bool is_custom_asset: A boolean to represent whether the asset is a custom asset or not.
   :statuscode 200: Assets successfully queried.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 500: Internal rotki error.


Querying owned assets
======================

.. http:get:: /api/(version)/assets/

   Doing a GET on the assets endpoint will return a list of all assets ever owned.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/ HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["EUR", "USD", "ETH", "BTC"],
          "message": ""
      }


   :resjson list result: A list of asset symbols owned by the user
   :statuscode 200: Assets successfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error

Detecting owned tokens
======================

.. http:post:: /api/(version)/blockchains/(blockchain)/tokens/detect

   Doing POST on the detect tokens endpoint will detect tokens owned by the provided addresses on the specified blockchain. If no addresses provided, tokens for all user's addresses will be detected.

    .. note::
          This endpoint can also be queried asynchronously by using ``"async_query": true``

  **Example Request**:

  .. http:example:: curl wget httpie python-requests

    GET /api/1/blockchains/ETH/tokens/detect HTTP/1.1
    Host: localhost:5042

    {"addresses": ["0xC88eA7a5df3A7BA59C72393C5b2dc2CE260ff04D", "0xE07Af3FBEAf8584dc885f5bAA7c72419BDDf002D"]}


  :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
  :reqjson bool only_cache: Boolean denoting whether to use only cache or re-detect tokens.
  :reqjson list addresses: A list of addresses to detect tokens for.


  **Example Response**:

  .. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "result": {
            "0x31F05553be0EBBf7774241603Cc7b28771F989B3": {
                "tokens": [
                    "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F", "eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
                ],
                "last_update_timestamp": 1658764910,
            },
        },
        "message": ""
    }


  :resjson object result: a dictionary containing mappings of an account to owned tokens and last tokens update timestamp. Tokens and last_update_timestamp can be None (if no info about account's tokens yet).
  :statuscode 200: Tokens successfully detected.
  :statuscode 400: Provided JSON is in some way malformed
  :statuscode 409: No user is currently logged in.
  :statuscode 500: Internal rotki error

Getting custom EVM tokens
==================================

.. http:get:: /api/(version)/assets/ethereum

   Doing a GET on the ethereum assets endpoint will return a list of all custom EVM tokens. You can also optionally specify an ethereum address to get its token details. If you query by address only a single object is returned. If you query without, a list of objects.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/ethereum HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"address": "0x1169C72f36A843cD3a3713a76019FAB9503B2807", "chain": "ethereum"}

   :reqjson string address: An optional address to query for ethereum token info. If given only token info of this address are returned. As an object. **not a list**. If not given, a list of all known tokens is returned.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "identifier": "eip155:1/erc20:0x1169C72f36A843cD3a3713a76019FAB9503B2807",
              "address": "0x1169C72f36A843cD3a3713a76019FAB9503B2807",
              "chain":"ethereum",
              "token_kind":"erc20",
              "decimals": 18,
              "name": "foo",
              "symbol": "FTK",
              "started": 1614636432,
              "swapped_for": "SCT",
              "coingecko": "foo-coin",
              "cryptocompare": "FOO",
              "protocol": "uniswap",
              "underlying_tokens": [
                  {"address": "0x4a363BDcF9C139c0B77d929C8c8c5f971a38490c", "chain":"ethereum", "token_kind":"erc20", "weight": "15.45"},
                  {"address": "0xf627B24754583896AbB6376b1e231A3B26d86c99", "chain":"ethereum", "token_kind":"erc20", "weight": "35.65"},
                  {"address": "0x2B18982803EF09529406e738f344A0c1A54fA1EB", "chain":"ethereum", "token_kind":"erc20", "weight": "39"}
              ]
          },
          "message": ""
      }

   .. _custom_ethereum_token:

   :resjson list result: A list of ethereum tokens
   :resjsonarr string identifier: The rotki identifier of the token. This is only returned from the GET endpoint and not input from the add/edit one.
   :resjsonarr string address: The address of the token. This is a required field.
   :resjsonarr string chain: The chain where the token is deployed. This is a required field.
   :resjsonarr string token_kind: The kind of the token. This is a required field.
   :resjsonarr integer decimals: Ethereum token decimals. Can be missing if not known.
   :resjsonarr string name: Asset name. Can be missing if not known.
   :resjsonarr string symbol: Asset symbol. Can be missing if not known.
   :resjsonarr integer started: The timestamp of the token deployment. Can be missing if not known.
   :resjsonarr string swapped_for: If this token was swapped for another one then here we would have the identifier of that other token. If not this is null.
   :resjsonarr string coingecko: The coingecko identifier for the asset. can be missing if not known.
   :resjsonarr string cryptocompare: The cryptocompare identifier for the asset. can be missing if not known.
   :resjsonarr string protocol: A name for the protocol the token belongs to. For example uniswap for all uniswap LP tokens. Can be missing if not known or there is no protocol the token belongs to.
   :resjsonarr list underlying_tokens: Optional. If the token is an LP token or a token set or something similar which represents a pool of multiple other tokens, then this is a list of the underlying token addresses, chain, token kind and a percentage that each token contributes to the pool.
   :statuscode 200: Assets successfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 404: Queried by address and no token was found.
   :statuscode 500: Internal rotki error

Adding custom ethereum tokens
==================================

.. http:put:: /api/(version)/assets/ethereum

   Doing a PUT on the ethereum assets endpoint will allow you to add a new ethereum token in the global rotki DB. Returns the asset identifier of the new custom token. For ethereum ones it's ``eip155:1/erc20:0xADDRESS``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/ethereum HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"token": {
          "address": "0x1169C72f36A843cD3a3713a76019FAB9503B2807",
          "chain":"ethereum",
          "token_kind":"erc20",
          "decimals": 18,
          "name": "foo",
          "symbol": "FTK",
          "started": 1614636432,
          "swapped_for": "SCT",
          "coingecko": "foo-coin",
          "cryptocompare": "FOO",
          "protocol": "uniswap",
          "underlying_tokens": [
              {"address": "0x4a363BDcF9C139c0B77d929C8c8c5f971a38490c", "token_kind":"erc20", "weight": "15.45"},
              {"address": "0xf627B24754583896AbB6376b1e231A3B26d86c99", "token_kind":"erc20", "weight": "35.65"},
              {"address": "0x2B18982803EF09529406e738f344A0c1A54fA1EB", "token_kind":"erc20", "weight": "39"}
         ]
       }}

   :reqjson object token: A token to add. For details on the possible fields see `here <custom_ethereum_token_>`_.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"identifier": "eip155:1/erc20:0x1169C72f36A843cD3a3713a76019FAB9503B2807"},
          "message": ""
      }


   :resjson string identifier: The identifier of the newly added token.
   :statuscode 200: Asset successfully added.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Some conflict at addition. For example token address is already in the DB.
   :statuscode 500: Internal rotki error

Editing custom ethereum tokens
==================================

.. http:patch:: /api/(version)/assets/ethereum

   Doing a PATCH on the ethereum assets endpoint will allow you to edit an existing ethereum token in the global rotki DB. Returns the asset identifier of the edited token for success.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/assets/ethereum HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "token": {
              "address": "0x1169C72f36A843cD3a3713a76019FAB9503B2807",
              "decimals": 5,
              "name": "foo",
              "symbol": "FTK",
              "started": 1614636432,
              "swapped_for": "SCP",
              "coingecko": "foo-coin",
              "cryptocompare": "FOO",
              "protocol": "aave"
         }
      }

   :reqjson object token: Token to edit. Token is edited by address. The old token is completely replaced by all new entries passed by this endpoint. For details on the possible fields see `here <custom_ethereum_token_>`_.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"identifier": "eip155:1/erc20:0x1169C72f36A843cD3a3713a76019FAB9503B2807"},
          "message": ""
      }


   :resjson string identifier: The identifier of the edited token.
   :statuscode 200: Asset successfully edited.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Some conflict at editing. For example token address does not exist in the DB.
   :statuscode 500: Internal rotki error

Deleting custom ethereum tokens
==================================

.. http:delete:: /api/(version)/assets/ethereum

   Doing a DELETE on the ethereum assets endpoint will allow you to delete an existing ethereum token from the global rotki DB by address.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/ethereum HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"address": "0x1169C72f36A843cD3a3713a76019FAB9503B2807"}

   :reqjson string address: Address of the token to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"identifier": "GNO"},
          "message": ""
      }


   :resjson string identifier: The rotki identifier of the token that was deleted.
   :statuscode 200: Asset successfully deleted.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Some conflict at deleting. For example token address does not exist in the DB.
   :statuscode 500: Internal rotki error


Get asset types
=================

.. http:get:: /api/(version)/assets/types

   Doing a GET on the assets types endpoint will return a list of all valid asset type

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/types HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["fiat", "own chain", "ethereum token", "omni token", "neo token", "counterparty token", "bitshares token", "ardor token", "nxt token", "ubiq token", "nubits token", "burst token", "waves token", "qtum token", "stellar token", "tron token", "ontology token", "vechain token", "binance token", "eos token", "fusion token", "luniverse token", "other"],
          "message": ""
      }


   :resjson list result: A list of all the valid asset type values to input when adding a new asset
   :statuscode 200: Asset types successfully queries
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 500: Internal rotki error

Adding custom asset
======================

.. http:put:: /api/(version)/assets/all

   Doing a PUT on the all assets endpoint will allow you to add a new asset in the global rotki DB. Returns the identifier of the newly added asset.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/all HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "name": "foo",
          "symbol": "FOO",
          "started": 1614636432,
          "forked": "SCT",
          "swapped_for": "SCK",
          "coingecko": "foo-coin",
          "cryptocompare": "FOO"
       }

   .. _custom_asset:

   :reqjson string name: The name of the asset. Required.
   :reqjson string symbol: The symol of the asset. Required.
   :reqjson integer started: The time the asset started existing. Optional
   :reqjson string forked: The identifier of an asset from which this asset got forked. For example ETC would have ETH as forked. Optional.
   :reqjson string swapped_for: The identifier of an asset for which this asset got swapped for. For example GNT got swapped for GLM. Optional.
   :resjsonarr string coingecko: The coingecko identifier for the asset. can be missing if not known.
   :resjsonarr string cryptocompare: The cryptocompare identifier for the asset. can be missing if not known.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"identifier": "4979582b-ee8c-4d45-b461-15c4220de666"},
          "message": ""
      }


   :resjson string identifier: The identifier of the newly added token.
   :statuscode 200: Asset successfully added.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Some conflict at addition. For example an asset with the same type, name and symbol already exists.
   :statuscode 500: Internal rotki error

Editing custom assets
======================

.. http:patch:: /api/(version)/assets/all

   Doing a PATCH on the custom assets endpoint will allow you to edit an existing asset in the global rotki DB.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/ethereum HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "identifier": "4979582b-ee8c-4d45-b461-15c4220de666",
          "name": "foo",
          "symbol": "FOO",
          "started": 1614636432,
          "forked": "SCT",
          "swapped_for": "SCK",
          "coingecko": "foo-coin",
          "cryptocompare": "FOO"
      }

   :reqjson object asset: Asset to edit. For details on the possible fields see `here <custom_asset_>`_. The only extra field has to be the identifier of the asset to edit.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }


   :statuscode 200: Asset successfully edited.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Some conflict at editing. For example identifier does not exist in the DB.
   :statuscode 500: Internal rotki error

Deleting custom assets
========================

.. http:delete:: /api/(version)/assets/all

   Doing a DELETE on the custom assets endpoint will allow you to delete an existing asset from the global rotki DB.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/all HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"identifier": "4979582b-ee8c-4d45-b461-15c4220de666"}

   :reqjson string identifier: Address of the asset to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }


   :statuscode 200: Asset successfully deleted.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Some conflict at deleting. For example identifier does not exist in the DB. Or deleting the asset would break a constraint since it's used by other assets.
   :statuscode 500: Internal rotki error


Checking for pending asset updates
=====================================

.. http:get:: /api/(version)/assets/updates

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on this endpoint will prompt a query on the remote github server and return how many updates (if any) exists for the local asset database.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/updates HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": true}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "local": 1,
              "remote": 4,
              "new_changes": 121
          "message": ""
      }

   :resjson int local: The version of the local assets database
   :resjson int remote: The latest assets update version on the remote
   :resjson int new_changes: The number of changes (additions, edits and deletions) that would be applied to reach the remote version.
   :statuscode 200: Pending asset updates information is successfully queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 500: Internal rotki error
   :statuscode 502: Error while trying to reach the remote for asset updates.

Performing an asset update
=====================================

.. http:post:: /api/(version)/assets/updates

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``


   Doing a POST on this endpoint will attempt an update of the assets database.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/updates HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "async_query": true,
          "up_to_version": 5,
          "conflicts": {
              "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015": "local",
              "eip155:1/erc20:0xD178b20c6007572bD1FD01D205cC20D32B4A6015": "remote",
              "Fas-23-da20": "local"
          }
      }

   :reqjson bool async_query: Optional. If given and true then the query becomes an asynchronous query.
   :reqjson int up_to_version: Optional. If given then the asset updates up to and including this version will be pulled and applied
   :reqjson object conflicts: Optional. Should only be given if at the previous run there were conflicts returned. This is a mapping of asset identifiers to either ``"local"`` or ``"remote"`` specifying which of the two to keep in a conflict.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": [{
            "identifier":  "assetid1",
            "local": {
                "coingecko": "2give",
                "name": "2GIVE",
                "started": 1460937600,
                "symbol": "2GIVE",
                "type": "own chain"
            },
            "remote": {
                "coingecko": "TWOgive",
                "name": "TWOGIVE",
                "started": 1460937600,
                "symbol": "2GIVEORNOTTOGIVE",
                "type": "own chain"
           }}, {
           "identifier": "asset_id2",
           "local": {
                   "coingecko": "aave",
                   "ethereum_address": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
                   "ethereum_token_decimals": 18,
                   "name": "Aave Token",
                   "started": 1600970788,
                   "symbol": "AAVE",
                   "type": "ethereum token"
           },
           "remote": {
                   "coingecko": "aaveNGORZ",
                   "ethereum_address": "0x1Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
                   "ethereum_token_decimals": 15,
                   "name": "Aave Token FOR REALZ",
                   "started": 1600970789,
                   "symbol": "AAVE_YO!",
                   "type": "binance token"
           }
        }],
        "message": ""
      }

   :resjson object result: Either ``true`` if all went fine or a a list of conflicts, containing the identifier of the asset in question and the local and remote versions.
   :statuscode 200: Update was successfully applied (if any).
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Conflicts were found during update. The conflicts should also be returned. No user is currently logged in.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error while trying to reach the remote for asset updates.

Reset state of assets
=====================

.. http:delete:: /api/(version)/assets/updates

   Doing a DELETE on this endpoint will attempt to reset the state of the assets in the globaldb. Can be called in two modes, ``soft`` where the API will try to reset the state of packaged assets without modifying assets added by the user and ``hard`` mode where the assets added by the user will be deleted and the database will get the information from the packaged globaldb.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/updates HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "ignore_warnings": true,
          "reset": "hard"
      }

   :reqjson bool ignore_warnings: Optional. Defaults to ``false``. If set to true the database will be reset even if there are events that depend on assets that will be deleted.
   :reqjson str reset: The mode selected to perform the reset. Can be either ``soft`` or ``hard``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson object result: ``true`` if the reset was completed successfully
   :statuscode 200: Reset of the globaldb performed.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Conflicts were found during the reset.


Replacing an asset
========================

.. http:put:: /api/(version)/assets/replace

   It's possible to replace an asset with another asset in both the global and the user DB. If the source asset identifier exists in the global DB it's removed in favor of the target asset. If not, the global DB is not touched. In both cases the user DB is touched and all appearances of the source asset identifier are replaced with target asset.
   If the asset you are replacing is used as swapped_for, forked_for or underlying asset by another asset you will first have to manually delete it from there.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/replace HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"source_identifier": "4979582b-ee8c-4d45-b461-15c4220de666", "target_asset": "BTC"}

   :reqjson string source_identifier: The identifier of the asset that will get replaced/removed. This asset does not need to exist in the global DB. If it does it will be removed.
   :reqjson string target_asset: The identifier of the asset that will replace the source asset. This must be an existing asset.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :statuscode 200: Asset successfully replaced.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Some conflict at replacing or user is not logged in.
   :statuscode 500: Internal rotki error

Querying asset icons
======================

.. http:post:: /api/(version)/assets/icon

   Doing a GET on the asset icon endpoint will return the icon of the given asset. If we have no icon for an asset a 404 is returned


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/icon?asset=eip155:1/erc20:3A0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e HTTP/1.1
      Host: localhost:5042

   :reqquery string asset: Identifier of the asset to be queried.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: image/png

   :result: The data of the image
   :statuscode 200: Icon successfully queried
   :statuscode 304: Icon data has not changed. Should be cached on the client. This is returned if the given If-Match or If-None-Match header match the etag of the previous response.
   :statuscode 400: Provided JSON is in some way malformed. Either unknown asset or invalid size.
   :statuscode 404: We have no icon for that asset
   :statuscode 500: Internal rotki error


Uploading custom asset icons
===============================

.. http:put:: /api/(version)/assets/icon/modify
.. http:post:: /api/(version)/assets/icon/modify

   Doing either a PUT or a POST on the asset icon endpoint with appropriate arguments will upload a custom icon for an asset. That icon will take precedence over what rotki already knows for the asset if anything.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/icon/modify HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"file": "/path/to/file", "asset": "eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96"}

   :reqjson string file: The path to the image file to upload for PUT. The file itself for POST.
   :reqjson string asset: Identifier of the asset to be updated.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {"result": {"identifier": "eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96"}, "message": ""}

   :resjson strin identifier: The identifier of the asset for which the icon was uploaded.
   :statuscode 200: Icon successfully uploaded
   :statuscode 500: Internal rotki error


Refreshing asset icons
===============================

.. http:patch:: /api/(version)/assets/icon/modify

   Doing a PATCH on the asset icon endpoint will refresh the icon of the given asset.
   First, the cache of the icon of the given asset is deleted and then requeried from CoinGecko and saved to the filesystem.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/assets/icon/modify HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"asset": "eip155:1/erc20:0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e"}

   :reqjson string asset: Identifier of the asset to be refreshed.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {"result": true, "message": ""}

   :statuscode 200: Icon successfully deleted and requeried.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 404: Unable to refresh icon at the moment.
   :statuscode 500: Internal rotki error


Statistics for netvalue over time
====================================

.. http:get:: /api/(version)/statistics/netvalue/

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the statistics netvalue over time endpoint will return all the saved historical data points with user's history


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/netvalue/ HTTP/1.1
      Host: localhost:5042

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

   :resjson list[integer] times: A list of timestamps for the returned data points
   :resjson list[string] data: A list of net usd value for the corresponding timestamps. They are matched by list index.
   :statuscode 200: Netvalue statistics successfully queried.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error.

Statistics for asset balance over time
======================================

.. http:post:: /api/(version)/statistics/balance

   .. note::
      This endpoint is only available for premium users


   Doing a POST on the statistics asset balance over time endpoint will return all saved balance entries for an asset. Optionally you can filter for a specific time range by providing appropriate arguments.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/statistics/balance HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1514764800, "to_timestamp": 1572080165, "asset": "BTC"}

   :reqjson int from_timestamp: The timestamp after which to return saved balances for the asset. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return saved balances for the asset. If not given all balances until now are returned.
   :reqjson string asset: Identifier of the asset.
   :param int from_timestamp: The timestamp after which to return saved balances for the asset. If not given zero is considered as the start.
   :param int to_timestamp: The timestamp until which to return saved balances for the asset. If not given all balances until now are returned.
   :param string asset: Identifier of the asset.

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

   :resjson list(object) result: A list of asset balance entries.
   :resjsonarr integer time: The timestamp of the balance entry.
   :resjsonarr number amount: The amount of the balance entry.
   :resjsonarr number usd_value: The usd_value of the balance entry at the given timestamp.

   :statuscode 200: Single asset balance statistics successfully queried
   :statuscode 400: Provided JSON is in some way malformed or data is invalid.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error

Statistics for value distribution
==================================

.. http:get:: /api/(version)/statistics/value_distribution/

   Doing a GET on the statistics value distribution endpoint with the ``"distribution_by": "location"`` argument will return the distribution of netvalue across all locations.

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint also accepts parameters as query arguments.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/value_distribution/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"distribution_by": "location"}

   :reqjson str distribution_by: The type of distribution to return. It can only be ``"location"`` or ``"asset"``.
   :param str distribution_by: The type of distribution to return. It can only be ``"location"`` or ``"asset"``.

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

   :resjson list(object) result: A list of location data entries.
   :resjsonarr integer time: The timestamp of the entry
   :resjsonarr string location: The location of the entry.
   :resjsonarr string usd_value: The value of the entry in $.

   :statuscode 200: Value distribution successfully queried.
   :statuscode 400: Provided JSON is in some way malformed or data is invalid.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error.

.. http:get:: /api/(version)/statistics/value_distribution/

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the statistics value distribution endpoint with the ``"distribution_by": "asset"`` argument will return the distribution of netvalue across all assets.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/value_distribution/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"distribution_by": "asset"}

   :reqjson str distribution_by: The type of distribution to return. It can only be ``"location"`` or ``"asset"``.
   :param str distribution_by: The type of distribution to return. It can only be ``"location"`` or ``"asset"``.

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

   :resjson list(object) result: A list of asset balance data entries. Each entry contains the timestamp of the entry, the assets, the amount in asset and the equivalent usd value at the time.
   :resjsonarr integer time: The timestamp of the balance entry.
   :resjsonarr string asset: The name of the asset for the balance entry.
   :resjsonarr string amount: The amount in asset for the balance entry.
   :resjsonarr string usd_value: The amount in $ for the balance entry at the time of query.

   :statuscode 200: Value distribution successfully queried.
   :statuscode 400: Provided JSON is in some way malformed or data is invalid.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error.

Statistics rendering code
================================

.. http:get:: /api/(version)/statistics/renderer/

   Doing a GET on the statistics renderer will return the code to render the statistics if the currently logged in user is a premium user.

   .. note::
      This endpoint is only available for premium users


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/renderer/ HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": "code goes here"
          "message": ""
      }


   :resjson string result: The source code of the renderer.
   :statuscode 200: Rendering code successfully returned.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. There is a problem reaching the rotki server.
   :statuscode 500: Internal rotki error.

Dealing with trades
===================

.. http:get:: /api/(version)/trades

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on this endpoint will return all trades of the current user. They can be further filtered by time range and/or location. If the user is not premium and has more than 250 trades then the returned trades will be limited to that number. Any filtering will also be limited to those first 250 trades. Trades are returned most recent first.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/trades HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "location": "external", "only_cache": false}

   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: Optional. This is the list of attributes of the trade table by which to order the results. If none is given 'time' is assumed. Valid values are: ['time', 'location', 'type', 'amount', 'rate', 'fee'].
   :reqjson list[bool] ascending: Optional. False by default. Defines the order by which results are returned depending on the chosen order by attribute.
   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string location: Optionally filter trades by location. A valid location name has to be provided. If missing location filtering does not happen.
   :reqjson string base_asset: Optionally filter trades by base_asset. A valid asset identifier has to be provided. If missing trades are not filtered by base asset.
   :reqjson string quote_asset: Optionally filter trades by quote_asset. A valid asset identifier has to be provided. If missing trades are not filtered by quote asset.
   :reqjson string trade_type: Optionally filter trades by type. A valid trade type (buy, sell) has to be provided. If missing trades are not filtered by type.
   :reqjson bool only_cache: Optional.If this is true then the equivalent exchange/location is not queried, but only what is already in the DB is returned.

   .. _trades_schema_section:

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "entries": [{
                  "entry": {
                      "trade_id": "dsadfasdsad",
                      "timestamp": 1491606401,
                      "location": "external",
                      "base_asset": "BTC",
                      "quote_asset": "EUR",
                      "trade_type": "buy",
                      "amount": "0.5541",
                      "rate": "8422.1",
                      "fee": "0.55",
                      "fee_currency": "USD",
                      "link": "Optional unique trade identifier",
                      "notes": "Optional notes"
                  },
                  "ignored_in_accounting": false
              }],
              "entries_found": 95,
              "entries_total": 155,
              "entries_limit": 250,
          "message": ""
      }

   :resjson object entries: An array of trade objects and their metadata. Each entry is composed of the main trade entry under the ``"entry"`` key and other metadata like ``"ignored_in_accounting"`` for each trade.
   :resjsonarr string trade_id: The uniquely identifying identifier for this trade. The trade id depends on the data of the trade. If the trade is edited so will the trade id.
   :resjsonarr int timestamp: The timestamp at which the trade occurred
   :resjsonarr string location: A valid location at which the trade happened
   :resjsonarr string base_asset: The base_asset of the trade.
   :resjsonarr string quote_asset: The quote_asset of the trade.
   :resjsonarr string trade_type: The type of the trade. e.g. ``"buy"`` or ``"sell"``
   :resjsonarr string amount: The amount that was bought or sold
   :resjsonarr string rate: The rate at which 1 unit of ``base_asset`` was exchanges for 1 unit of ``quote_asset``
   :resjsonarr string fee: Optional. The fee that was paid, if anything, for this trade
   :resjsonarr string fee_currency: Optional. The currency in which ``fee`` is denominated in.
   :resjsonarr string link: Optional unique trade identifier or link to the trade.
   :resjsonarr string notes: Optional notes about the trade.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_limit: The limit of entries if free version. -1 for premium.
   :resjson int entries_total: The number of total entries ignoring all filters.
   :statuscode 200: Trades are successfully returned
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error reaching the remote from which the trades got requested

.. http:put:: /api/(version)/trades

   Doing a PUT on this endpoint adds a new trade to rotki's currently logged in user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/trades HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "timestamp": 1491606401,
          "location": "external",
          "base_asset": "BTC",
          "quote_asset": "EUR",
          "trade_type": "buy",
          "amount": "0.5541",
          "rate": "8422.1",
          "fee": "0.55",
          "fee_currency": "USD",
          "link": "Optional unique trade identifier",
          "notes": "Optional notes"
      }

   :reqjson int timestamp: The timestamp at which the trade occurred
   :reqjson string location: A valid location at which the trade happened
   :resjsonarr string base_asset: The base_asset of the trade.
   :resjsonarr string quote_asset: The quote_asset of the trade.
   :reqjson string trade_type: The type of the trade. e.g. ``"buy"`` or ``"sell"``
   :reqjson string amount: The amount that was bought or sold
   :reqjson string rate: The rate at which 1 unit of ``base_asset`` was exchanges for 1 unit of ``quote_asset``
   :reqjson string fee: Optional. The fee that was paid, if anything, for this trade
   :reqjson string fee_currency: Optional. The currency in which ``fee`` is denominated in
   :reqjson string link: Optional unique trade identifier or link to the trade.
   :reqjson string notes: Optional notes about the trade.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
                  "trade_id": "dsadfasdsad",
                  "timestamp": 1491606401,
                  "location": "external",
                  "base_asset": "BTC",
                  "quote_asset": "EUR",
                  "trade_type": "buy",
                  "amount": "0.5541",
                  "rate": "8422.1",
                  "fee": "0.55",
                  "fee_currency": "USD",
                  "link": "Optional unique trade identifier",
                  "notes": "Optional notes"
          }],
          "message": ""
      }

   :resjson object result: Array of trade entries with the same schema as seen in `this <trades_schema_section_>`_ section.
   :statuscode 200: Trades was successfully added.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error

.. http:patch:: /api/(version)/trades

   Doing a PATCH on this endpoint edits an existing trade in rotki's currently logged in user using the ``trade_id``.
   The edited trade's trade id is returned and will be different.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/trades HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "trade_id" : "dsadfasdsad",
          "timestamp": 1491606401,
          "location": "external",
          "base_asset": "BTC",
          "quote_asset": "EUR",
          "trade_type": "buy",
          "amount": "1.5541",
          "rate": "8422.1",
          "fee": "0.55",
          "fee_currency": "USD",
          "link": "Optional unique trade identifier",
          "notes": "Optional notes"
      }

   :reqjson string trade_id: The ``trade_id`` of the trade to edit. Note: the returned trade id will be different.
   :reqjson int timestamp: The new timestamp
   :reqjson string location: The new location
   :reqjson string base_asset: The new base_asset
   :reqjson string quote_asset: The new quote_asset
   :reqjson string trade_type: The new trade type
   :reqjson string rate: The new trade rate
   :reqjson string fee: The new fee. Can be set to null.
   :reqjson string fee_currency: The new fee currency. Can be set to null.
   :reqjson string link: The new link attribute. Can be set to null.
   :reqjson string notes: The new notes attribute. Can be set to null.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "trade_id": "sdfhdjskfha",
              "timestamp": 1491606401,
              "location": "external",
              "base_asset": "BTC",
              "quote_asset": "EUR",
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

   :resjson object result: A trade with the same schema as seen in `this <trades_schema_section_>`_ section. The trade id will be different if the trade was successfully edited.
   :statuscode 200: Trades was successfully edited.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The given trade identifier to edit does not exist.
   :statuscode 500: Internal rotki error.

.. http:delete:: /api/(version)/trades

   Doing a DELETE on this endpoint deletes an existing trade in rotki's currently logged in user using the ``trade_id``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/trades HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      { "trades_ids" : ["dsadfasdsad"]}

   :reqjson string trades_ids: The list of identifiers for trades to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: Returns ``true`` if all identifiers were found and deleted, otherwise returns ``false``.
   :resjson string message: Returns ``""`` if ``result`` is ``True`` else returns the error message.
   :statuscode 200: Trades was successfully deleted.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The given trade identifier to delete does not exist.
   :statuscode 500: Internal rotki error.

Querying asset movements
===========================

.. http:get:: /api/(version)/asset_movements

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on this endpoint will return all asset movements (deposits/withdrawals) from all possible exchanges for the current user. It can be further filtered by a time range of a location. For non premium users there is a limit on the amount of movements returned.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/asset_movements HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "location": "kraken", "only_cache": false}

   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: Optional. This is the list of attributes of the asset movements table by which to order the results. If none is given 'time' is assumed. Valid values are: ['time', 'location', 'category', 'amount', 'fee'].
   :reqjson list[bool] ascending: Optional. False by default. Defines the order by which results are returned depending on the chosen order by attribute.
   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string location: Optionally filter asset movements by location. A valid location name has to be provided. Valid locations are for now only exchanges for deposits/withdrawals.
   :reqjson string asset: Optionally filter asset movements by asset. A valid asset identifier has to be provided. If missing, movements are not filtered by asset.
   :reqjson string action: Optionally filter asset movements by action type. A valid action type (deposit, withdrawals) has to be provided. If missing movements are not filtered by type.
   :reqjson bool only_cache: Optional. If this is true then the equivalent exchange/location is not queried, but only what is already in the DB is returned.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "entries": [{
                  "entry": {
                      "identifier": "foo"
                      "location": "kraken",
                      "category": "deposit",
                      "address": "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B",
                      "transaction_id": "3a4b9b2404f6e6fb556c3e1d46a9752f5e70a93ac1718605c992b80aacd8bd1d",
                      "timestamp": 1451706400
                      "asset": "ETH",
                      "amount": "500.55",
                      "fee_asset": "ETH",
                      "fee": "0.1",
                      "link": "optional exchange unique id"
                  },
                  "ignored_in_accounting": false
              }],
              "entries_found": 80,
              "entries_total": 120,
              "entries_limit": 100,
          "message": ""
      }

   :resjson object entries: An array of deposit/withdrawal objects and their metadata. Each entry is composed of the main movement entry under the ``"entry"`` key and other metadata like ``"ignored_in_accounting"`` for each asset movement.
   :resjsonarr string identifier: The uniquely identifying identifier for this asset movement
   :resjsonarr string location: A valid location at which the deposit/withdrawal occurred
   :resjsonarr string category: Either ``"deposit"`` or ``"withdrawal"``
   :resjsonarr string address: The source address if this is a deposit or the destination address if this is a withdrawal.
   :resjsonarr string transaction_id: The transaction id
   :resjsonarr integer timestamp: The timestamp at which the deposit/withdrawal occurred
   :resjsonarr string asset: The asset deposited or withdrawn
   :resjsonarr string amount: The amount of asset deposited or withdrawn
   :resjsonarr string fee_asset: The asset in which ``fee`` is denominated in
   :resjsonarr string fee: The fee that was paid, if anything, for this deposit/withdrawal
   :resjsonarr string link: Optional unique exchange identifier for the deposit/withdrawal
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_limit: The limit of entries if free version. -1 for premium.
   :resjson int entries_total: The number of total entries ignoring all filters.
   :statuscode 200: Deposits/withdrawals are successfully returned
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error querying the remote for the asset movements


Dealing with ledger actions
=============================

.. http:get:: /api/(version)/ledgeractions

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on this endpoint will return all ledger actions of the current user. That means income, loss, expense and other actions. They can be further filtered by time range and/or location. If the user is not premium and has more than 50 actions then the returned results will be limited to that number. Any filtering will also be limited to those first 50 actions. Actions are returned most recent first.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/ledgeractions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "location": "blockchain"}

   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: Optional. This is the list of attributes of the ledger actions table by which to order the results. If none is given 'timestamp' is assumed. Valid values are: ['timestamp', 'location', 'type', 'amount', 'rate'].
   :reqjson list[bool] ascending: Optional. False by default. Defines the order by which results are returned depending on the chosen order by attribute.
   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string asset: Optionally filter by action asset. A valid asset has to be provided. If missing asset filtering does not happen.
   :reqjson string location: Optionally filter actions by location. A valid location name has to be provided. If missing location filtering does not happen.
   :reqjson string type: Optionally filter by ledger action type. A valid action type to be provided. If missing action type filtering does not happen.
   :reqjson bool only_cache: Optional. If this is true then the equivalent exchange/location is not queried, but only what is already in the DB is returned.

   .. _ledger_actions_schema_section:

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "entries": [{
                  "entry": {
                      "identifier": 344,
                      "timestamp": 1491606401,
                      "action_type": "loss",
                      "location": "blockchain",
                      "amount": "1550",
                      "asset": "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F",
                      "rate": "0.85",
                      "rate_asset": "EUR",
                      "link": "https://etherscan.io/tx/0xea5594ad7a1e552f64e427b501676cbba66fd91bac372481ff6c6f1162b8a109"
                      "notes": "The DAI I lost in the pickle finance hack"
                  },
                  "ignored_in_accounting": false
              }],
              "entries_found": 1,
              "entries_total": 1,
              "entries_limit": 50,
          "message": ""
      }

   :resjson object entries: An array of action objects and their metadata. Each entry is composed of the ledger action entry under the ``"entry"`` key and other metadata like ``"ignored_in_accounting"`` for each action.
   :resjsonarr int identifier: The uniquely identifying identifier for this action.
   :resjsonarr int timestamp: The timestamp at which the action occurred
   :resjsonarr string action_type: The type of action. Valid types are: ``income``, ``loss``, ``donation received``, ``expense`` and ``dividends income``.
   :resjsonarr string location: A valid location at which the action happened.
   :resjsonarr string amount: The amount of asset for the action
   :resjsonarr string asset: The asset for the action
   :resjsonarr string rate: Optional. If given then this is the rate in ``rate_asset`` for the ``asset`` of the action.
   :resjsonarr string rate_asset: Optional. If given then this is the asset for which ``rate`` is given.
   :resjsonarr string link: Optional unique identifier or link to the action. Can be an empty string
   :resjsonarr string notes: Optional notes about the action. Can be an empty string
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_limit: The limit of entries if free version. -1 for premium.
   :resjson int entries_total: The number of total entries ignoring all filters.
   :statuscode 200: Actions are successfully returned
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/ledgeractions

   Doing a PUT on this endpoint adds a new ledgeraction to rotki's currently logged in user. The identifier of the new created action is returned.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/ledgeraction HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "action": {
              "timestamp": 1491606401,
              "action_type": "income",
              "location": "external",
              "amount": "1",
              "asset": "ETH",
              "rate": "650",
              "rate_asset": "EUR",
              "link": "Optional unique identifier",
              "notes": "Eth I received for being pretty"
      }}

   The request object is the same as above, a LedgerAction entry.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"identifier": 1},
          "message": ""
      }

   :resjson object result: The identifier of the newly created ledger action
   :statuscode 200: Ledger action was successfully added.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error

.. http:patch:: /api/(version)/ledgeractions

   Doing a PATCH on this endpoint edits an existing ledger action in rotki's currently logged in user using the given ``identifier``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/ledgeractions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "identifier": 55,
          "timestamp": 1491606401,
          "action_type": "income",
          "location": "external",
          "amount": "2",
          "asset": "ETH",
          "rate": "650",
          "rate_asset": "EUR",
          "link": "Optional unique identifier",
          "notes": "Eth I received for being pretty"
      }

   The request object is the same as above, a LedgerAction entry, with the addition of the identifier which signifies which ledger action entry will be edited.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "entries": [{
                  "entry": {
                      "identifier": 55,
                      "timestamp": 1491606401,
                      "action_type": "income"
                      "location": "external",
                      "amount": "2",
                      "asset": "ETH",
                      "rate": "650",
                      "rate_asset": "EUR",
                      "link": "Optional unique identifier",
                      "notes": "Eth I received for being pretty"
                  },
                  "ignored_in_accounting": false
              }],
              "entries_found": 1,
              "entries_limit": 50,
          "message": ""
      }

   :resjson object entries: An array of action objects after editing. Same schema as the get method.
   :resjson int entries_found: The amount of actions found for the user. That disregards the filter and shows all actions found.
   :resjson int entries_limit: The actions limit for the account tier of the user. If unlimited then -1 is returned.
   :statuscode 200: Actions was successfully edited.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/ledgeractions

   Doing a DELETE on this endpoint deletes an existing ledger action in rotki's currently logged in user using the ``identifier``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/ledgeractions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"identifiers" : [55]}

   :reqjson integer identifiers: The list of identifiers of the actions to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {"result": true, "message": ""}

   :resjson bool result: Returns ``true`` if all identifiers were found and deleted, otherwise returns ``false``.
   :resjson string message: Returns ``""`` if ``result`` is ``True`` else return the error message.
   :statuscode 200: Action was successfully removed.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error

Dealing with BaseHistoryEntry events
============================================

.. http:put:: /api/(version)/history/events

   Doing a PUT on this endpoint can add a new history event base entry to rotki. The unique identifier for the entry is returned as success.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/ledgeractions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "event_identifier": "0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e",
          "sequence_index": 162,
          "timestamp": 1569924574,
          "location": "blockchain",
          "event_type": "informational",
          "asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
          "balance": {"amount": "1.542", "usd_value": "1.675"},
          "location_label": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12",
          "notes": "Approve 1 SAI of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 for spending by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE",
          "event_subtype": "approve",
          "counterparty": "0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE"
      }

   .. _history_base_entry_schema_section:

   :reqjson string event_identifier: This is an identifier that could be common between multiple history base entries so that entries identifying a single event can be grouped. For ethereum transactions for example it's the transaction hash.
   :reqjson int sequence_index: This is an index that tries to provide the order of history entries for a single event_identifier.
   :reqjson int timestamp: The timestamp of the entry
   :reqjson string location: The location of the entry
   :reqjson string event_type: The main event type of the entry. Possible event types can be seen in HistoryEventType enum.
   :reqjson string asset: The asset identifier for this entry
   :reqjson object balance: The amount/usd value of the event. If not known usd_value can also be "0".
   :reqjson string location_label: location_label is a string field that allows to provide more information about the location. For example when we use this structure in blockchains can be used to specify the source address.
   :reqjson string notes: This is a description of the event entry in plain text explaining what is being done. This is supposed to be shown to the user.
   :reqjson string event_subtype: Optional. An optional subtype for the entry. Possible event types can be seen in HistoryEventSubType enum.
   :reqjson string counterparty: Optional. An identifier for a potential counterparty of the event entry. For a send it's the target. For a receive it's the sender. For bridged transfer it's the bridge's network identifier. For a protocol interaction it's the protocol.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"identifier": 243},
          "message": ""
      }

   :resjsonarr int identifier: The uniquely identifying identifier for this entry.
   :statuscode 200: Entry is successfully added.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in or failure at event addition.
   :statuscode 500: Internal rotki error

.. http:patch:: /api/(version)/history/events

   Doing a PATCH on this endpoint edits an existing base history entry in rotki's currently logged in user using the given ``identifier``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/history/events HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "identifier": 243,
          "event_identifier": "0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e",
          "sequence_index": 162,
          "timestamp": 1569924574,
          "location": "blockchain",
          "event_type": "informational",
          "asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
          "balance": {"amount": "1.542", "usd_value": "1.675"},
          "location_label": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12",
          "notes": "Approve 1 SAI of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 for spending by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE",
          "event_subtype": "approve",
          "counterparty": "0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE"
      }

   The request object is the same as above, a base history entry, with the addition of the identifier which signifies which entry will be edited.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :statuscode 200: Event was successfully edited.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in. Or event to edit was not found in the DB or edit is not allowed.
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/history/events

   Doing a DELETE on this endpoint deletes a set of history entry events from the DB for the currently logged in user. If any of the identifiers is not found in the DB the entire call fails. If any of the identifiers are the last for their transaction hash the call fails.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/history/events HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"identifiers" : [55, 65, 124]}

   :reqjson list<integer> identifiers: A list of the identifiers of the history entries to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :statuscode 200: Event was successfully removed.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in or one of the identifiers to delete did not correspond to an event in the DB or one of the identifiers was for the last event in the corresponding transaction hash.
   :statuscode 500: Internal rotki error

Querying messages to show to the user
=====================================

.. http:get:: /api/(version)/messages

   Doing a GET on the messages endpoint will pop all errors and warnings from the message queue and return them. The message queue is a queue where all errors and warnings that are supposed to be see by the user are saved and are supposed to be popped and read regularly.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/messages HTTP/1.1
      Host: localhost:5042

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

   :resjson list[string] errors: A list of strings denoting errors that need to be shown to the user.
   :resjson list[string] warnings: A list of strings denoting warnings that need to be shown to the user.

   :statuscode 200: Messages popped and read successfully.
   :statuscode 500: Internal rotki error.

Querying complete action history
================================

.. http:get:: /api/(version)/history

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the history endpoint will trigger a query and processing of the history of all actions (trades, deposits, withdrawals, loans, eth transactions) within a specific time range. Passing them as a query arguments here would be given as: ``?async_query=true&from_timestamp=1514764800&to_timestamp=1572080165``. Will return the id of the generated report to query.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1514764800, "to_timestamp": 1572080165, "async_query": true}

   :reqjson int from_timestamp: The timestamp after which to return action history. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return action history. If not given all balances until now are returned.
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :param int from_timestamp: The timestamp after which to return action history. If not given zero is considered as the start.
   :param int to_timestamp: The timestamp until which to return action history. If not given all balances until now are returned.
   :param bool async_query: Boolean denoting whether this is an asynchronous query or not


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": 15,
          "message": ""
      }

   :resjson int result: The id of the generated report to later query

   :statuscode 200: History processed and returned successfully
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.


Export PnL report debug data
============================

.. http:post:: /api/(version)/history/debug

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a POST on the PnL report debug endpoint will trigger a query and export of the history of all actions (trades, deposits, withdrawals, loans, eth transactions) within a specific time range alongside the user settings and ignored events identifiers.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/history/debug HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

       {
            "from_timestamp": 1514764800,
            "to_timestamp": 1572080165,
            "async_query": false
        }

   :reqjson int from_timestamp: The timestamp after which to return action history. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return action history. If not given all balances until now are returned.
   :reqjson path directory_path: Optional. The directory the PnL debug data should be written to.
   :reqjson bool async_query: Optional boolean denoting whether this is an asynchronous query or not. Defaults to false.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
            "events": [
                {
                "identifier": 12,
                "event_identifier": "0xb626d9d9e3a5b9ecbe0c2194cf96ab7561063c6d31e0e6799d56a589b8094609",
                "sequence_index": 0,
                "timestamp": 1651258550,
                "location": "blockchain",
                "asset": "ETH",
                "balance": {
                    "amount": "3.55448345",
                    "usd_value": "24455.415502078435"
                },
                "event_type": "receive",
                "accounting_event_type": "history base entry",

                "event_subtype": null,
                "location_label": "0x19e4057A38a730be37c4DA690b103267AAE1d75d",
                "notes": "Receive 3.55448345 ETH 0xaBEA9132b05A70803a4E85094fD0e1800777fBEF -> 0x19e4057A38a730be37c4DA690b103267AAE1d75d",
                "counterparty": "0xaBEA9132b05A70803a4E85094fD0e1800777fBEF"
                },
                {
                "identifier": 8,
                "event_identifier": "0xa9905f5eaa664a53e6513f7ba2147dcebc3e54d4062df9df1925116b6a220014",
                "sequence_index": 0,
                "timestamp": 1651259834,
                "location": "blockchain",
                "accounting_event_type": "history base entry",
                "asset": "ETH",
                "balance": {
                    "amount": "0.009",
                    "usd_value": "33.85395142596176076"
                },
                "event_type": "spend",
                "event_subtype": "fee",
                "location_label": "0x19e4057A38a730be37c4DA690b103267AAE1d75d",
                "notes": "Burned 0.001367993179812 ETH for gas",
                "counterparty": "gas"
                }
            ],
            "settings": {
                "have_premium": false,
                "version": 32,
                "last_write_ts": 1654528773,
                "premium_should_sync": false,
                "include_crypto2crypto": true,
                "last_data_upload_ts": 0,
                "ui_floating_precision": 2,
                "taxfree_after_period": 31536000,
                "balance_save_frequency": 24,
                "include_gas_costs": true,
                "ksm_rpc_endpoint": "http://localhost:9933",
                "dot_rpc_endpoint": "",
                "main_currency": "USD",
                "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
                "last_balance_save": 0,
                "submit_usage_analytics": true,
                "active_modules": [
                    "uniswap",
                    "eth2",
                    "aave",
                    "loopring",
                    "balancer",
                    "yearn_vaults_v2",
                    "makerdao_vaults",
                    "compound",
                    "liquity",
                    "pickle_finance",
                    "nfts",
                    "sushiswap"
                ],
                "frontend_settings": "{\"defi_setup_done\":false,\"timeframe_setting\":\"REMEMBER\",\"visible_timeframes\":[\"All\",\"1Y\",\"3M\",\"1M\",\"2W\",\"1W\"],\"last_known_timeframe\":\"2W\",\"query_period\":5,\"profit_loss_report_period\":{\"year\":\"2022\",\"quarter\":\"ALL\"},\"thousand_separator\":\",\",\"decimal_separator\":\".\",\"currency_location\":\"after\",\"refresh_period\":-1,\"explorers\":{},\"items_per_page\":10,\"amount_rounding_mode\":0,\"value_rounding_mode\":1,\"dark_mode_enabled\":false,\"light_theme\":{\"primary\":\"#7e4a3b\",\"accent\":\"#e45325\",\"graph\":\"#96DFD2\"},\"dark_theme\":{\"primary\":\"#ff5722\",\"accent\":\"#ff8a50\",\"graph\":\"#E96930\"},\"graph_zero_based\":false,\"nfts_in_net_value\":true,\"dashboard_tables_visible_columns\":{\"ASSETS\":[\"percentage_of_total_net_value\"],\"LIABILITIES\":[\"percentage_of_total_net_value\"],\"NFT\":[\"percentage_of_total_net_value\"]},\"date_input_format\":\"%d/%m/%Y %H:%M:%S\",\"version_update_check_frequency\":24,\"enable_ens\":true}",
                "account_for_assets_movements": true,
                "btc_derivation_gap_limit": 20,
                "calculate_past_cost_basis": true,
                "display_date_in_localtime": true,
                "current_price_oracles": [
                    "coingecko",
                    "cryptocompare",
                    "uniswapv2",
                    "uniswapv3",
                    "saddle"
                ],
                "historical_price_oracles": ["manual", "cryptocompare", "coingecko"],
                "taxable_ledger_actions": [
                    "income",
                    "expense",
                    "loss",
                    "dividends income",
                    "donation received",
                    "grant"
                ],
                "pnl_csv_with_formulas": true,
                "pnl_csv_have_summary": false,
                "ssf_0graph_multiplier": 0,
                "last_data_migration": 3,
                "non_syncing_exchanges": []
            },
            "ignored_events_ids": {
                "trade": ["X124-JYI", "2325"],
                "ethereum transaction": ["0xfoo", "0xboo"]
            }
            "pnl_settings": {
                "from_timestamp": 0,
                "to_timestamp": 1656608820
            }
            },
          "message": ""
      }

   :resjson object result: This returns the requested Pnl debug data. ``"events"`` represent the history events created within specified timestamps. ``"settings"`` represent the user settings at the point when the pnl debug was exported. ``"ignored_events_ids"`` represent action identifiers ignored by the user.

   :statuscode 200: Debugging history data returned successfully
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. Error occured when creating history events for pnl debug data.
   :statuscode 500: Internal rotki error.


Import PnL report debug data
============================

.. http:put:: /api/(version)/history/debug
.. http:patch:: /api/(version)/history/debug

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the PnL report debug endpoint with a path to the debug PnL json file will import the history events, settings and ignored action identifiers.
   Doing a PATCH on the PnL report debug endpoint with the debug PnL json file will import the history events, settings and ignored action identifiers uploaded as multipart/form-data.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/history/debug HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

       {
            "filepath": "/home/user/Documents/pnl_debug.json",
            "async_query": true
        }

   :reqjson str file: The path to the exported debug PnL JSON file.
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: Boolean denoting success or failure of the query.

   :statuscode 200: Import of debug history data successfully
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. Import history data does not contain required keys. Import history data contains some invalid data types. Error importing history debug data.
   :statuscode 500: Internal rotki error.


Export action history to CSV
================================

.. http:get:: /api/(version)/history/export

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the history export endpoint will export the last previously queried history to CSV files and save them in the given directory. If history has not been queried before an error is returned.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history/export HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"directory_path": "/home/username/path/to/csvdir"}

   :reqjson str directory_path: The directory in which to write the exported CSV files
   :param str directory_path: The directory in which to write the exported CSV files

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :resjson bool result: Boolean denoting success or failure of the query
   :statuscode 200: File were exported successfully
   :statuscode 400: Provided JSON is in some way malformed or given string is not a directory.
   :statuscode 409: No user is currently logged in. No history has been processed. No permissions to write in the given directory. Check error message.
   :statuscode 500: Internal rotki error.


Download action history CSV
================================

.. http:get:: /api/(version)/history/download


   Doing a GET on the history download endpoint will download the last previously queried history to CSV files and return it in a zip file. If history has not been queried before an error is returned.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history/download HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8


Get missing acquisitions and prices
====================================

.. http:get:: /api/(version)/history/actionable_items

   .. note::
      This endpoint should be called after getting a PnL report data.

   Doing a GET on the this endpoint will return all missing acquisitions and missing prices encountered during generation of the last PnL report.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history/actionable_items HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "report_id": 42,
            "missing_acquisitions": [
              {
                "asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359v",
                "time": 1428994442,
                "found_amount": "0",
                "missing_amount": "0.1"
              },
              {
                "asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
                "time": 1439048640,
                "found_amount": "0",
                "missing_amount": "14.36963"
              },
              {
                "asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
                "time": 1439994442,
                "found_amount": "0",
                "missing_amount": "0.0035000000"
              },
              {
                "asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
                "time": 1439994442,
                "found_amount": "0",
                "missing_amount": "1.7500"
              }
            ],
          "missing_prices": [
            {
              "from_asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
              "to_asset": "AVAX",
              "time": 1439994442,
              "rate_limited": false,
            },
            {
              "from_asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
              "to_asset": "USD",
              "time": 1439995442,
              "rate_limited": true,
            }
          ]
        },
        "message": ""
      }

   :resjson object result: An object with missing acquisitions and prices data.
   :resjson int report_id: [Optional -- missing if no report was ran]. The id of the PnL report for which the actionable items were generated.
   :resjson list missing_prices: A list that contains entries of missing prices found during PnL reporting.
   :resjsonarr str from_asset: The asset whose price is missing.
   :resjsonarr str to_asset: The asset in which we want the price of from_asset.
   :resjsonarr int time: The timestamp for which the price is missing.
   :resjosnarr bool reate_limited: True if we couldn't get the price and any of the oracles got rate limited.
   :resjson list missing_acquisitions: A list that contains entries of missing acquisitions found during PnL reporting.
   :resjsonarr str asset: The asset that is involved in the event.
   :resjsonarr int time: The timestamp this event took place in.
   :resjsonarr str found_amount: The matching amount found from an acquisition event for a spend.
   :resjsonarr str missing_amount: The corresponding acquisition amount we can't find for a particular spend.

   :statuscode 200: Data were queried successfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.


Querying history progress status
=================================

.. http:get:: /api/(version)/history/status


   Doing a GET on the history's query current status will return information about the progress of the current historical query process.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history/status HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "processing_state": "Querying kraken exchange history",
              "total_progress": "50%"
          }
          "message": ""
      }

   :resjson str processing_state: The name of the task that is currently being executed for the history query and profit/loss report.
   :resjson str total_progress: A percentage showing the total progress of the profit/loss report.
   :statuscode 200: Data were queried successfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.


Query saved PnL Reports
=================================

.. http:get:: /api/(version)/reports/(report_id)


   Doing a GET on the PnL reports endpoint with an optional report id will return information for that report or for all reports. Free users can only query up to 20 saved reports.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/reports/4 HTTP/1.1
      Host: localhost:5042

   :reqview int report_id: An optional id to limit the query to that specific report.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
          "entries":[
            {
              "identifier":2,
              "timestamp":1637931305,
              "start_ts":15,
              "end_ts":1637928988,
              "first_processed_timestamp":null,
              "last_processed_timestamp": 1602042717,
              "size_on_disk":14793,
              "settings": {
                  "profit_currency": "USD",
                  "taxfree_after_period": 365,
                  "include_crypto2crypto": true,
                  "calculate_past_cost_basis": true,
                  "include_gas_costs": true,
                  "account_for_assets_movements": true,
                  "cost_basis_method": "lifo",
                  "eth_staking_taxable_after_withdrawal_enabled": true
              },
              "overview": {
                  "trade": {"free": "0", "taxable": "60.1"},
                  "transaction event": {"free": "0", "taxable": "40.442"},
                  "fee": {"free": "10", "taxable": "55.5"}
              }
            },
            {
              "identifier":3,
              "timestamp":1637931305,
              "start_ts":0,
              "end_ts":1637928988,
              "first_processed_timestamp":null,
              "last_processed_timestamp": 1602042717,
              "size_on_disk":6793,
              "settings": {
                  "profit_currency": "USD",
                  "taxfree_after_period": 365,
                  "include_crypto2crypto": true,
                  "calculate_past_cost_basis": true,
                  "include_gas_costs": true,
                  "account_for_assets_movements": true,
                  "cost_basis_method": "fifo",
                  "eth_staking_taxable_after_withdrawal_enabled": false
              },
              "overview": {
                  "trade": {"free": "0", "taxable": "60.1"},
                  "fee": {"free": "10", "taxable": "55.5"}
              }
            },
            {
              "identifier":4,
              "timestamp":1647931305,
              "start_ts":0,
              "end_ts":1637928988,
              "first_processed_timestamp":null,
              "last_processed_timestamp": 1602042717,
              "size_on_disk":23493,
              "settings": {
                  "profit_currency": "USD",
                  "taxfree_after_period": 365,
                  "include_crypto2crypto": true,
                  "calculate_past_cost_basis": true,
                  "include_gas_costs": true,
                  "account_for_assets_movements": true,
                  "cost_basis_method": "fifo",
                  "eth_staking_taxable_after_withdrawal_enabled": false
              },
              "overview": {
                  "asset movement": {"free": "0", "taxable": "5"},
                  "fee": {"free": "10", "taxable": "55.5"}
              }
            }
          ],
          "entries_found":3,
          "entries_limit":20
        },
        "message":""
      }

   :resjson int identifier: The identifier of the PnL report
   :resjson int start_ts: The end unix timestamp of the PnL report
   :resjson int end_ts: The end unix timestamp of the PnL report
   :resjson int first_processed_timestamp: The timestamp of the first even we processed in the PnL report or 0 for empty report.
   :resjson int size_on_disk: An approximation of the size of the PnL report on disk.


   :resjson object overview: The overview contains an entry for totals per event type. Each entry contains pnl breakdown (free/taxable for now).
   :resjson int last_processed_timestamp: The timestamp of the last processed action. This helps us figure out when was the last action the backend processed and if it was before the start of the PnL period to warn the user WHY the PnL is empty.
   :resjson int processed_actions: The number of actions processed by the PnL report. This is not the same as the events shown within the report as some of them may be before the time period of the report started. This may be smaller than "total_actions".
   :resjson int total_actions: The total number of actions to be processed  by the PnL report. This is not the same as the events shown within the report as some of them they may be before or after the time period of the report.
   :resjson int entries_found: The number of reports found if called without a specific report id.
   :resjson int entries_limit: -1 if there is no limit (premium). Otherwise the limit of saved reports to inspect is 20.

   **Settings**
   This object contains an entry per PnL report setting.
   :resjson str profit_currency: The identifier of the asset used as profit currency in the PnL report.
   :resjson integer taxfree_after_period: An optional integer for the value of taxfree_after_period setting. Can be either null or an integer.
   :resjson bool include_crypto2crypto: The value of the setting used in the PnL report.
   :resjson bool calculate_past_cost_basis: The value of the setting used in the PnL report.
   :resjson bool include_gas_costs: The value of the setting used in the PnL report.
   :resjson bool account_for_assets_movements: The value of the setting used in the PnL report.
   :resjson str cost_basis_method: The method for cost basis calculation. Either fifo or lifo.
   :resjson bool eth_staking_taxable_after_withdrawal_enabled: A boolean indicating whether the staking of ETH is taxable only after the merge and withdrawals are enabled (true) or (false) if each eth staking event is considered taxable at the point of receiving if if you can't yet withdraw.
   :statuscode 200: Data were queried successfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.

Get saved events of a PnL Report
====================================

.. http:post:: /api/(version)/reports/(report_id)/data


   Doing a POST on the PnL reports data endpoint with a specific report id and optional pagination and timestamp filtering will query the events of the given report.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/reports/4/data HTTP/1.1
      Host: localhost:5042

   :reqview int report_id: Optional. The id of the report to query as a view arg.
   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson str from_timestamp: Optional. A filter for the from_timestamp of the range of events to query.
   :reqjson str to_timestamp: Optional. A filter for the to_timestamp of the range of events to query.
   :reqjson list[string] order_by_attributes: Optional. Default is ["timestamp"]. The list of the attributes to order results by.
   :reqjson list[bool] ascending: Optional. Default is [false]. The order in which to return results depending on the order by attribute.
   :reqjson str event_type: Optional. Not used yet. In the future will be a filter for the type of event to query.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "entries": [{
		"asset": "BTC",
		"cost_basis": {
		    "is_complete": true,
		    "matched_acquisitions": [
			{
			    "amount": "0.001",
			    "event": {
				"full_amount": "1",
				"index": 11,
				"rate": "100.1",
				"timestamp": 1458994442
			    },
			    "taxable": false}
		     ]},
		"free_amount": "1E-11",
		"location": "bitmex",
		"notes": "bitmex withdrawal",
		"pnl_free": "-1.0010E-9",
		"pnl_taxable": "0.00",
		"price": "9367.55",
		"taxable_amount": "0",
		"timestamp": 1566572401,
		"type": "asset movement"
            }, {
		"asset": "XMR",
		"cost_basis": null,
		"free_amount": "0",
		"location": "poloniex",
		"notes": "Buy XMR(Monero) with ETH(Ethereum).Amount in",
		"pnl_free": "0",
		"pnl_taxable": "0",
		"price": "12.47924607060",
		"taxable_amount": "1.40308443",
		"timestamp": 1539713238,
		"type": "trade"
        }],
        "entries_found": 2,
        "entries_limit": 1000
       },
       "message": ""
      }

   :resjson str asset: The asset that is involved in the event.
   :resjson object cost_basis: Can be null. An object describing the cost basis of the event if it's a spend event. Contains a boolean attribute ``"is_complete"`` to denoting if we have complete cost basis information for the spent asset or not. If not then this means that rotki does not know enough to properly calculate cost basis. The other attribute is ``"matched_acquisitions"`` a list of matched acquisition events from which the cost basis is calculated. Each event has an ``"amount"`` attribute denoting how much of the acquisition event this entry uses. A ``"taxable"`` attribute denoting if this acquisition concerns taxable or tax-free spend. Then there is also an event which shows the full event. It's attributes show the full amount bought, when, at what rate and the index of the event in the PnL report.
   :resjson str free_amount: The amount of the event that counts as tax free.
   :resjson str taxable_amount: The amount of the event that counts as taxable.
   :resjson str location: The location this event took place in.
   :resjson str notes: A description of the event.
   :resjson str pnl_free: The non-taxable profit/loss caused by this event.
   :resjson str pnl_taxable: The taxable profit/loss caused by this event.
   :resjson str price: The price in profit_currency for asset used
   :resjson str taxable_amount: The amount of the event that counts as taxable.
   :resjson int timestamp: The timestamp this event took place in.
   :resjson str type: The type of event. Can be any of the possible accounting event types.
   :resjson str group_id: Optional. Can be missing. An id signifying events that should be grouped together in the frontend. If missing no grouping needs to happen.

   :statuscode 200: Report event data was successfully queried.
   :statuscode 400: Report id does not exist.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.

Purge PnL report and all its data
====================================

.. http:delete:: /api/(version)/reports/(report_id)


   Doing a DELETE on the PnL reports endpoint with a specific report will remove the given report and all of its saved events from the DB.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/reports/4 HTTP/1.1
      Host: localhost:5042

   :reqview int report_id: The id of the report to delete as a view arg.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :statuscode 200: Report was deleted.
   :statuscode 400: Report id does not exist.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.

Querying periodic data
======================

.. http:get:: /api/(version)/periodic


   Doing a GET on the periodic data endpoint will return data that would be usually frequently queried by an application. Check the example response to see what these data would be.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/periodic HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "last_balance_save": 1572345881,
              "connected_eth_nodes": ["nodeX", "nodeY"],
              "last_data_upload_ts": 0
          }
          "message": ""
      }

   :resjson int last_balance_save: The last time (unix timestamp) at which balances were saved in the database.
   :resjson list connected_eth_nodes: A list of nodes that we are connected to.
   :statuscode 200: Data were queried successfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.


Getting blockchain account data
===============================
.. http:get:: /api/(version)/blockchains/(name)/

   .. note::
      Supported blockchains: ``"BTC", "BCH", "ETH", "KSM", "DOT", "AVAX"``

   Doing a GET on the blockchains endpoint with a specific blockchain queries account data information for that blockchain.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/ HTTP/1.1
      Host: localhost:5042

   .. _blockchain_accounts_result:

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result" : [{
              "address": "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B",
              "label": "my new metamask",
              "tags": ["public", "metamask"]
           }, {
              "address": "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b",
              "label": null,
              "tags": ["private"]
           }, {
              "address": "G7UkJAutjbQyZGRiP8z5bBSBPBJ66JbTKAkFDq3cANwENyX",
              "label": "my Kusama account",
              "tags": null
           }],
           "message": "",
      }

   :resjson list result: A list with the account data details
   :resjsonarr string address: The address, which is the unique identifier of each account. For BTC blockchain query and if the entry is an xpub then this attribute is missing.
   :resjsonarr string xpub: The extended public key. This attribute only exists for BTC blockchain query and if the entry is an xpub
   :resjsonarr string label: The label to describe the account. Can also be null.
   :resjsonarr list tags: A list of tags associated with the account. Can also be null.

   :statuscode 200: Account data successfully queried.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/BTC/ HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result" : {
              "standalone": [{
                  "address": "bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5",
                  "label": null,
                  "tags": ["private"],
                  }, {
                  "address": "bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra",
                  "label": "some label",
                  "tags": null,
              }],
              "xpubs": [{
                  "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
                  "derivation_path": "m/0/0",
                  "label": "ledger xpub",
                  "tags": ["super secret", "awesome"],
                  "addresses": [{
                      "address": "1LZypJUwJJRdfdndwvDmtAjrVYaHko136r",
                      "label": "derived address",
                      "tags": ["super secret", "awesome", "derived"]
                      }, {
                      "address": "1AMrsvqsJzDq25QnaJzX5BzEvdqQ8T6MkT",
                      "label": null,
                      "tags": null
                      }]
                  }, {
                  "xpub": "zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q",
                  "derivation_path": null,
                  "label": "some label",
                  "tags": null,
                  "addresses": null,
              }]
          },
           "message": "",
      }

   :resjson list result: An object with the account data details. Has two attributes. ``"standalone"`` for standalone addresses. That follows the same response format as above. And ``"xpub"`` for bitcoin xpubs. Below we will see the format of the xpub response.
   :resjsonarr string xpub: The extended public key string
   :resjsonarr string derivation_path: [Optional] If existing this is the derivation path from which to start deriving accounts from the xpub.
   :resjsonarr string label: [Optional] The label to describe the xpub. Can also be null.
   :resjsonarr list tags: [Optional] A list of tags associated with the account. Can also be null.
   :resjsonarr list addresses: [Optional] A list of address objects  derived by the account. Can also be null. The attributes of each object are as seen in the previous response.

   :statuscode 200: Account data successfully queried.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

Getting all DeFi balances
=========================

.. http:get:: /api/(version)/blockchains/ETH/defi

   Doing a GET on the DeFi balances endpoint will return a mapping of all accounts to their respective balances in DeFi protocols.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/defi HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": [{
                  "protocol": {"name": "Curve"},
                  "balance_type": "Asset",
                  "base_balance": {
                      "token_address": "0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                      "token_name": "Y Pool",
                      "token_symbol": "yDAI+yUSDC+yUSDT+yTUSD",
                      "balance": {
                          "amount": "1000",
                          "usd_value": "1009.12"
                      }
                  },
                  "underlying_balances": [{
                      "token_address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                      "token_name": "Dai Stablecoin",
                      "token_symbol": "DAI",
                      "balance": {
                          "amount": "200",
                          "usd_value": "201.12"
                      }
                  }, {
                      "token_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                      "token_name": "USD//C",
                      "token_symbol": "USDC",
                      "balance": {
                          "amount": "300",
                          "usd_value": "302.14"
                      }
                  }, {
                      "token_address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                      "token_name": "Tether USD",
                      "token_symbol": "USDT",
                      "balance": {
                          "amount": "280",
                          "usd_value": "281.98"
                      }
                  }, {
                      "token_address": "0x0000000000085d4780B73119b644AE5ecd22b376",
                      "token_name": "TrueUSD",
                      "token_symbol": "TUSD",
                      "balance": {
                          "amount": "220",
                          "usd_value": "221.201"
                      }
                  }]
              }, {
                  "protocol": {"name": "Compound"},
                  "balance_type": "Asset",
                  "base_balance": {
                      "token_address": "0x6C8c6b02E7b2BE14d4fA6022Dfd6d75921D90E4E",
                      "token_name": "Compound Basic Attention Token",
                      "token_symbol": "cBAT",
                      "balance": {
                          "amount": "8000",
                          "usd_value": "36.22"
                      }
                  },
                  "underlying_balances": [{
                      "token_address": "0x0D8775F648430679A709E98d2b0Cb6250d2887EF",
                      "token_name": "Basic Attention Token",
                      "token_symbol": "BAT",
                      "balance": {
                          "amount": "150",
                          "usd_value": "36.21"
                      }
                  }]
              }, {
                  "protocol": {"name": "Compound"},
                  "balance_type": "Asset",
                  "base_balance": {
                      "token_address": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
                      "token_name": "Compound",
                      "token_symbol": "COMP",
                      "balance": {
                          "amount": "0.01",
                          "usd_value": "1.9"
                      }
                  },
                  "underlying_balances": []
              }],
              "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B": [{
                  "protocol": {"name": "Aave"},
                  "balance_type": "Asset",
                  "base_balance": {
                      "token_address": "0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d",
                      "token_name": "Aave Interest bearing DAI",
                      "token_symbol": "aDAI",
                      "balance": {
                          "amount": "2000",
                          "usd_value": "2001.95"
                      }
                  },
                  "underlying_balances": [{
                      "token_address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                      "token_name": "Dai Stablecoin",
                      "token_symbol": "DAI",
                      "balance": {
                          "amount": "2000",
                          "usd_value": "2001.95"
                      }
                  }]
              }],
          },
          "message": ""
      }

   :resjson object result: A mapping from account to list of DeFi balances.
   :resjsonarr object protocol: The name of the protocol. Since these names come from Zerion check `here <https://github.com/zeriontech/defi-sdk#supported-protocols>`__ for supported names.
   :resjsonarr string balance_type: One of ``"Asset"`` or ``"Debt"`` denoting that one if deposited asset in DeFi and the other a debt or liability.
   :resjsonarr string base_balance: A single DefiBalance entry. It's comprised of a token address, name, symbol and a balance. This is the actually deposited asset in the protocol. Can also be a synthetic in case of synthetic protocols or lending pools.
   :resjsonarr string underlying_balances: A list of underlying DefiBalances supporting the base balance. Can also be an empty list. The format of each balance is the same as that of base_balance. For lending this is going to be the normal token. For example for aDAI this is DAI. For cBAT this is BAT etc. For pools this list contains all tokens that are contained in the pool.

   :statuscode 200: Balances successfully queried.
   :statuscode 409: User is not logged in or if using own chain the chain is not synced.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting current ethereum MakerDAO DSR balance
=================================================

.. http:get:: /api/(version)/blockchains/ETH/modules/makerdao/dsrbalance

   Doing a GET on the makerdao dsrbalance resource will return the current balance held in DSR by any of the user's accounts that ever had DAI deposited in the DSR and also the current DSR percentage.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/makerdao/dsrbalance HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "current_dsr": "8.022774065220581075333120100",
              "balances": {
                  "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
                      "amount": "125.24423",
                      "usd_value": "126.5231"
                  },
                  "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                      "amount": "456.323",
                      "usd_value": "460.212"
                  }
                }
          },
          "message": ""
      }

   :resjson object result: A mapping of accounts to the number of DAI they have locked in DSR and the corresponding USD value. If an account is not in the mapping rotki does not see anything locked in DSR for it.

   :statuscode 200: DSR successfully queried.
   :statuscode 409: User is not logged in. Or makerdao module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting ethereum MakerDAO DSR historical report
=================================================

.. http:get:: /api/(version)/blockchains/ETH/modules/makerdao/dsrhistory

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the makerdao dsrhistory resource will return the history of deposits and withdrawals of each account to the DSR along with the amount of DAI gained at each step and other information

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/makerdao/dsrhistory HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
                  "movements": [{
                      "movement_type": "deposit",
                      "gain_so_far": {
                          "amount": "0",
                          "usd_value": "0"
                      },
                      "value": {
                          "amount": "350",
                          "usd_value": "351.21"
                      },
                      "block_number": 9128160,
                      "timestamp": 1582706553,
                      "tx_hash": "0x988aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289"
                  }, {
                      "movement_type": "deposit",
                      "gain_so_far": {
                          "amount": "0.875232",
                          "usd_value": "0.885292"
                      },
                      "value": {
                          "amount": "50",
                          "usd_value": "50.87"
                      },
                      "block_number": 9129165,
                      "timestamp": 1582806553,
                      "tx_hash": "0x2a1bee69b9bafe031026dbcc8f199881b568fd767482b5436dd1cd94f2642443"
                  }, {
                      "movement_type": "withdrawal",
                      "gain_so_far": {
                          "amount": "1.12875932",
                          "usd_value": "1.34813"
                      },
                      "value": {
                          "amount": "350",
                          "usd_value": "353.12"
                      },
                      "block_number": 9149160,
                      "timestamp": 1592706553,
                      "tx_hash": "0x618fc9542890a2f58ab20a3c12d173b3638af11fda813e61788e242b4fc9a756"
                  }, {
                  }],
                  "gain_so_far": {
                      "amount": "1.14875932",
                      "usd_value": "1.2323"
                  }
              },
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                  "movements": [{
                      "movement_type": "deposit",
                      "gain_so_far": {
                          "amount": "0",
                          "usd_value": "0"
                      },
                      "value": {
                          "amount": "550",
                          "usd_value": "553.43"
                      },
                      "block_number": 9128174,
                      "timestamp": 1583706553,
                      "tx_hash": "0x2a1bee69b9bafe031026dbcc8f199881b568fd767482b5436dd1cd94f2642443"
                  }],
                  "gain_so_far": {
                      "amount": "0.953423",
                      "usd_value": "0.998421"
                  }
              }
          },
          "message": ""
      }

   :resjson object result: A mapping of accounts to the DSR history report of each account. If an account is not in the mapping rotki does not see anything locked in DSR for it.
   :resjson object movements: A list of deposits/withdrawals to/from the DSR for each account.
   :resjson string gain_so_far: The total gain so far in DAI from the DSR for this account. The amount is the DAI amount and the USD value is the added usd value of all the usd values of each movement again plus the usd value of the remaining taking into account current usd price
   :resjsonarr string movement_type: The type of movement involving the DSR. Can be either "deposit" or "withdrawal".
   :resjsonarr string gain_so_far: The amount of DAI gained for this account in the DSR up until the moment of the given deposit/withdrawal along with the usd value equivalent of the DAI gained for this account in the DSR up until the moment of the given deposit/withdrawal. The rate is the DAI/USD rate at the movement's timestamp.
   :resjsonarr string value: The amount of DAI deposited or withdrawn from the DSR along with the USD equivalent value of the amount of DAI deposited or withdrawn from the DSR. The rate is the DAI/USD rate at the movement's timestamp.
   :resjsonarr int block_number: The block number at which the deposit or withdrawal occurred.
   :resjsonarr int tx_hash: The transaction hash of the DSR movement

   :statuscode 200: DSR history successfully queried.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. Or makerdao module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting MakerDAO vaults basic data
===================================

.. http:get:: /api/(version)/blockchains/ETH/modules/makerdao/vaults

   Doing a GET on the makerdao vault resource will return the basic information for each vault the user has

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/makerdao/vaults HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
              "identifier": 1,
              "collateral_type": "ETH-A",
              "owner": "0xA76a9560ffFD9fC603F7d6A30c37D79665207876",
              "collateral_asset": "ETH",
              "collateral": {
                  "amount": "5.232",
                  "usd_value": "950.13"
              },
              "debt": {
                  "amount": "650",
                  "usd_value": "653.42"
              },
              "collateralization_ratio": "234.21%",
              "liquidation_ratio": "150%",
              "liquidation_price": "125.1",
              "stability_fee": "0.00%",
          }, {
              "identifier": 55,
              "collateral_type": "USDC-A",
              "owner": "0xB26a9561ffFD9fC603F7d6A30c37D79665207876",
              "collateral_asset": "eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
              "collateral": {
                  "amount": "150",
                  "usd_value": "150"
              },
              "debt": {
                  "amount": "50",
                  "usd_value": "53.2"
              },
              "collateralization_ratio": "250.551%",
              "liquidation_ratio": "150%",
              "liquidation_price": "0.45",
              "stability_fee": "0.75%",
          }]
          "message": ""
      }

   :resjson object result: A list of all vaults auto detected for the user's accounts
   :resjsonarr string identifier: A unique integer identifier for the vault.
   :resjsonarr string collateral_type: The collateral_type of the vault. e.g. ETH-A. Various collateral types can be seen here: https://catflip.co/
   :resjsonarr string owner: The address of the owner of the vault.
   :resjsonarr string collateral_asset: The identifier of the asset deposited in the vault as collateral.
   :resjsonarr string collateral: The amount of collateral currently deposited in the vault along with the current value in USD of all the collateral in the vault according to the MakerDAO price feed.
   :resjsonarr string debt: The amount of DAI owed to the vault. So generated DAI plus the stability fee interest. Along with its current usd value.
   :resjsonarr string collateralization_ratio: A string denoting the percentage of collateralization of the vault.
   :resjsonarr string liquidation_ratio: This is the current minimum collateralization ratio. Less than this and the vault is going to get liquidated.
   :resjsonarr string liquidation_price: The USD price that the asset deposited in the vault as collateral at which the vault is going to get liquidated.
   :resjsonarr string stability_fee: The current annual interest rate you have to pay for borrowing collateral from this vault type.
   :statuscode 200: Vaults successfully queried
   :statuscode 409: User is not logged in. Or makerdao module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting MakerDAO vault details
===================================

.. http:get:: /api/(version)/blockchains/ETH/modules/makerdao/vaultdetails

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the makerdao vault details resource will return additional details for each vault and also the list of vault events such as deposits, withdrawals, liquidations, debt generation and repayment.

   To get the total amount of USD lost from the vault (including liquidations) the user should simply add ``total_liquidated_usd`` and ``total_interest_owed``.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/makerdao/vaultdetails HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
              "identifier": 1,
              "collateral_asset": "ETH",
              "creation_ts": 1589067898,
              "total_interest_owed": "0.02341",
              "total_liquidated": {
                  "amount": "0",
                  "usd_value": "0"
              },
              "events": [{
                  "event_type": "deposit",
                  "value": {
                      "amount": "5.551",
                      "usd_value": "120.32"
                  },
                  "timestamp": 1589067899,
                  "tx_hash": "0x678f31d49dd70d76c0ce441343c0060dc600f4c8dbb4cee2b08c6b451b6097cd"
              }, {
                  "event_type": "generate",
                  "value": {
                      "amount": "325",
                      "usd_value": "12003.32"
                  },
                  "timestamp": 1589067900,
                  "tx_hash": "0x678f31d49dd70d76c0ce441343c0060dc600f4c8dbb4cee2b08c6b451b6097cd"
              }]
          }, {
              "identifier": 56,
              "collateral_asset": "eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
              "creation_ts": 1589067897,
              "total_interest_owed": "-751.32",
              "total_liquidated": {
                  "amount": "1050.21",
                  "usd_value": "2501.234"
              },
              "events": [{
                  "event_type": "deposit",
                  "value": {
                      "amount": "1050.21",
                      "usd_value": "10500.21"
                  },
                  "timestamp": 1589067899,
                  "tx_hash": "0x678f31d49dd70d76c0ce441343c0060dc600f4c8dbb4cee2b08c6b451b6097cd"
              }, {
                  "event_type": "generate",
                  "value": {
                      "amount": "721.32",
                      "usd_value": "7213.2"
                  },
                  "timestamp": 1589067900,
                  "tx_hash": "0x678f31d49dd70d76c0ce441343c0060dc600f4c8dbb4cee2b08c6b451b6097cd"
              }, {
                  "event_type": "liquidation",
                  "value": {
                      "amount": "500",
                      "usd_value": "5000"
                  },
                  "timestamp": 1589068000,
                  "tx_hash": "0x678f31d49dd70d76c0ce441343c0060dc600f4c8dbb4cee2b08c6b451b6097cd"
              }, {
                  "event_type": "liquidation",
                  "value": {
                      "amount": "550.21",
                      "usd_value": "5502.1"
                  },
                  "timestamp": 1589068001,
                  "tx_hash": "0x678f31d49dd70d76c0ce441343c0060dc600f4c8dbb4cee2b08c6b451b6097cd"
              }]
          }]
          "message": ""
      }

   :resjson object result: A list of all vault details detected.
   :resjsonarr string collateral_asset: The identifier of the asset deposited in the vault as collateral.
   :resjsonarr int creation_ts: The timestamp of the vault's creation.
   :resjsonarr string total_interest_owed: Total amount of DAI lost to the vault as interest rate. This can be negative, if the vault has been liquidated. In that case the negative number is the DAI that is out in the wild and does not need to be returned after liquidation. Even if the vault has been paid out this still shows how much interest was paid to the vault. So it's past and future interest owed.
   :resjsonarr string total_liquidated: The total amount/usd_value of the collateral asset that has been lost to liquidation. Will be ``0`` if no liquidations happened.
   :resjson object events: A list of all events that occurred for this vault
   :resjsonarr string event_type: The type of the event. Valid types are: ``["deposit", "withdraw", "generate", "payback", "liquidation"]``
   :resjsonarr string value: The amount/usd_value associated with the event. So collateral deposited/withdrawn, debt generated/paid back, amount of collateral lost in liquidation.
   :resjsonarr int timestamp: The unix timestamp of the event
   :resjsonarr string tx_hash: The transaction hash associated with the event.

   :statuscode 200: Vault details successfully queried
   :statuscode 409: User is not logged in. Or makerdao module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting Aave balances
========================

.. http:get:: /api/(version)/blockchains/ETH/modules/aave/balances

   Doing a GET on the aave balances resource will return the balances that the user has locked in Aave for lending and borrowing along with their current APYs.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/aave/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
                  "lending": {
                      "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                          "balance": {
                              "amount": "350.0",
                              "usd_value": "351.21"
                          },
                          "apy": "3.51%"
                      },
                      "eip155:1/erc20:0xdd974D5C2e2928deA5F71b9825b8b646686BD200": {
                          "balance": {
                              "amount": "220.21",
                              "usd_value": "363.3465"
                          },
                          "apy": "0.53%"
                      },
                  },
                  "borrowing": {
                      "eip155:1/erc20:0x80fB784B7eD66730e8b1DBd9820aFD29931aab03": {
                          "balance": {
                              "amount": "590.21",
                              "usd_value": "146.076975"
                          },
                          "variable_apr": "7.46%"
                          "stable_apr": "9.03%"
                      }
                  }
              },
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                  "lending": {},
                  "borrowing": {
                      "eip155:1/erc20:0x0D8775F648430679A709E98d2b0Cb6250d2887EF": {
                          "balance": {
                              "amount": "560",
                              "usd_value": "156.8"
                          },
                          "variable_apr": "7.46%"
                          "stable_apr": "9.03%"
                      }
                  }
              }
          },
          "message": ""
      }

   :resjson object result: A mapping of all accounts that currently have Aave balance to the balances and APY data for each account for lending and borrowing. Each key is an asset and its values are the current balance and the APY in %

   :statuscode 200: Aave balances successfully queried.
   :statuscode 409: User is not logged in. Or aave module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting Aave historical data
============================

.. http:get:: /api/(version)/blockchains/ETH/modules/aave/history

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the makerdao dsrhistory resource will return the history of deposits,withdrawals and interest payments of each account in Aave's lending.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/aave/history HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool reset_db_data: Boolean denoting whether all aave event data saved in the DB are going to be deleted and rewritten after this query. False by default.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
                  "events": [{
                      "event_type": "deposit",
                      "asset": "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F",
                      "atoken": "eip155:1/erc20:0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d",
                      "value": {
                          "amount": "350.0",
                          "usd_value": "351.21"
                      },
                      "block_number": 9128160,
                      "timestamp": 1582706553,
                      "tx_hash": "0x988aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                      "log_index": 1
                  }, {
                      "event_type": "interest",
                      "asset": "eip155:1/erc20:0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d",
                      "value": {
                          "amount": "0.5323",
                          "usd_value": "0.5482"
                      },
                      "block_number": 9129165,
                      "timestamp": 1582806553,
                      "tx_hash": "0x2a1bee69b9bafe031026dbcc8f199881b568fd767482b5436dd1cd94f2642443",
                      "log_index": 1
                  }, {
                      "event_type": "withdrawal",
                      "asset": "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F",
                      "atoken": "eip155:1/erc20:0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d",
                      "value": {
                          "amount": "150",
                          "usd_value": "150.87"
                      },
                      "block_number": 9149160,
                      "timestamp": 1592706553,
                      "tx_hash": "0x618fc9542890a2f58ab20a3c12d173b3638af11fda813e61788e242b4fc9a756",
                      "log_index": 1
                  }, {
                      "event_type": "deposit",
                      "asset": "eip155:1/erc20:0xE41d2489571d322189246DaFA5ebDe1F4699F498",
                      "atoken": "eip155:1/erc20:0x6Fb0855c404E09c47C3fBCA25f08d4E41f9F062f",
                      "value": {
                          "amount": "150",
                          "usd_value": "60.995"
                      },
                      "block_number": 9149160,
                      "timestamp": 1592706553,
                      "tx_hash": "0x618fc9542890a2f58ab20a3c12d173b3638af11fda813e61788e242b4fc9a755",
                      "log_index": 1
                  }],
                  "total_earned": {
                      "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                          "amount": "0.9482",
                          "usd_value": "1.001"
                      },
                      "eip155:1/erc20:0xE41d2489571d322189246DaFA5ebDe1F4699F498": {
                          "amount": "0.523",
                          "usd_value": "0.0253"
                      }
                  },
                  "total_lost": {
                      "eip155:1/erc20:0xFC4B8ED459e00e5400be803A9BB3954234FD50e3": {
                          "amount": "0.3212",
                          "usd_value": "3560.32"
                      }
                  }
              },
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                  "events": [{
                      "event_type": "deposit",
                      "asset": "eip155:1/erc20:0x0D8775F648430679A709E98d2b0Cb6250d2887EF",
                      "value": {
                          "amount": "500",
                          "usd_value": "124.1"
                      },
                      "block_number": 9149160,
                      "timestamp": 1592706553,
                      "tx_hash": "0x618fc9542890a2f58ab20a3c12d173b3638af11fda813e61788e242b4fc9a755",
                      "log_index": 1
                  }],
                  "total_earned_interest": {
                      "eip155:1/erc20:0x0D8775F648430679A709E98d2b0Cb6250d2887EF": {
                          "amount": "0.9482",
                          "usd_value": "0.2312"
                      }
                  },
                  "total_lost": {},
                  "total_earned_liquidations": {},
              }
          },
          "message": ""
      }

   :resjson object result: A mapping of accounts to the Aave history report of each account. If an account is not in the mapping rotki does not see anything ever deposited in Aave for it.
   :resjson object events: A list of AaveEvents. Check the fields below for the potential values.
   :resjsonarr string event_type: The type of Aave event. Can be ``"deposit"``, ``"withdrawal"``, ``"interest"``, ``"borrow"``, ``"repay"`` and ``"liquidation"``.
   :resjsonarr int timestamp: The unix timestamp at which the event occurred.
   :resjsonarr int block_number: The block number at which the event occurred. If the graph is queried this is unfortunately always 0, so UI should not show it.
   :resjsonarr string tx_hash: The transaction hash of the event.
   :resjsonarr int log_index: The log_index of the event. For the graph this is indeed a unique number in combination with the transaction hash, but it's unfortunately not the log index.
   :resjsonarr string asset: This attribute appears in all event types except for ``"liquidation"``. It shows the asset that this event is about. This can only be an underlying asset of an aToken.
   :resjsonarr string atoken: This attribute appears in ``"deposit"`` and ``"withdrawals"``. It shows the aToken involved in the event.
   :resjsonarr object value: This attribute appears in all event types except for ``"liquidation"``. The value (amount and usd_value mapping) of the asset for the event. The rate is the asset/USD rate at the event's timestamp.
   :resjsonarr string borrow_rate_mode: This attribute appears only in ``"borrow"`` events. Signifies the type of borrow. Can be either ``"stable"`` or ``"variable"``.
   :resjsonarr string borrow_rate: This attribute appears only in ``"borrow"`` events. Shows the rate at which the asset was borrowed. It's a floating point number. For example ``"0.155434"`` would means 15.5434% interest rate for this borrowing.
   :resjsonarr string accrued_borrow_interest: This attribute appears only in ``"borrow"`` events. Its a floating point number showing the accrued interest for borrowing the asset so far
   :resjsonarr  object fee: This attribute appears only in ``"repay"`` events. The value (amount and usd_value mapping) of the fee for the repayment. The rate is the asset/USD rate at the event's timestamp.
   :resjsonarr string collateral_asset: This attribute appears only in ``"liquidation"`` events. It shows the collateral asset that the user loses due to liquidation.
   :resjsonarr string collateral_balance: This attribute appears only in ``"liquidation"`` events. It shows the value (amount and usd_value mapping) of the collateral asset that the user loses due to liquidation. The rate is the asset/USD rate at the event's timestamp.
   :resjsonarr string principal_asset: This attribute appears only in ``"liquidation"`` events. It shows the principal debt asset that is repaid due to the liquidation due to liquidation.
   :resjsonarr string principal_balance: This attribute appears only in ``"liquidation"`` events. It shows the value (amount and usd_value mapping) of the principal asset whose debt is repaid due to liquidation. The rate is the asset/USD rate at the event's timestamp.
   :resjson object total_earned_interest: A mapping of asset identifier to total earned (amount + usd_value mapping) for each asset's interest earnings. The total earned is essentially the sum of all interest payments plus the difference between ``balanceOf`` and ``principalBalanceOf`` for each asset.
   :resjson object total_lost: A mapping of asset identifier to total lost (amount + usd_value mapping) for each asset. The total losst for each asset is essentially the accrued interest from borrowing and the collateral lost from liquidations.
   :resjson object total_earned_liquidations: A mapping of asset identifier to total earned (amount + usd_value mapping) for each repaid assets during liquidations.

   :statuscode 200: Aave history successfully queried.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. Or aave module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting AdEx balances
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/adex/balances

   Doing a GET on the adex balances resource will return the ADX staked in the pools of the platform.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/adex/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "0xE74ad5437C6CFB0cCD6bADda1F6b57b6E542E75e": [
                {
                    "adx_balance": {
                        "amount": "1050",
                        "usd_value": "950"
                    },
                    "contract_address": "0x4846C6837ec670Bbd1f5b485471c8f64ECB9c534",
                    "dai_unclaimed_balance": {
                        "amount": "0.221231768887185282",
                        "usd_value": "0.221895464193846837846"
                    },
                    "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                    "pool_name": "Tom"
                }
            ]
        },
        "message": "",
      }

   :resjson object result: A mapping between accounts and their balances in the AdEx pools (represented by a list where each item is a pool).
   :resjson string address: The staking contract address.
   :resjson string pool_id: The identifier of the pool.
   :resjson string pool_id: The name of the pool.
   :resjson object adx_balance: The sum of the staked ADX plus the unclaimed ADX amount the user has in the pool, and its USD value.
   :resjson object dai_unclaimed_balance: The unclaimed DAI amount the user has in the pool and its USD value.

   :statuscode 200: AdEx balances successfully queried.
   :statuscode 409: User is not logged in. Or AdEx module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting AdEx historical data
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/adex/history

   Doing a GET on the adex events history resource will return the history of staking events (e.g. withdraw, deposit) and the staking details of the pools.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/adex/history HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "0xE74ad5437C6CFB0cCD6bADda1F6b57b6E542E75e": {
                "events": [
                    {
                        "bond_id": "0x540cab9883923c01e657d5da4ca5674b6e4626b4a148224635495502d674c7c5",
                        "event_type": "deposit",
                        "identity_address": "0x2a6c38D16BFdc7b4a20f1F982c058F07BDCe9204",
                        "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                        "pool_name": "Tom",
                        "timestamp": 1604366004,
                        "tx_hash": "0x9989f47c6c0a761f98f910ac24e2438d858be96c12124a13be4bb4b3150c55ea",
                        "value": {
                            "amount": "1000",
                            "usd_value": "950"
                        }
                    },
                    {
                        "event_type": "claim",
                        "identity_address": "0x2a6c38D16BFdc7b4a20f1F982c058F07BDCe9204",
                        "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                        "pool_name": "Tom",
                        "timestamp": 1607453764,
                        "tx_hash": "0xa9ee91af823c0173fc5ada908ff9fe3f4d7c84a2c9da795f0889b3f4ace75b13",
                        "value": {
                            "amount": "50",
                            "usd_value": "45.23"
                        },
                        "token": "eip155:1/erc20:0xADE00C28244d5CE17D72E40330B1c318cD12B7c3",
                    },
                    {
                        "bond_id": "0x540cab9883923c01e657d5da4ca5674b6e4626b4a148224635495502d674c7c5",
                        "event_type": "withdraw",
                        "identity_address": "0x2a6c38D16BFdc7b4a20f1F982c058F07BDCe9204",
                        "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                        "pool_name": "Tom",
                        "timestamp": 1607453764,
                        "tx_hash": "0xa9ee91af823c0173fc5ada908ff9fe3f4d7c84a2c9da795f0889b3f4ace75b13",
                        "value": {
                            "amount": "1000",
                            "usd_value": "950"
                        }
                    },
                    {
                        "bond_id": "0x16bb43690fe3764b15a2eb8d5e94e1ac13d6ef38e6c6f9d9f9c745eaff92d427",
                        "event_type": "deposit",
                        "identity_address": "0x2a6c38D16BFdc7b4a20f1F982c058F07BDCe9204",
                        "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                        "pool_name": "Tom",
                        "timestamp": 1607453764,
                        "tx_hash": "0xa9ee91af823c0173fc5ada908ff9fe3f4d7c84a2c9da795f0889b3f4ace75b13",
                        "value": {
                            "amount": "1050",
                            "usd_value": "1015"
                        }
                    },
                    {
                        "event_type": "claim",
                        "identity_address": "0x2a6c38D16BFdc7b4a20f1F982c058F07BDCe9204",
                        "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                        "pool_name": "Tom",
                        "timestamp": 1607915796,
                        "tx_hash": "0x892e2dacbd0fcb787d7104b4f384e24fc4573294b75b9bfd91ca969119d8ed80",
                        "value": {
                            "amount": "43",
                            "usd_value": "39.233"
                        },
                        "token": "eip155:1/erc20:0xADE00C28244d5CE17D72E40330B1c318cD12B7c3",
                    },
                    {
                        "bond_id": "0x16bb43690fe3764b15a2eb8d5e94e1ac13d6ef38e6c6f9d9f9c745eaff92d427",
                        "event_type": "withdraw",
                        "identity_address": "0x2a6c38D16BFdc7b4a20f1F982c058F07BDCe9204",
                        "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                        "pool_name": "Tom",
                        "timestamp": 1607915796,
                        "tx_hash": "0x892e2dacbd0fcb787d7104b4f384e24fc4573294b75b9bfd91ca969119d8ed80",
                        "value": {
                            "amount": "1050",
                            "usd_value": "1015"
                        }
                    },
                    {
                        "bond_id": "0x30bd07a0cc0c9b94e2d10487c1053fc6a5043c41fb28dcfa3ff80a68013eb501",
                        "event_type": "deposit",
                        "identity_address": "0x2a6c38D16BFdc7b4a20f1F982c058F07BDCe9204",
                        "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                        "pool_name": "Tom",
                        "timestamp": 1607915796,
                        "tx_hash": "0x892e2dacbd0fcb787d7104b4f384e24fc4573294b75b9bfd91ca969119d8ed80",
                        "value": {
                            "amount": "1093",
                            "usd_value": "1075"
                        }
                    }
                ],
                "staking_details": [
                    {
                        "contract_address": "0x4846C6837ec670Bbd1f5b485471c8f64ECB9c534",
                        "pool_id": "0x1ce0c96393fa219d9776f33146e983a3e4a7d95821faca1b180ea0011d93a121",
                        "pool_name": "Tom",
                        "apr": "52.43%",
                        "adx_balance": {
                            "amount": "1093",
                            "usd_value": "1075"
                        },
                        "adx_unclaimed_balance": {
                            "amount": "19.75",
                            "usd_value": "5.24"
                        },
                        "dai_unclaimed_balance": {
                            "amount": "0.221231768887185282",
                            "usd_value": "0.221895464193846837846"
                        },
                        "adx_profit_loss": {
                            "amount": "93",
                            "usd_value": "81"
                        },
                        "dai_profit_loss": {
                            "amount": "0.22",
                            "usd_value": "0.21"
                        },
                        "total_staked_amount": "28809204.154057988204380985"
                    }
                ]
            }
        },
        "message": "",
      }

   :resjson object result: A mapping between accounts and their events history on the AdEx pools and the staking details of the pools.
   :resjson list[object] events: A list of all the staking events generated by the address interacting with the pools.

       - tx_hash: The transaction hash of the event.
       - timestamp: The Unix timestamp in UTC when the event happened (in seconds).
       - identity_address: The contract address associated with the user address in the platform.
       - event_type: The type of event. Can be: ``"deposit"`` (bond), ``"withdraw"`` (unbond), ``"withdraw request"`` (unbond request) and ``"claim"`` (channel withdraw).
       - value: the deposited, withdrawn or claimed ADX amount and its USD value.
       - bond_id (except claim events): The identifier of the bond, shared among deposit, withdraw and withdraw requested events that involve the same bond.
       - pool_id: The identifier of the pool.
       - pool_name: The name of the pool.
       - token (only claim events): The identifier of the tokens claimed.

   :resjson list[object] staking_details: A list of the staking details of the staking pools the address is currently staking in.

       - contract_address: The ADX staking contract address.
       - pool_id: The identifier of the pool.
       - pool_name: The name of the pool.
       - total_staked_amount: The total amount of ADX staked in the pool.
       - adx_balance: The sum of the staked ADX plus the unclaimed ADX amount the user has in the pool, and its USD value.
       - adx_unclaimed_balance: The unclaimed ADX amount the user has in the pool and its USD value.
       - dai_unclaimed_balance: The unclaimed DAI amount the user has in the pool and its USD value.
       - apr: The current staking APR in the pool.
       - adx_profit_loss: The ADX profit/loss amount and its USD value (includes unclaimed ADX).
       - dai_profit_loss: The DAI profit/loss amount and its USD value (includes unclaimed DAI).

   :statuscode 200: AdEx events history successfully queried.
   :statuscode 409: User is not logged in. Or AdEx module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting Balancer balances
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/balancer/balances

   Doing a GET on the balancer balances resource will return the balances locked in Balancer Liquidity Pools (LPs or pools).

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/balancer/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "0x49a2DcC237a65Cc1F412ed47E0594602f6141936": [
            {
              "address": "0x1efF8aF5D577060BA4ac8A29A13525bb0Ee2A3D5",
              "tokens": [
                {
                  "token": "eip155:1/erc20:0xFC4B8ED459e00e5400be803A9BB3954234FD50e3",
                  "total_amount": "2326.81686488",
                  "user_balance": {
                    "amount": "331.3943886097855861540937492",
                    "usd_value": "497.0915829146783792311406238"
                  },
                  "usd_price": "1.5",
                  "weight": "50"
                },
                {
                  "token": "eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                  "total_amount": "74878.381384930530866965",
                  "user_balance": {
                    "amount": "10664.47290875603144268225218",
                    "usd_value": "15996.70936313404716402337827"
                  },
                  "usd_price": "1.5",
                  "weight": "50"
                }
              ],
              "total_amount": "1760.714302455317821908",
              "user_balance": {
                "amount": "250.767840213663437898",
                "usd_value": "16493.80094604872554325451889"
              }
            },
            {
              "address": "0x280267901C175565C64ACBD9A3c8F60705A72639",
              "tokens": [
                {
                  "token": "eip155:1/erc20:0x2ba592F78dB6436527729929AAf6c908497cB200",
                  "total_amount": "3728.283461100135483274",
                  "user_balance": {
                    "amount": "3115.861971106915456546519315",
                    "usd_value": "4673.792956660373184819778972"
                  },
                  "usd_price": "1.5",
                  "weight": "75.0"
                },
                {
                  "token": "eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                  "total_amount": "98.530639172406329742",
                  "user_balance": {
                    "amount": "82.34563567641578625390887189",
                    "usd_value": "123.5184535146236793808633078"
                  },
                  "usd_price": "1.5",
                  "weight": "25.0"
                }
              ],
              "total_amount": "5717.338833050074822996",
              "user_balance": {
                "amount": "4778.187826034253307037",
                "usd_value": "4797.311410174996864200642280"
              }
            },
          ],
        },
        "message": "",
      }

   :resjson object result: A mapping between accounts and their Balancer balances (represented by a list where each item is a LP).
   :resjson string address: The LP contract address.
   :resjson list[object] tokens: A list with the LP underlying tokens data.

       - token: the token identifier (as string). When its an object it means the token is unknown to rotki.
       - total_amount: the total amount of this token the LP has.
       - usd_price: the token USD price.
       - user_balance: the token amount of the user and its estimated USD value.
       - weight: the weight (%) that represents the token in the LP.

   :resjson string total_amount: The total amount of liquidity tokens the LP has.
   :resjson object user_balance: The liquidity token amount of the user balance and its estimated USD value.

   :statuscode 200: Balancer balances successfully queried.
   :statuscode 409: User is not logged in. Or Balancer module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as the graph node could not be reached or returned unexpected response.

Getting Balancer events
=========================

.. http:get:: /api/(version)/blockchains/ETH/modules/balancer/history/events

   Doing a GET on the Balancer events history resource will return the history of all Balancer events (i.e. add and remove liquidity in the pools).

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/balancer/history/events HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "message": "",
          "result": {
              "0x7716a99194d758c8537F056825b75Dd0C8FDD89f": [
                  {
                    "pool_address": "0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4",
                    "pool_tokens": [
                      { "token": "eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "weight": "20" },
                      { "token": "eip155:1/erc20:0xba100000625a3754423978a60c9317c58a424e3D", "weight": "80" }
                    ],
                    "events": [
                      {
                        "tx_hash": "0xb9dff9df4e3838c75d354d62c4596d94e5eb8904e07cee07a3b7ffa611c05544",
                        "log_index": 331,
                        "timestamp": 1597144247,
                        "event_type": "mint",
                        "lp_balance": {
                          "amount": "0.042569019597126949",
                          "usd_value": "19.779488662371895"
                        },
                        "amounts": {
                          "eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "0.05",
                          "eip155:1/erc20:0xba100000625a3754423978a60c9317c58a424e3D": "0"
                        }
                      },
                      {
                        "tx_hash": "0xfa1dfeb83480e51a15137a93cb0eba9ac92c1b6b0ee0bd8551a422c1ed83695b",
                        "log_index": 92,
                        "timestamp": 1597243001,
                        "event_type": "burn",
                        "lp_balance": {
                          "amount": "0.042569019597126949",
                          "usd_value": "19.01364749076136579119809947"
                        },
                        "amounts": {
                          "eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "0.010687148200906598",
                          "eip155:1/erc20:0xba100000625a3754423978a60c9317c58a424e3D": "0.744372160905819159"
                        }
                      }
                    ],
                    "profit_loss_amounts": {
                      "eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "-0.039312851799093402",
                      "eip155:1/erc20:0xba100000625a3754423978a60c9317c58a424e3D": "0.744372160905819159"
                    },
                    "usd_profit_loss": "-0.76584117161052920880190053"
                  }
              ]
          }
      }

   :resjson object result: A mapping between accounts and their Balancer events history (grouped per liquidity pool).
   :resjson string address: The address of the user who interacted with the pool.
   :resjson list[object] events: A list of all the events generated by the address interacting with the pool.

       - tx_hash: The transaction hash of the event.
       - log_index: The index of the event in the transaction.
       - timestamp: The Unix timestamp in UTC when the event happened (in seconds).
       - event_type: The type of interaction, i.e. "mint" (add liquidity) and "burn" (remove liquidity).
       - amounts: A mapping between each pool token identifier and the amount added or removed on the event.
       - lp_balance: The amount of liquidity token (i.e. BPT) involved in the event and its estimated USD amount. This amount is set to zero if the endpoint is not able to get the USD value of the event token at a particular timestamp.

   :resjson string pool_address: The contract address of the pool.
   :resjson list[object] profit_loss_amounts: A mapping between each pool token identifier and the profit/loss amount.
   :resjson list[object] pool_tokens: A list with the LP underlying tokens data.

       - token: the token identifier (as string). When its an object it means the token is unknown to rotki.
       - weight: the weight (%) that represents the token in the LP.

   :resjson string usd_profit_loss: The total profit/loss in USD.

   :statuscode 200: Balancer events successfully queried.
   :statuscode 409: User is not logged in. Or Balancer module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as the graph node could not be reached or returned unexpected response.


Getting Compound balances
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/compound/balances

   Doing a GET on the compound balances resource will return the balances that the user has locked in Compound for lending and borrowing along with their current APYs. The APYs are return in a string percentage with 2 decimals of precision. If for some reason APY can't be queried ``null`` is returned.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/compound/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
                  "rewards": {
                      "eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888": {
                          "balance" :{
                              "amount": "3.5",
                              "usd_value": "892.5",
                          }
                      }
                  },
                  "lending": {
                      "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                          "balance": {
                              "amount": "350.0",
                              "usd_value": "351.21"
                          },
                          "apy": "3.51%"
                      },
                      "eip155:1/erc20:0xFC4B8ED459e00e5400be803A9BB3954234FD50e3": {
                          "balance": {
                              "amount": "1",
                              "usd_value": "9500"
                          },
                          "apy": null,
                      },
                  },
                  "borrowing": {
                      "ETH": {
                          "balance": {
                              "amount": "10",
                              "usd_value": "3450"
                          },
                          "apy": "7.46%"
                      }
                  }
              },
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                  "lending": {},
                  "borrowing": {
                      "eip155:1/erc20:0x0D8775F648430679A709E98d2b0Cb6250d2887EF": {
                          "balance": {
                              "amount": "560",
                              "usd_value": "156.8"
                          },
                          "apy": "7.46%"
                      }
                  }
              }
          },
          "message": ""
      }

   :resjson object result: A mapping of all accounts that currently have compound balance to the balances and APY data for each account for lending and borrowing. Each key is an asset identifier and its values are the current balance and the APY in %

   :statuscode 200: Compound balances successfully queried.
   :statuscode 409: User is not logged in. Or compound module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting compound historical data
==================================

.. http:get:: /api/(version)/blockchains/ETH/modules/compound/history

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the compound balances history resource will return all compound events for all addresses who are tracked for compound.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/compound/history HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool reset_db_data: Boolean denoting whether all compound event data saved in the DB are going to be deleted and rewritten after this query. False by default.
   :reqjson int from_timestamp: Timestamp from which to query compound historical data. If not given 0 is implied.
   :reqjson int to_timestamp: Timestamp until which to query compound historical data. If not given current timestamp is implied.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "events": [{
                  "event_type": "mint",
                  "address": "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056",
                  "block_number": 1,
                  "timestamp": 2,
                  "asset": "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F",
                  "value": {
                      "amount": "10.5",
                      "usd_value": "10.86"
                  },
                  "to_asset": "eip155:1/erc20:0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643",
                  "to_value": {
                      "amount": "165.21",
                      "usd_value": "10.86"
                  },
                  "tx_hash": "0x988aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                  "log_index": 1
              }, {
                  "event_type": "redeem",
                  "address": "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056",
                  "block_number": 1,
                  "timestamp": 2,
                  "asset": "eip155:1/erc20:0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643",
                  "value": {
                      "amount": "165.21",
                      "usd_value": "12.25"
                  },
                  "to_asset": "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F",
                  "to_value": {
                      "amount": "12.01",
                      "usd_value": "12.25"
                  },
                  "realized_pnl": {
                      "amount": "1",
                      "usd_value": "1.15"
                  },
                  "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                  "log_index": 1
              }, {
                  "event_type": "borrow",
                  "address": "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237",
                  "block_number": 1,
                  "timestamp": 2,
                  "asset": "eip155:1/erc20:0xE41d2489571d322189246DaFA5ebDe1F4699F498",
                  "value": {
                      "amount": "10",
                      "usd_value": "4.5"
                  },
                  "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                  "log_index": 1
              }, {
                  "event_type": "repay",
                  "address": "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237",
                  "block_number": 1,
                  "timestamp": 2,
                  "asset": "eip155:1/erc20:0xE41d2489571d322189246DaFA5ebDe1F4699F498",
                  "value": {
                      "amount": "10.5",
                      "usd_value": "4.8"
                  },
                  "realized_pnl": {
                      "amount": "0.5",
                      "usd_value": "0.8"
                  },
                  "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                  "log_index": 1
              }, {
                  "event_type": "liquidation",
                  "address": "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237",
                  "block_number": 1,
                  "timestamp": 2,
                  "asset": "ETH",
                  "value": {
                      "amount": "0.00005",
                      "usd_value": "0.09"
                  },
                  "to_asset": "eip155:1/erc20:0xE41d2489571d322189246DaFA5ebDe1F4699F498",
                  "to_value": {
                      "amount": "10",
                      "usd_value": "4.5"
                  }
                  "realized_pnl": null,
                  "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                  "log_index": 1
              }, {
                  "event_type": "comp",
                  "address": "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237",
                  "block_number": 1,
                  "timestamp": 2,
                  "asset": "eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888",
                  "value": {
                      "amount": "1.01",
                      "usd_value": "195"
                  },
                  "realized_pnl": {
                      "amount": "1.01",
                      "usd_value": "195"
                  },
                  "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                  "log_index": 1
              }],
              "interest_profit": {
                  "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
                      "eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888": {
                              "amount": "3.5",
                              "usd_value": "892.5",
                          },
                       "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                              "amount": "250",
                              "usd_value": "261.1",
                      }
                  },
                  "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                      "eip155:1/erc20:0xE41d2489571d322189246DaFA5ebDe1F4699F498": {
                          "amount": "0.55",
                          "usd_value": "86.1"
                      }
                  }
               },
               "debt_loss": {
                  "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                       "ETH": {
                              "amount": "0.1",
                              "usd_value": "30.5",
                      }
                  }
               },
               "liquidation_profit": {
                  "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                       "ETH": {
                              "amount": "0.00005",
                              "usd_value": "0.023",
                      }
                  }
               },
               "rewards": {
                  "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
                      "eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888": {
                              "amount": "3.5",
                              "usd_value": "892.5",
                          },
                  }
               }
          },
          "message": ""
      }

   :resjson object events: A list of mint/redeem/borrow/repay/liquidation/comp events for Compound
   :resjsonarr string event_type: The type of the compound event. Can be:
       - ``"mint"``: if depositing a token which mints a cToken equivalent.
       - ``"redeem"``: if redeeming a cToken for the underlying normal equivalent
       - ``"borrow"``: if you are borrowing an asset from compound
       - ``"repay"``: if you are repaying an asset borrowed from compound
       - ``"liquidation"``: if your borrowing position got liquidated
       - ``"comp"``: if this is a comp earning reward
   :resjsonarr string address: The address of the account involved in the event
   :resjsonarr int timestamp: The unix timestamp at which the event occurred.
   :resjsonarr int block_number: The block number at which the event occurred.
   :resjsonarr string asset: The asset involved in the event.
       - For ``"mint"`` events this is the underlying asset.
       - For ``"redeem"`` events this is the cToken.
       - For ``"borrow"`` and ``"repay"`` events this is the borrowed asset
       - For ``"liquidation"`` events this is the part of the debt that was repaid by the liquidator.
       - For ``"comp"`` events this the COMP token.
   :resjsonarr object value: The value of the asset for the event. The rate is the asset/USD rate at the event's timestamp.
   :resjsonarr string to_asset: [Optional] The target asset involved in the event.
       - For ``"mint"`` events this is the cToken.
       - For ``"redeem"`` events this is the underlying asset.
       - For ``"borrow"`` and ``"repay"`` this is missing.
       - For ``"liquidation"`` events this is asset lost to the liquidator.
   :resjsonarr object to_value: [Optional] The value of the ``to_asset`` for the event. The rate is the asset/USD rate at the event's timestamp.
   :resjsonarr object realized_pnl: [Optional]. Realized profit/loss at this event if any.
       - For ``"redeem"`` events this can be the realized profit from compound interest at this event. Amount is for the normal token.
       - For ``"repay"`` events this can be the realized loss from compound debt up to this point. Amount is for the borrowed asset.
       - For ``"comp"`` events this is the gain in COMP.

   :resjsonarr int tx_hash: The transaction hash of the event.
   :resjsonarr int log_index: The log index of the event.
   :resjson object interest_profit: A mapping of addresses to mappings of totals assets earned from lending over a given period
   :resjson object debt_loss: A mapping of addresses to mappings of totals assets lost to repayment fees and liquidation over a given period.
   :resjson object liquidation_profit: A mapping of addresses to mappings of totals assets gained thanks to liquidation repayments over a given period.
   :resjson object rewards: A mapping of addresses to mappings of totals assets (only COMP atm) gained as a reward for using Compound over a given period.

   :statuscode 200: Compound history successfully queried.
   :statuscode 409: User is not logged in. Or compound module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting Liquity balances
========================

.. http:get:: /api/(version)/blockchains/ETH/modules/liquity/balances

   Doing a GET on the liquity balances resource will return the balances that the user has in troves.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint will provide different information if called with a premium account or not. With premium accounts information about staking is provided.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/liquity/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
            "0x063c26fF1592688B73d8e2A18BA4C23654e2792E": {
                "collateral": {
                    "asset": "ETH"
                    "amount": "5.3100000000000005",
                    "usd_value": "16161.675300000001521815"
                },
                "debt": {
                    "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"
                    "amount": "6029.001719188487",
                    "usd_value": "6089.29173638037187"
                },
                "collateralization_ratio": "268.0655281381374051287323733",
                "liquidation_price": "1261.435199626818912670885158",
                "active": true,
                "trove_id": 148
            }
          },
          "message": ""
      }

   :resjson object result: A mapping of all accounts that currently have Liquity positions to ``trove`` information.

   :statuscode 200: Liquity balances successfully queried.
   :statuscode 409: User is not logged in or Liquity module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting Liquity staked amount
=============================

.. http:get:: /api/(version)/blockchains/ETH/modules/liquity/staking

   Doing a GET on the liquity balances resource will return the balances that the user has staked.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint requires a premium account.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/liquity/staking HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
            "0x063c26fF1592688B73d8e2A18BA4C23654e2792E": {
                "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"
                "amount": "177.02",
                "usd_value": "265.530"
            }
          },
          "message": ""
      }

   :resjson object result: A mapping of the amount and value of LQTY staked in the protocol.

   :statuscode 200: Liquity staking information successfully queried.
   :statuscode 409: User is not logged in or Liquity module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting Liquity stability pool infomration
==========================================

.. http:get:: /api/(version)/blockchains/ETH/modules/liquity/pool

   Doing a GET on the liquity stability pool resource will return the balances deposited in it and the rewards accrued.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint requires a premium account.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/liquity/pool HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
            "0x3DdfA8eC3052539b6C9549F12cEA2C295cfF5296":{
              "eth_gain":"43.180853032438783295",
              "lqty_gain":"94477.70111867384658505",
              "deposited":"10211401.723115634393264567"
            },
            "0xFBcAFB005695afa660836BaC42567cf6917911ac":{
              "eth_gain":"0.012830143966323228",
              "lqty_gain":"1430.186501693619414912",
              "deposited":"546555.36725208608367891"
            }
        },
        "message":""
      }

   :resjson object result: A mapping of the addresses having the liquity module enabled and their positions.
   :resjson string deposited: The amount of LUSD owned by the address deposited in the pool.
   :resjson string eth_gain: The amount of ETH gained in the pool.
   :resjson string lqty_gain: The amount of LQTY gained in the pool.

   :statuscode 200: Liquity information successfully queried.
   :statuscode 409: User is not logged in or Liquity module is not activated.
   :statuscode 500: Internal rotki error.


Getting Liquity historical trove data
=====================================

.. http:get:: /api/(version)/blockchains/ETH/modules/liquity/events/trove

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the liquity events resource will return the history of deposits, withdrawals, liquidations and trove events of each account in Liquity.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/liquity/events/ HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool reset_db_data: Boolean denoting whether all liquity event data saved in the DB are going to be deleted and rewritten after this query. False by default.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
                "0x063c26fF1592688B73d8e2A18BA4C23654e2792E": [
                        {
                            "kind": "trove",
                            "tx": "0xc8ad6f6ec244a93e1d66e60d1eab2ff2cb9de1f3a1f45c7bb4e9d2f720254137",
                            "address": "0x063c26fF1592688B73d8e2A18BA4C23654e2792E",
                            "timestamp": 1627818194,
                            "debt_after": {
                                "amount": "6029.001719188487125",
                                "usd_value": "6149.58175357225686750",
                                "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"
                            },
                            "debt_delta": {
                                "amount": "6029.001719188487125",
                                "usd_value": "6149.58175357225686750",
                                "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"
                            },
                            "collateral_after": {
                                "amount": "3.5",
                                "usd_value": "10500.0",
                                "asset": "ETH"
                            },
                            "collateral_delta": {
                                "amount": "3.5",
                                "usd_value": "10500.0",
                                "asset": "ETH"
                            },
                            "trove_operation": "Open Trove",
                            "sequence_number": "51647"
                        },
                        {
                            "kind": "trove",
                            "tx": "0x8c875e36737918807af1616cc89a084971a569f33006acba308897a80554983a",
                            "address": "0x063c26fF1592688B73d8e2A18BA4C23654e2792E",
                            "timestamp": 1627818617,
                            "debt_after": {
                                "amount": "6029.001719188487125",
                                "usd_value": "6143.552751853068380375",
                                "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"
                            },
                            "debt_delta": {
                                "amount": "0",
                                "usd_value": "0.000",
                                "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"
                            },
                            "collateral_after": {
                                "amount": "5.31",
                                "usd_value": "15930.00",
                                "asset": "ETH"
                            },
                            "collateral_delta": {
                                "amount": "1.81",
                                "usd_value": "5430.00",
                                "asset": "ETH"
                            },
                            "trove_operation": "Adjust Trove",
                            "sequence_number": "51747"
                        }
                    ]
                    "stake": [
                        {
                            "kind": "stake",
                            "tx": "0xe527749c76a3af56d86c97a8f8f8ce07e191721e9e16a0f62a228f8a8ef6d295",
                            "address": "0x063c26fF1592688B73d8e2A18BA4C23654e2792E",
                            "timestamp": 1627827057,
                            "stake_after": {
                                "amount": "177.02",
                                "usd_value": "654.974",
                                "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"
                            },
                            "stake_change": {
                                "amount": "177.02",
                                "usd_value": "654.974",
                                "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"
                            },
                            "issuance_gain": {
                                "amount": "0",
                                "usd_value": "0.00",
                                "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"
                            },
                            "redemption_gain": {
                                "amount": "0",
                                "usd_value": "0.00",
                                "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"
                            },
                            "stake_operation": "Stake Created",
                            "sequence_number": "51676"
                        }
                    ]
                }
            }
          },
          "message": ""
      }

   :resjson object result: A mapping of accounts to the Liquity history report of each account. If an account is not in the mapping rotki does not see anything ever deposited in Liquity for it.
   :resjson string kind: "trove" if it's an action in troves and "stake" if it's a change in the staking position
   :resjson int timestamp: The unix timestamp at which the event occurred.
   :resjson string tx: The transaction hash of the event.
   :resjson object debt_after: Debt in the Trove after the operation
   :resjson object collateral_after: Amount, asset and usd value of collateral at the Trove
   :resjson object debt_delta: Amount, asset and usd value of debt that the operation changed.
   :resjson object collateral_delta: Amount, asset and usd value of collateral that the operation changed.
   :resjson string trove_operation: The operation that happened in the change. Can be ``Open Trove``, ``Close Trove``, ``Adjust Trove``, ``Accrue Rewards``, ``Liquidation In Normal Mode``, ``Liquidation In Recovery Mode``, ``Redeem Collateral``

   :statuscode 200: Liquity history successfully queried.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. Or Liquity module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting Liquity historical staking data
=======================================

.. http:get:: /api/(version)/blockchains/ETH/modules/liquity/events/staking

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the liquity events resource will return the history for staking events.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/liquity/events/ HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool reset_db_data: Boolean denoting whether all liquity event data saved in the DB are going to be deleted and rewritten after this query. False by default.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
                "0x063c26fF1592688B73d8e2A18BA4C23654e2792E": [
                    {
                        "kind": "stake",
                        "tx": "0xe527749c76a3af56d86c97a8f8f8ce07e191721e9e16a0f62a228f8a8ef6d295",
                        "address": "0x063c26fF1592688B73d8e2A18BA4C23654e2792E",
                        "timestamp": 1627827057,
                        "stake_after": {
                            "amount": "177.02",
                            "usd_value": "654.974",
                            "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"
                        },
                        "stake_change": {
                            "amount": "177.02",
                            "usd_value": "654.974",
                            "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"
                        },
                        "issuance_gain": {
                            "amount": "0",
                            "usd_value": "0.00",
                            "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D"
                        },
                        "redemption_gain": {
                            "amount": "0",
                            "usd_value": "0.00",
                            "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0"
                        },
                        "stake_operation": "Stake Created",
                        "sequence_number": "51676"
                    }
                ]
          },
          "message": ""
      }

   :resjson object result: A mapping of accounts to the Liquity history report of each account. If an account is not in the mapping rotki does not see anything ever deposited in Liquity for it.
   :resjson string kind: "trove" if it's an action in troves and "stake" if it's a change in the staking position
   :resjson int timestamp: The unix timestamp at which the event occurred.
   :resjson string tx: The transaction hash of the event.
   :resjson string stake_after: Amount, asset and usd value changed in the operation over the staked position. Amount is represented in LQTY
   :resjson string stake_change: Amount, asset and usd value that the operation changed
   :resjson string stake_operation: Can be ``Stake Created``, ``Stake Increased``, ``Stake Decreased``, ``Stake Removed``, ``Gains Withdrawn``

   :statuscode 200: Liquity history successfully queried.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. Or Liquity module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting Uniswap balances
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/uniswap/v2/balances

   Doing a GET on the uniswap balances resource will return the balances locked in Uniswap Liquidity Pools (LPs or pools).

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/uniswap/v2/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "0xcf2B8EeC2A9cE682822b252a1e9B78EedebEFB02": [
            {
              "address": "0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae",
              "assets": [
                {
                  "asset": {
                    "ethereum_address": "0x364A7381A5b378CeD7AB33d1CDf6ff1bf162Bfd6",
                    "name": "DeFi-X Token",
                    "symbol": "TGX"
                  },
                  "total_amount": "9588317.030426553444567747",
                  "usd_price": "0.3015901111469715543448531276626107",
                  "user_balance": {
                    "amount": "4424094.631122964837017895643",
                    "usd_value": "1334263.191525095084350185834"
                  }
                },
                {
                  "asset": "eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7",
                  "total_amount": "2897321.681999",
                  "usd_price": "1.001",
                  "user_balance": {
                    "amount": "1336837.868136041506994516873",
                    "usd_value": "1338174.706004177548501511390"
                  }
                }
              ],
              "total_supply": "5.255427314262137581",
              "user_balance": {
                "amount": "2.424878911648769806",
                "usd_value": "2672437.897529272632851697224"
              }
            }
          ],
        },
        "message": "",
      }

   :resjson object result: A mapping between accounts and their Uniswap balances (represented by a list where each item is a LP).
   :resjson string address: The LP contract address.
   :resjson list[object] assets: A list with the LP underlying tokens data. Per item, when ``"asset"`` is an object, it means the token is unknown to rotki. ``"total_amount"`` is the total amount of this token the pool has. ``"total_amount"`` is only available to premium users. For free users ``null`` is returned. ``"usd_price"`` is the token USD price. ``"user_balance"`` contains the user token balance and its estimated USD value.
   :resjson optional[string] total_supply: The total amount of liquidity tokens the LP has. Only available for premium users via the graph query. For free users ``null`` is returned.
   :resjson object user_balance: The liquidity token user balance and its USD value.

   :statuscode 200: Uniswap balances successfully queried.
   :statuscode 409: User is not logged in. Or Uniswap module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting Uniswap V3 balances
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/uniswap/v3/balances

   Doing a GET on the uniswap v3 balances resource will return the balances locked in Uniswap V3 Liquidity Pools (LPs or pools).

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/uniswap/v3/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "0xcf2B8EeC2A9cE682822b252a1e9B78EedebEFB02": [
            {
              "address": "0x318BE2AA088FFb991e3F6E61AFb276744e36F4Ae",
              "nft_id": 223251,
              "price_range": ["1000", "1500"],
              "assets": [
                {
                  "asset": {
                    "ethereum_address": "0x364A7381A5b378CeD7AB33d1CDf6ff1bf162Bfd6",
                    "name": "DeFi-X Token",
                    "symbol": "TGX"
                  },
                  "total_amount": "410064.7008276195",
                  "usd_price": "0.3015901111469715543448531276626107",
                  "user_balance": {
                    "amount": "4.631122964837017895643",
                    "usd_value": "1334263.191525095084350185834"
                  }
                },
                {
                  "asset": "eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7",
                  "total_amount": "1251.608339987909",
                  "usd_price": "1.001",
                  "user_balance": {
                    "amount": "1336837.868136041506994516873",
                    "usd_value": "1338174.706004177548501511390"
                  }
                }
              ],
              "total_supply": null,
              "user_balance": {
                "amount": "0",
                "usd_value": "2672437.897529272632851697224"
              }
            }
          ],
        },
        "message": "",
      }

   :resjson object result: A mapping between accounts and their Uniswap V3 balances (represented by a list where each item is a LP).
   :resjson string address: The LP contract address.
   :resjson int nft_id: The LP position NFT ID.
   :resjson string price_range: The range of prices the LP position is valid for.
   :resjson list[object] assets: A list with the LP underlying tokens data. Per item, when ``"asset"`` is an object, it means the token is unknown to rotki. ``"total_amount"`` is the total amount of this token the pool has. ``"usd_price"`` is the token USD price. ``"user_balance"`` contains the user token balance and its estimated USD value.
   :resjson string total_supply: The total amount of liquidity tokens the LP has. This is ``null`` as Uniswap V3 does not store LP as tokens.
   :resjson object user_balance: The liquidity token user balance and its USD value.

   :statuscode 200: Uniswap balances successfully queried.
   :statuscode 409: User is not logged in. Or Uniswap module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting Uniswap events
=========================

.. http:get:: /api/(version)/blockchains/ETH/modules/uniswap/history/events

   Doing a GET on the uniswap events history resource will return the history of all uniswap events (i.e. add and remove liquidity in the pools).

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/uniswap/history/events HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "message": "",
          "result": {
              "0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F": [
                  {
                      "address": "0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F",
                      "events": [
                          {
                              "amount0": "953.198109979915172437",
                              "amount1": "720.804729278838558402",
                              "event_type": "mint",
                              "log_index": 232,
                              "lp_amount": "190.200269390899700166",
                              "timestamp": 1597412453,
                              "tx_hash": "0x95c31c24811aa89890f586455230a21b5e6805571291c41f2429c0b27ffa6494",
                              "usd_price": "1498.982998827867862380542829830168"
                          },
                          {
                              "amount0": "689.108242482979840535",
                              "amount1": "632.127650995837381138",
                              "event_type": "burn",
                              "log_index": 100,
                              "lp_amount": "190.200269390899700166",
                              "timestamp": 1597906014,
                              "tx_hash": "0xf5c8fb7369d00f306c615d664021de2b0498e74edc538f7767c66f477adaeec5",
                              "usd_price": "1336.795325171526015938992923665357"
                          }
                      ],
                      "pool_address": "0x2C7a51A357d5739C5C74Bf3C96816849d2c9F726",
                      "profit_loss0": "264.089867496935331902",
                      "profit_loss1": "88.677078283001177264",
                      "token0": "eip155:1/erc20:0x0e2298E3B3390e3b945a5456fBf59eCc3f55DA16",
                      "token1": "eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                      "usd_profit_loss": "162.1876736563418464415499063"
                  }
              ]
          }
      }


   :resjson object result: A mapping between accounts and their Uniswap events history (grouped per liquidity pool)
   :resjson string address: The address of the user who interacted with the pool
   :resjson list[object] events: A list of all the events generated by the address interacting with the pool

       - event_type: The type of interaction, i.e. "mint" (add liquidity) and "burn" (remove liquidity).
       - amount0: The amount of token0 involved in the event.
       - amount1: The amount of token1 involved in the event.
       - lp_amount: The amount of liquidity token (i.e. UNI-V2) involved in the event.
       - usd_price: The USD amount involved in the event.
       - log_index: The index of the event in the transaction.
       - tx_hash: The transaction hash of the event.
       - timestamp: The Unix timestamp in UTC when the event happened (in seconds).

   :resjson string pool_address: The contract address of the pool.
   :resjson string profit_loss0: The token0 profit/loss.
   :resjson string profit_loss1: The token1 profit/loss.
   :resjson object token0: The pool's pair left token identifier
   :resjson object token1: The pool's pair right token identifier.
   :resjson string usd_profit_loss: The total profit/loss in USD.


   :statuscode 200: Uniswap events successfully queried.
   :statuscode 409: User is not logged in. Or Uniswap module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.


Getting yearn finance vaults balances
==========================================

.. http:get:: /api/(version)/blockchains/ETH/modules/yearn/vaults/balances

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the yearn finance vaults balances resource will return all yearn vault balances.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/yearn/vaults/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                  "YCRV Vault": {
                      "underlying_token": "eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                      "vault_token": "eip155:1/erc20:0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c",
                      "underlying_value": {
                          "amount": "25", "usd_value": "150"
                      },
                      "vault_value": {
                          "amount": "19", "usd_value": "150"
                      },
                      "roi": "25.55%",
                  },
                  "YYFI Vault": {
                      "underlying_token": "eip155:1/erc20:0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e",
                      "vault_token": "eip155:1/erc20:0xBA2E7Fed597fd0E3e70f5130BcDbbFE06bB94fe1",
                      "underlying_value": {
                          "amount": "25", "usd_value": "150"
                      },
                      "vault_value": {
                          "amount": "19", "usd_value": "150"
                      },
                      "roi": "5.35%",
                  }
              },
          "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
              "YALINK Vault": {
                      "underlying_token": "eip155:1/erc20:0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84",
                      "vault_token": "eip155:1/erc20:0x29E240CFD7946BA20895a7a02eDb25C210f9f324",
                      "underlying_value": {
                          "amount": "25", "usd_value": "150"
                      },
                      "vault_value": {
                          "amount": "19", "usd_value": "150"
                      },
                      "roi": "35.15%",
              }
          }
          },
          "message": ""
      }

   :resjson object result: A mapping of addresses to a mapping of vault names to vault balances
   :resjsonarr string underlying_token: The symbol of the token that is deposited to the vault
   :resjsonarr string vault_token: The symbol of the token that is minted when you deposit underlying token to the vault
   :resjsonarr object underlying_value: The value of the underlying token for the vault.
   :resjsonarr object vault_value: The value of the vault token for the vault.
   :resjsonarr str roi: The Return of Investment for the vault since its creation


   :statuscode 200: Yearn vault balances successfully queried.
   :statuscode 409: User is not logged in. Or yearn module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting yearn finance vaults historical data
=============================================

.. http:get:: /api/(version)/blockchains/ETH/modules/yearn/vaults/history

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the yearn finance vaults history resource will return all yearn vault related events for addresses that have utilized yearn finance vaults.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/yearn/vaults/history HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool reset_db_data: Boolean denoting whether all yearn event data saved in the DB are going to be deleted and rewritten after this query. False by default.
   :reqjson int from_timestamp: Timestamp from which to query yearn vaults historical data. If not given 0 is implied.
   :reqjson int to_timestamp: Timestamp until which to query yearn vaults historical data. If not given current timestamp is implied.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                  "YCRV Vault": {
                      "events": [{
                          "event_type": "deposit",
                          "block_number": 1,
                          "timestamp": 1,
                          "from_asset": "eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                          "from_value": {
                              "amount": "115000", "usd_value": "119523.23"
                          },
                          "to_asset": "eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                          "to_value": {
                              "amount": "108230.234", "usd_value": "119523.23"
                          },
                          "realized_pnl": null,
                          "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                          "log_index": 1
                      }, {
                          "event_type": "withdraw",
                          "block_number": 1,
                          "timestamp": 1,
                          "from_asset": "eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                          "from_value": {
                              "amount": "108230.234", "usd_value": "125321.24"
                          },
                          "to_asset": "eip155:1/erc20:0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                          "to_value": {
                              "amount": "117500.23", "usd_value": "123500.32"
                          },
                          "realized_pnl": {
                              "amount": "2500.23", "usd_value": "2750.452"
                          },
                          "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                          "log_index": 1
                      }],
                      "profit_loss": {
                              "amount": "2500.23", "usd_value": "2750.452"
                      }
                  },
                  "YYFI Vault": {
                      "events": [{
                          "event_type": "deposit",
                          "block_number": 1,
                          "timestamp": 1,
                          "from_asset": "eip155:1/erc20:0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e",
                          "from_value": {
                              "amount": "5", "usd_value": "155300.23"
                          },
                          "to_asset": "yYFI",
                          "to_value": {
                              "amount": "4.97423", "usd_value": "154300.44"
                          },
                          "realized_pnl": null,
                          "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                          "log_index": 1
                      }],
                      "profit_loss": {
                              "amount": "0.05", "usd_value": "1500"
                      }
              }
          },
          "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
              "YSRENCURVE Vault": {
                      "events": [{
                          "event_type": "deposit",
                          "block_number": 1,
                          "timestamp": 1,
                          "from_asset": "eip155:1/erc20:0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3",
                          "from_value": {
                              "amount": "20", "usd_value": "205213.12"
                          },
                          "to_asset": "eip155:1/erc20:0x7Ff566E1d69DEfF32a7b244aE7276b9f90e9D0f6",
                          "to_value": {
                              "amount": "19.8523", "usd_value": "2049874.23"
                          },
                          "realized_pnl": null,
                          "tx_hash": "0x188aea85b54c5b2834b144e9f7628b524bf9faf3b87821aa520b7bcfb57ab289",
                          "log_index": 1
                      }],
                      "profit_loss": {
                              "amount": "0.1", "usd_value": "1984.23"
                      }
              }
          }},
          "message": ""
      }

   :resjson object result: A mapping of addresses to vault history results
   :resjsonarr string event_type: The type of the yearn vault event.
       - ``"deposit"``: when you deposit a token in the vault
       - ``"withdraw"``: when you withdraw a token from the vault
   :resjsonarr int timestamp: The unix timestamp at which the event occurred.
   :resjsonarr int block_number: The block number at which the event occurred.
   :resjsonarr string from_asset: The source asset involved in the event.
       - For ``"deposit"`` events this is the asset being deposited in the vault
       - For ``"withdraw"`` events this is the vault token that is being burned and converted to the original asset.
   :resjsonarr object from_value: The value of the from asset for the event. The rate should be the asset/USD rate at the event's timestamp. But in reality due to current limitations of our implementation is the USD value at the current timestamp. We will address this soon.
   :resjsonarr string to_asset: The target asset involved in the event.
       - For ``"deposit"`` events this is the vault token that is minted to represent the equivalent of the deposited asset.
       - For ``"withdraw"`` events this is the original token that the user withdrew from the vault
   :resjsonarr object to_value: The value of the to asset for the event. The rate should be the asset/USD rate at the event's timestamp. But in reality due to current limitations of our implementation is the USD value at the current timestamp. We will address this soon.
   :resjsonarr object realized_pnl: [Optional]. Realized profit/loss at this event if any. May happen for withdraw events. Same limitation as the usd value in from/to value applies.
   :resjsonarr int tx_hash: The transaction hash of the event.
   :resjsonarr int log_index: The log index of the event.
   :resjson object profit_loss: The total profit/loss for the vault

   :statuscode 200: Yearn vaults history successfully queried.
   :statuscode 409: User is not logged in. Or yearn module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting yearn finance V2 vaults balances
==========================================

.. http:get:: /api/(version)/blockchains/ETH/modules/yearn/vaultsv2/balances

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the yearn finance vaults V2 balances resource will return all yearn vault balances.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/yearn/vaultsv2/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
            "0x915C4580dFFD112db25a6cf06c76cDd9009637b7":{
              "0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9":{
                  "underlying_token":"eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                  "vault_token":"eip155:1/erc20:0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9",
                  "underlying_value":{
                    "amount":"74.292820",
                    "usd_value":"105.0"
                  },
                  "vault_value":{
                    "amount":"70",
                    "usd_value":"105.0"
                  },
                  "roi":"-238.20%"
              },
              "0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67":{
                  "underlying_token":"eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302",
                  "vault_token":"eip155:1/erc20:0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67",
                  "underlying_value":{
                    "amount":"2627.246068139435250",
                    "usd_value":"3825.0"
                  },
                  "vault_value":{
                    "amount":"2550",
                    "usd_value":"3825.0"
                  },
                  "roi":"9.14%"
              }
            }
        },
        "message":""
      }

   :resjson object result: A mapping of addresses to a mapping of vault names to vault balances
   :resjsonarr string underlying_token: The identifier of the token that is deposited to the vault
   :resjsonarr string vault_token: The identifier of the token that is minted when you deposit underlying token to the vault
   :resjsonarr object underlying_value: The value of the underlying token for the vault.
   :resjsonarr object vault_value: The value of the vault token for the vault.
   :resjsonarr str roi: The Return of Investment for the vault since its creation


   :statuscode 200: Yearn vault V2 balances successfully queried.
   :statuscode 409: User is not logged in. Or yearn module is not activated.
   :statuscode 500: Internal Rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting yearn finance V2 vaults historical data
================================================

.. http:get:: /api/(version)/blockchains/ETH/modules/yearn/vaultsv2/history

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the yearn finance vaults V2 history resource will return all yearn vault related events for addresses that have utilized yearn finance vaults.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/yearn/vaultsv2/history HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool reset_db_data: Boolean denoting whether all yearn event data saved in the DB are going to be deleted and rewritten after this query. False by default.
   :reqjson int from_timestamp: Timestamp from which to query yearn vaults historical data. If not given 0 is implied.
   :reqjson int to_timestamp: Timestamp until which to query yearn vaults historical data. If not given current timestamp is implied.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
            "0x915C4580dFFD112db25a6cf06c76cDd9009637b7":{
              "eip155:1/erc20:0xF29AE508698bDeF169B89834F76704C3B205aedf":{
                  "events":[
                    {
                        "event_type":"deposit",
                        "block_number":12588754,
                        "timestamp":1623087604,
                        "from_asset":"eip155:1/erc20:0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F",
                        "from_value":{
                          "amount":"273.682277822922514201",
                          "usd_value":"273.682277822922514201"
                        },
                        "to_asset":"eip155:1/erc20:0xF29AE508698bDeF169B89834F76704C3B205aedf",
                        "to_value":{
                          "amount":"269.581682615706959373",
                          "usd_value":"269.581682615706959373"
                        },
                        "realized_pnl":null,
                        "tx_hash":"0x01ed01b47b8c7bdab961dd017e8412d1e9d181163e72cbfbce931395004bda4b",
                        "log_index":149
                    }
                  ],
                  "profit_loss":{
                    "amount":"-273.682277822922514201",
                    "usd_value":"-273.682277822922514201"
                  }
              },
              "eip155:1/erc20:0x1C6a9783F812b3Af3aBbf7de64c3cD7CC7D1af44":{
                  "events":[
                    {
                        "event_type":"deposit",
                        "block_number":12462638,
                        "timestamp":1621397797,
                        "from_asset":"eip155:1/erc20:0x94e131324b6054c0D789b190b2dAC504e4361b53",
                        "from_value":{
                          "amount":"32064.715735449204040742",
                          "usd_value":"32064.715735449204040742"
                        },
                        "to_asset":"eip155:1/erc20:0x1C6a9783F812b3Af3aBbf7de64c3cD7CC7D1af44",
                        "to_value":{
                          "amount":"32064.715735449204040742",
                          "usd_value":"32064.715735449204040742"
                        },
                        "realized_pnl":null,
                        "tx_hash":"0x0a53f8817f44ac0f8b516b7fa7ecba2861c001f506dbc465fe289a7110fcc1ca",
                        "log_index":16
                    },
                    {
                        "event_type":"withdraw",
                        "block_number":12494161,
                        "timestamp":1621820621,
                        "from_asset":"eip155:1/erc20:0x1C6a9783F812b3Af3aBbf7de64c3cD7CC7D1af44",
                        "from_value":{
                          "amount":"32064.715735449204040742",
                          "usd_value":"32064.715735449204040742"
                        },
                        "to_asset":"eip155:1/erc20:0x94e131324b6054c0D789b190b2dAC504e4361b53",
                        "to_value":{
                          "amount":"32092.30659836985292638",
                          "usd_value":"32092.30659836985292638"
                        },
                        "realized_pnl":{
                          "amount":"27.590862920648885638",
                          "usd_value":"27.590862920648885638"
                        },
                        "tx_hash":"0xda0694c6b3582fe03b2eb9edb0169d23c8413157e233d0c8f678a7cc9ab4f918",
                        "log_index":134
                    }
                  ],
                  "profit_loss":{
                    "amount":"27.590862920648885638",
                    "usd_value":"27.590862920648885638"
                  }
                }
          }
        },
        "message":""
      }


   :resjson object result: A mapping of addresses to vault history results
   :resjsonarr string event_type: The type of the yearn vault event.
       - ``"deposit"``: when you deposit a token in the vault
       - ``"withdraw"``: when you withdraw a token from the vault
   :resjsonarr int timestamp: The unix timestamp at which the event occurred.
   :resjsonarr int block_number: The block number at which the event occurred.
   :resjsonarr string from_asset: The source asset involved in the event.
       - For ``"deposit"`` events this is the asset being deposited in the vault
       - For ``"withdraw"`` events this is the vault token that is being burned and converted to the original asset.
   :resjsonarr object from_value: The value of the from asset for the event. The rate should be the asset/USD rate at the events's timestamp. But in reality due to current limitations of our implementation is the USD value at the current timestamp. We will address this soon.
   :resjsonarr string to_asset: The target asset involved in the event.
       - For ``"deposit"`` events this is the vault token that is minted to represent the equivalent of the deposited asset.
       - For ``"withdraw"`` events this is the original token that the user withdrew from the vault
   :resjsonarr object to_value: The value of the to asset for the event. The rate should be the asset/USD rate at the events's timestamp. But in reality due to current limitations of our implementation is the USD value at the current timestamp. We will address this soon.
   :resjsonarr object realized_pnl: [Optional]. Realized profit/loss at this event if any. May happen for withdraw events. Same limitation as the usd value in from/to value applies.
   :resjsonarr int tx_hash: The transaction hash of the event.
   :resjsonarr int log_index: The log index of the event.
   :resjson object profit_loss: The total profit/loss for the vault

   :statuscode 200: Yearn vaults V2 history successfully queried.
   :statuscode 409: User is not logged in. Or yearn module is not activated.
   :statuscode 500: Internal Rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting Loopring balances
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/loopring/balances

   Doing a GET on the loopring balances resource will return the balances in loopring L2 that the user has deposited from any of the L1 addresses that are set to track loopring.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/loopring/balances HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "0xE74ad5437C6CFB0cCD6bADda1F6b57b6E542E75e": [{
                    "ETH": {
                        "amount": "1050",
                        "usd_value": "950"
                    },
                    "eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96": {
                        "amount": "1",
                        "usd_value": "5"
                    }
            }]
        },
        "message": ""
      }

   :resjson object result: A mapping between accounts and their balances

   :statuscode 200: Loopring balances successfully queried.
   :statuscode 409: User is not logged in. Or loopring module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as loopring returned an unexpected result.


Getting Eth2 Staking details
==============================

.. http:get:: /api/(version)/blockchains/ETH2/stake/details

   Doing a GET on the ETH2 stake details endpoint will return detailed information about your ETH2 staking activity.

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH2/stake/details HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": [{
              "eth1_depositor": "0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397",
              "index": 9,
              "public_key": "0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b",
              "balance": {"amount": "32.101", "usd_value": "11399"},
              "performance_1d": {"amount": "0.1", "usd_value": "100"},
              "performance_1w": {"amount": "0.7", "usd_value": "700"},
              "performance_1m": {"amount": "3", "usd_value": "3000"},
              "performance_1y": {"amount": "36.5", "usd_value": "36500"},
          }, {
              "eth1_depositor": "0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397",
              "index": 10,
              "public_key": "0xa256e41f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cf14",
              "balance": {"amount": "32.101", "usd_value": "11399"},
              "performance_1d": {"amount": "0.1", "usd_value": "100"},
              "performance_1w": {"amount": "0.7", "usd_value": "700"},
              "performance_1m": {"amount": "3", "usd_value": "3000"},
              "performance_1y": {"amount": "36.5", "usd_value": "36500"},
          }, {
              "eth1_depositor": "0xaee017635291ea8E3C70FeAC5B86e1d3B0e23341",
              "index": 155,
              "public_key": "0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3",
              "balance": {"amount": "32", "usd_value": "19000"},
              "performance_1d": {"amount": "0", "usd_value": "0"},
              "performance_1w": {"amount": "0", "usd_value": "0"},
              "performance_1m": {"amount": "0", "usd_value": "0"},
              "performance_1y": {"amount": "0", "usd_value": "0"},
          }],
        "message": "",
      }

   :resjson result list: The result of the Eth2 staking details for all of the user's accounts. It's a list of details per validator. Important thing to note here is that if all performance entries are 0 then this means that the validator is not active yet and is still waiting in the deposit queue.

   :resjson eth_depositor string: The eth1 address that made the deposit for the validator.
   :resjson index int: The Eth2 validator index.
   :resjson public_key str: The Eth2 validator pulic key.
   :resjson balance object: The balance in ETH of the validator and its usd value
   :resjson performance_1d object: How much has the validator earned in ETH (and USD equivalent value) in the past day.
   :resjson performance_1w object: How much has the validator earned in ETH (and USD equivalent value) in the past week.
   :resjson performance_1m object: How much has the validator earned in ETH (and USD equivalent value) in the past month.
   :resjson performance_1y object: How much has the validator earned in ETH (and USD equivalent value) in the past year.

   :statuscode 200: Eth2 staking details successfully queried
   :statuscode 409: User is not logged in. Or eth2 module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting Eth2 Staking daily stats
=====================================

.. http:post:: /api/(version)/blockchains/ETH2/stake/dailystats

   Doing a POST on the ETH2 stake daily stats endpoint will return daily stats for your ETH2 validators filtered and paginated by the given parameters

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/blockchains/ETH2/stake/dailystats HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "validators": [0, 15, 23542], "only_cache": false}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool only_cache: If true then only the daily stats in the DB are queried.
   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: Optional. This is the list of attributes of the eth2_daily_staking_details table by which to order the results. If none is given 'timestamp' is assumed. Valid values are: ['timestamp', 'validator_index', 'start_usd_price', 'end_usd_price', 'pnl', 'start_amount', 'end_amount', 'missed_attestations', 'orphaned_attestations', 'proposed_blocks', 'missed_blocks', 'orphaned_blocks', 'included_attester_slashings', 'proposer_attester_slashings', 'deposits_number', 'amount_deposited'].
   :reqjson list[bool] ascending: Optional. False by default. Defines the order by which results are returned depending on the chosen order by attribute.
   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson list(string) validators: Optionally filter entries validator indices. If missing data for all validators are returned.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "entries": [{
                  "validator_index": 15,
                  "timestamp": 1613952000,
                  "pnl": {"amount": "0.007", "usd_value": "70"},
                  "start_balance": {"amount": "32.69", "usd_value": "32690"},
                  "end_balance": {"amount": "32.7", "usd_value": "32700"},
                  "missed_attestations": 1,
                  "orphaned_attestations": 0,
                  "proposed_blocks": 1,
                  "missed_blocks": 0,
                  "orphaned_blocks": 0,
                  "included_attester_slashings": 0,
                  "proposer_attester_slashings": 0,
                  "deposits_number": 1,
                  "deposited_balance": {"amount": "32", "usd_value": "32000"}
              }, {
                  "validator_index": 43567,
                  "timestamp": 1613865600,
                  "pnl": {"amount": "-0.0066", "usd_value": "-6.6"},
                  "start_balance": {"amount": "32.69", "usd_value": "32690"},
                  "end_balance": {"amount": "32.7", "usd_value": "32700"},
                  "missed_attestations": 0,
                  "orphaned_attestations": 0,
                  "proposed_blocks": 0,
                  "missed_blocks": 1,
                  "orphaned_blocks": 0,
                  "included_attester_slashings": 0,
                  "proposer_attester_slashings": 0,
                  "deposits_number": 0,
                  "amount_deposited": {"amount": "0", "usd_value": "0"},
              }],
              "entries_found": 95,
              "entries_total": 1000
         },
        "message": "",
      }

   :resjson entries : The list of daily stats filtered by the given filter.

   :resjson eth_depositor string: The eth1 address that made the deposit for the validator.
   :resjson timestamp int: The timestamp of the start of the day in GMT for which this entry is.
   :resjson pnl object: The amount of ETH gained or lost in that day along with its usd value. Average price of the day is taken.
   :resjson start_balance object: The amount of ETH the day started with along with its usd value.
   :resjson end_balance object: The amount of ETH the day ended with along with its usd value.
   :resjson missed_attestations int: The number of attestations the validator missed during the day.
   :resjson orphaned_attestations int: The number of attestations the validator orphaned during the day.
   :resjson proposed_blocks int: The number of blocks the validator proposed during the day.
   :resjson missed_blocks int: The number of blocks the validator missed during the day.
   :resjson orphaned_blocks int: The number of blocks the validator proposed during the day but they got orphaned.
   :resjson included_attester_slashings int: The number of included attester slashins the validator had inside the day.
   :resjson proposer_attester_slashings int: The number of proposer attester slashins the validator had inside the day.
   :resjson deposits_number int: The number of deposits from the eth1 chain the validator had inside the day.
   :resjson deposited_balance object: The amount deposited from the eth1 chain for the validator inside the day along with its usd value.
   :resjson string sum_pnl: The sum of PnL in ETH for the current filter. Ignores pagination.
   :resjson string sum_usd_value: The sum of usd value of ETH PnL for the current filter. Ignores pagination.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_total: The number of total entries ignoring all filters.

   :statuscode 200: Eth2 staking details successfully queried
   :statuscode 409: User is not logged in. Or eth2 module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting Eth2 Staking deposits
==============================

.. http:get:: /api/(version)/blockchains/ETH2/stake/deposits

   Doing a GET on the ETH2 stake deposits endpoint will return detailed information about your ETH2 staking activity.

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH2/stake/deposits HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": [{
              "from_address": "0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397",
              "pubkey": "0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b",
              "withdrawal_credentials": "0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499",
              "value": {
                  "amount": "32", "usd_value": "11360"
              },
              "deposit_index": 9,
              "tx_hash": "0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1",
              "log_index": 22
              }, {
              "from_address": "0x00F8a0D8EE1c21151BCcB416bCa1C152f9952D19",
              "pubkey": "0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3",
              "withdrawal_credentials": "0x00cfe1c10347d642a8b8daf86d23bcb368076972691445de2cf517ff43765817",
              "value": {
                  "amount": "32", "usd_value": "11860"
              },
              "deposit_index": 1650,
              "tx_hash": "0x6905f4d1843fb8c003c1fbbc2c8e6c5f9792f4f44ddb1122553412ee0b128da7",
              "log_index": 221
          }],
        "message": "",
      }

   :resjson result list: The Eth2 staking deposits for all of the user's accounts. Contains a list of the deposits.

   :resjson from_address string: The Eth1 address that made the Eth2 deposit.
   :resjson pubkey string: The Eth2 public key for which the deposit was made
   :resjson withdrawal_credentials string: The Eth2 withdrawal credentials with which the deposit was made
   :resjson deposit_index int: The index slot for which the deposit was made. NOT the same as the validator index.
   :resjson tx_hash str: The Eth1 transaction hash in which the deposit was made.
   :resjson log_index int: The log index of the deposit

   :statuscode 200: Eth2 staking deposits successfully queried
   :statuscode 409: User is not logged in. Or eth2 module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Adding an Eth2 validator
==========================

.. http:put:: /api/(version)/blockchains/ETH2/validators

   Doing a PUT on the eth2 validators endpoint will input information and track an ETH2 validator.


   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/ETH2/validators HTTP/1.1
      Host: localhost:5042

   :reqjson validator_index int: An optional integer representing the validator index of the validator to track. If this is not given then the pulic key of the validator has to be given!
   :reqjson public_key str: An optional string representing the hexadecimal string of the public key of the validator to track. If this is not given the the validator index has to be given!
   :resjson ownership_percentage: An optional string representing the amount of the validator owned by the user in the range of 0 to 100. If not provided a default value of 100 is assigned.
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true
        "message": "",
      }

   :statuscode 200: Eth2 validator successfully added.
   :statuscode 401: Can't add the validator since user is not premium and would go over the limit.
   :statuscode 409: User is not logged in. Or eth2 module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as beaconcha.in could not be reached or returned unexpected response.


Deleting Eth2 validators
===========================

.. http:delete:: /api/(version)/blockchains/ETH2/validators

   Doing a DELETE on the eth2 validators endpoint will delete information and stop tracking an ETH2 validator.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/ETH2/validators HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
        "validators": [
          {
            "validator_index": 1,
            "public_key": "abcd"
          }
        ]
      }

   :reqjson list[object] validators: A list of eth2 validators to delete.
   :reqjsonarr int[optional] validator_index: An optional integer representing the validator index of the validator to track. If this is not given then the pulic key of the validator has to be given!
   :reqjsonarr string[optional] public_key: An optional string representing the hexadecimal string of the public key of the validator to track. If this is not given the the validator index has to be given!

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

   :statuscode 200: Eth2 validator successfully delete.
   :statuscode 409: User is not logged in. Or eth2 module is not activated.
   :statuscode 500: Internal rotki error.


Editing an Eth2 validator
==========================

.. http:patch:: /api/(version)/blockchains/ETH2/validators

   Doing a PATCH on the eth2 validators endpoint will allow to edit the ownership percentage of a validator indentified by its index.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/ETH2/validators HTTP/1.1
      Host: localhost:5042

   :reqjson validator_index int: An integer representing the validator index of the validator to edit.
   :resjson ownership_percentage: A float representing the amount of the validator owned by the user in the range of 0 to 100. If not provided a default value of 100 is assigned.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true
        "message": "",
      }

   :statuscode 200: Eth2 validator successfully edited.
   :statuscode 409: User is not logged in, eth2 module is not activated or validator doesn't exist.
   :statuscode 500: Internal rotki error.


Getting tracked Eth2 validators
===============================

.. http:get:: /api/(version)/blockchains/ETH2/validators

   Doing a GET on the ETH2 validators endpoint will get information on the tracked ETH2 validators. If the user is not premium they will see up to a certain limit of validators.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH2/validators HTTP/1.1
      Host: localhost:5042


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
          "entries":[
            {
              "index":1,
              "public_key":"0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c",
              "ownership_percentage": "100"
            },
            {
              "index":1532,
              "public_key":"0xa509dec619e5b3484bf4bc1c33baa4c2cdd5ac791876f4add6117f7eded966198ab77862ec2913bb226bdf855cc6d6ed",
              "ownership_percentage": "50"
            },
            {
              "index":5421,
              "public_key":"0xa64722f93f37c7da8da67ee36fd2a763103897efc274e3accb4cd172382f7a170f064b81552ae77cdbe440208a1b897e",
              "ownership_percentage": "25.75"
            }
          ],
          "entries_found":3,
          "entries_limit":4
        },
        "message":""
      }

   :resjson object entries: The resulting entries list
   :resjson integer index: The index of the validator
   :resjson string public_key: The public key of the validator
   :resjson string ownership_percentage: The ownership percentage of the validator

   :statuscode 200: Eth2 validator defaults successfully returned.
   :statuscode 409: User is not logged in. Or eth2 module is not activated.
   :statuscode 500: Internal rotki error.


Getting Pickle's DILL balances
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/pickle/dill

   Doing a GET on the pickle's DILL balances resource will return the balances that the user has locked with the rewards that can be claimed.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/pickle/dill HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

        {
            "result": {
                "0x5c4D8CEE7dE74E31cE69E76276d862180545c307": {
                    "locked_amount": {
                        "amount": "4431.204412216798860222",
                        "usd_value": "43735.98754857980475039114",
                        "asset": "eip155:1/erc20:0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5"
                    },
                    "pending_rewards": {
                        "amount": "82.217560698031032969",
                        "usd_value": "811.48732408956629540403",
                        "asset": "eip155:1/erc20:0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5"
                    },
                    "locked_until": 1755129600
                }
            },
            "message": ""
        }

   :resjson object result: A mapping of all accounts that currently have Pickle locked to keys ``locked_amount``,  ``pending_rewards`` and ``locked_until``

   :statuscode 200: Pickle balances successfully queried.
   :statuscode 409: User is not logged in or Pickle module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Querying ethereum airdrops
==============================

.. http:get:: /api/(version)/blockchains/ETH/airdrops

   Doing a GET on the ethereum airdrops endpoint will return how much and of which token any of the tracked ethereum addresses are entitled to.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/airdrops HTTP/1.1
      Host: localhost:5042


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0xe5B3330A43CeC5A01A80E75ebaB2d3bc17e70819": {
                  "1inch": {
                      "amount": "675.55",
                      "asset": "eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302",
                      "link": "https://app.uniswap.org/"
                  }
              },
              "0x0B89f648eEcCc574a9B7449B5242103789CCD9D7": {
                  "1inch": {
                      "amount": "1823.23",
                      "asset": "eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302",
                      "link": "https://1inch.exchange/"
                  },
                  "uniswap": {
                      "amount": "400",
                      "asset": "eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
                      "link": "https://app.uniswap.org/"
                  }
              },
          "message": ""
      }

   :reqjson object result: A mapping of addresses to protocols for which claimable airdrops exist

   :statuscode 200: Tags successfully queried.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not query an airdrop file
   :statuscode 507: Failed to store CSV files for airdrops.

Get addresses to query per protocol
=======================================

.. http:get:: /api/(version)/queried_addresses/

   Doing a GET on this endpoint will return a mapping of which addresses are set for querying for each protocol. If a protocol is not returned or has no addresses then
   all addresses are queried

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/queried_addresses HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "aave": ["0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B", "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"],
              "makerdao_dsr": ["0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"],
          },
          "message": ""
      }

   :resjson list result: A mapping of modules/protocols for which an entry exists to the list of addresses to query.
   :statuscode 200: The addresses have been queried successfully
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error


Add address to query per protocol
==================================

.. http:put:: /api/(version)/queried_addresses/

   Doing a PUT on this endpoint will add a new address for querying by a protocol/module. Returns all the queried addresses per module after the addition.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/queried_addresses HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "module": "aave",
          "address": "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"
      }

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "aave": ["0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B", "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"],
              "makerdao_dsr": ["0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"],
          },
          "message": ""
      }

   :resjson list result: A mapping of modules/protocols for which an entry exists to the list of addresses to query.
   :statuscode 200: The address has been added successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The address already exists in the addresses to query for that protocol.
   :statuscode 500: Internal rotki error

Remove an address to query per protocol
=========================================

.. http:delete:: /api/(version)/queried_addresses/

   Doing a DELETE on this endpoint will remove an address for querying by a protocol/module. Returns all the queried addresses per module after the deletion.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/queried_addresses HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "module": "aave",
          "address": "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"
      }

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "aave": ["0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B"],
              "makerdao_dsr": ["0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"],
          },
          "message": ""
      }

   :resjson list result: A mapping of modules/protocols for which an entry exists to the list of addresses to query.
   :statuscode 200: The address has been removed successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The address is not in the addresses to query for that protocol.
   :statuscode 500: Internal rotki error

Adding blockchain accounts
===========================

.. http:put:: /api/(version)/blockchains/(name)/

   .. note::
      Supported blockchains: ``"BTC", "BCH", "ETH", "KSM", "DOT", "AVAX"``

      Supported blockchains with ENS domains: ``"BTC", "BCH", "ETH", "KSM", "DOT"``

      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the blockchains endpoint with a specific blockchain URL and a list of account data in the json data will add these accounts to the tracked accounts for the given blockchain and the current user. A list of accounts' addresses that were added during a request is returned. This data is returned so that if you add an ens name, you get its name's resolved address for the further usage.
   If one of the given accounts to add is invalid the entire request will fail.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/ETH/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "accounts": [{
                  "address": "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B",
                  "label": "my new metamask",
                  "tags": ["public", "metamask"]
              }, {
                  "address": "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"
              }]
      }

   :reqjson list[object] accounts: A list of account data to add for the given blockchain
   :reqjsonarr string address: The address of the account to add. Can either be a hexadecimal address or an ENS name.
   :reqjsonarr string[optional] label: An optional label to describe the new account. Cannot be empty string.
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the new account
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": [
            "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B",
            "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b"
        ],
        "message": ""
      }

   :resjson list result: A list containing accounts' addresses that were added during a request.
   :statuscode 200: Accounts successfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Remote error occured when attempted to connect to an Avalanche or Polkadot node and only if it's the first account added. Check message for details.

Adding BTC/BCH xpubs
========================

.. http:put:: /api/(version)/blockchains/(blockchain)/xpub

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      Only ``"BCH"`` and ``"BTC"`` are the supported blockchain values for Xpubs.

   Doing a PUT on the xpubs endpoint will add an extended public key for bitcoin/bitcoin cash mainnet.
   All derived addresses that have ever had a transaction from this xpub and derivation path will be found and added for tracking in rotki.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/BTC/xpub HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
          "xpub_type": "p2sh_p2wpkh",
          "derivation_path": "m/0/0",
          "label": "my electrum xpub",
          "tags": ["public", "old"]
      }

   :reqjson string xpub: The extended public key to add
   :reqjsonarr string derivation_path: The derivation path from which to start deriving addresses relative to the xpub.
   :reqjsonarr string[optional] xpub_type: An optional type to denote the type of the given xpub. If omitted the prefix xpub/ypub/zpub is used to determine the type. The valid xpub types are: ``"p2pkh"``, ``"p2sh_p2wpkh"``, ``"wpkh"`` and ``"p2tr"``.
   :reqjsonarr string[optional] label: An optional label to describe the new extended public key
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the xpub
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "per_account": {
                  "BTC": {
                      "standalone": {
                          "3Kb9QPcTUJKspzjQFBppfXRcWew6hyDAPb": {
                              "amount": "0.5", "usd_value": "3770.075"
                          }, "33hjmoU9XjEz8aLxf44FNGB8TdrLkAVBBo": {
                              "amount": "0.5", "usd_value": "3770.075"
                      }},
                      "xpubs": [{
                              "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
                              "derivation_path": "m/0/0",
                              "addresses": {
                                  "1LZypJUwJJRdfdndwvDmtAjrVYaHko136r": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "1AMrsvqsJzDq25QnaJzX5BzEvdqQ8T6MkT": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}, {
                              "xpub": "zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q",
                              "derivation_path": "m",
                              "addresses": {
                                  "bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}]
                   },
                   "ETH": { "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B": {
                       "assets": {
                           "ETH": {"amount": "10", "usd_value": "1755.53"},
                           "GNO": {"amount": "1", "usd_value": "50"},
                           "RDN": {"amount": "1", "usd_value": "1.5"}
                       },
                      "liabilities": {}
                  }}
              },
              "totals": {
                  "assets": {
                      "BTC": {"amount": "1", "usd_value": "7540.15"},
                      "ETH": {"amount": "10", "usd_value": "1650.53"},
                      "RDN": {"amount": "1", "usd_value": "1.5"},
                      "GNO": {"amount": "1", "usd_value": "50"}
                  },
                  "liabilities": {
                      "DAI": {"amount": "10", "usd_value": "10.2"}
                  }
          },
          "message": ""
      }

   :resjson object result: An object containing the ``"per_account"`` and ``"totals"`` keys as also defined `here <blockchain_balances_result_>`_.
   :statuscode 200: Xpub successfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occurred when re-querying the balances after addition. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as blockstream or haskoin. Check message for details.

Editing BTC/BCH xpubs
========================

.. http:patch:: /api/(version)/blockchains/(blockchain)/xpub

   .. note::
      Only ``"BCH"`` and ``"BTC"`` are the supported blockchain values for Xpubs.

   Doing a PATCH on the xpubs endpoint will edit the label and tag of an extended public key for bitcoin/bitcoin cash mainnet.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/blockchains/BTC/xpub HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
          "derivation_path": "m/0/0",
          "label": "my electrum xpub",
          "tags": ["public", "old"]
      }

   :reqjson string xpub: The extended public key to edit
   :reqjsonarr string derivation_path: The derivation path from which to start deriving addresses relative to the xpub.
   :reqjsonarr string[optional] label: An optional label to describe the new extended public key
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the xpub

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "per_account": {
                  "BTC": {
                      "standalone": {
                          "3Kb9QPcTUJKspzjQFBppfXRcWew6hyDAPb": {
                              "amount": "0.5", "usd_value": "3770.075"
                          }, "33hjmoU9XjEz8aLxf44FNGB8TdrLkAVBBo": {
                              "amount": "0.5", "usd_value": "3770.075"
                      }},
                      "xpubs": [{
                              "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
                              "derivation_path": "m/0/0",
                              "addresses": {
                                  "1LZypJUwJJRdfdndwvDmtAjrVYaHko136r": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "1AMrsvqsJzDq25QnaJzX5BzEvdqQ8T6MkT": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}, {
                              "xpub": "zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q",
                              "derivation_path": "m",
                              "addresses": {
                                  "bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}]
                   },
                   "ETH": { "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B": {
                       "assets": {
                           "ETH": {"amount": "10", "usd_value": "1755.53"},
                           "GNO": {"amount": "1", "usd_value": "50"},
                           "RDN": {"amount": "1", "usd_value": "1.5"}
                       },
                       "total_usd_value": "1807.03",
                  }}
              },
              "totals": {
                  "BTC": {"amount": "1", "usd_value": "7540.15"},
                  "ETH": {"amount": "10", "usd_value": "1650.53"},
                  "RDN": {"amount": "1", "usd_value": "1.5"},
                  "GNO": {"amount": "1", "usd_value": "50"}
          },
          "message": ""
      }

   :resjson object result: An object containing the ``"per_account"`` and ``"totals"`` keys as also defined `here <blockchain_balances_result_>`_.
   :statuscode 200: Xpub successfully edited
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occurred when re-querying the balances after addition. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error

Deleting BTC/BCH xpubs
========================

.. http:delete:: /api/(version)/blockchains/(blockchain)/xpub

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      Only ``"BCH"`` and ``"BTC"`` are the supported blockchain values for Xpubs.

   Doing a DELETE on the xpubs endpoint will remove an extended public key for bitcoin/bitcoin cash mainnet. All derived addresses from the xpub will also be deleted.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/BTC/xpub HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
          "derivation_path": "m/0/0"
      }

   :reqjson string xpub: The extended public key to remove
   :reqjsonarr string derivation_path: The derivation path from which addresses were derived.
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "per_account": {
                  "BTC": {
                      "standalone": {
                          "3Kb9QPcTUJKspzjQFBppfXRcWew6hyDAPb": {
                              "amount": "0.5", "usd_value": "3770.075"
                          }, "33hjmoU9XjEz8aLxf44FNGB8TdrLkAVBBo": {
                              "amount": "0.5", "usd_value": "3770.075"
                      }},
                      "xpubs": [{
                              "xpub": "zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q",
                              "derivation_path": "m",
                              "addresses": {
                                  "bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}]
                   },
                   "ETH": { "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B": {
                       "assets": {
                           "ETH": {"amount": "10", "usd_value": "1755.53"},
                           "GNO": {"amount": "1", "usd_value": "50"},
                           "RDN": {"amount": "1", "usd_value": "1.5"}
                       },
                       "liabilities": {}
                  }}
              },
              "totals": {
                  "assets": {
                      "BTC": {"amount": "1", "usd_value": "7540.15"},
                      "ETH": {"amount": "10", "usd_value": "1650.53"},
                      "RDN": {"amount": "1", "usd_value": "1.5"},
                      "GNO": {"amount": "1", "usd_value": "50"}
                  },
                  "liabilities": {}
          },
          "message": ""
      }

   :resjson object result: An object containing the ``"per_account"`` and ``"totals"`` keys as also defined `here <blockchain_balances_result_>`_.
   :statuscode 200: Xpub successfully removed
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occurred when re-querying the balances after addition. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as blockstream/haskoin. Check message for details.


Editing blockchain account data
=================================

.. http:patch:: /api/(version)/blockchains/(name)/

   .. note::
      Supported blockchains: ``"BTC", "BCH", "ETH", "KSM", "DOT", "AVAX"``

      Supported blockchains with ENS domains: ``"BTC", "BCH", "ETH", "KSM", "DOT"``

   Doing a PATCH on the the blockchains endpoint with a specific blockchain URL and a list of accounts to edit will edit the label and tags for those accounts.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/blockchains/ETH/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "accounts": [
              {
                  "address": "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B",
                  "label": "my new metamask",
                  "tags": [
                      "public",
                      "metamask"
                  ]
              },
              {
                  "address": "johndoe.eth",
                  "label": "my hardware wallet"
              }
          ]
      }


   :reqjson list[object] accounts: A list of account data to edit for the given blockchain
   :reqjsonarr string address: The address of the account to edit. Can either be a hexadecimal address or an ENS name.
   :reqjsonarr string[optional] label: An optional label to edit for the account. Cannot be empty string.
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the account

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result" : [{
              "address": "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B",
              "label": "my new metamask",
              "tags": ["public", "metamask"]
           }, {
              "address": "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b",
              "label": "my hardware wallet",
              "tags": null
           }],
           "message": "",
      }

   :resjson list result: A list containing the blockchain account data as also defined `here <blockchain_accounts_result_>`_. Result is different depending on the blockchain type.

   :statuscode 200: Accounts successfully edited
   :statuscode 400: Provided JSON or data is in some way malformed. Given list to edit is empty.
   :statuscode 409: User is not logged in. An account given to edit does not exist or a given tag does not exist.
   :statuscode 500: Internal rotki error

Removing blockchain accounts
==============================

.. http:delete:: /api/(version)/blockchains/(name)/

   .. note::
      Supported blockchains: ``"BTC", "BCH", "ETH", "KSM", "DOT", "AVAX"``

      Supported blockchains with ENS domains: ``"BTC", "BCH", "ETH", "KSM", "DOT"``

      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a DELETE on the the blockchains endpoint with a specific blockchain URL and a list of accounts in the json data will remove these accounts from the tracked accounts for the given blockchain and the current user. The updated balances after the account deletions are returned.
    If one of the given accounts to add is invalid the entire request will fail.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/ETH HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"accounts": ["0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B"]}

   :reqjson list[string] accounts: A list of accounts to delete for the given blockchain. Each account Can either be a hexadecimal address or an ENS name.
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "per_account": {
                  "BTC": {
                      "standalone": {
                          "3Kb9QPcTUJKspzjQFBppfXRcWew6hyDAPb": {
                              "amount": "0.5", "usd_value": "3770.075"
                          }, "33hjmoU9XjEz8aLxf44FNGB8TdrLkAVBBo": {
                              "amount": "0.5", "usd_value": "3770.075"
                      }},
                      "xpubs": [{
                              "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
                              "derivation_path": "m/0/0",
                              "addresses": {
                                  "1LZypJUwJJRdfdndwvDmtAjrVYaHko136r": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "1AMrsvqsJzDq25QnaJzX5BzEvdqQ8T6MkT": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}, {
                              "xpub": "zpub6quTRdxqWmerHdiWVKZdLMp9FY641F1F171gfT2RS4D1FyHnutwFSMiab58Nbsdu4fXBaFwpy5xyGnKZ8d6xn2j4r4yNmQ3Yp3yDDxQUo3q",
                              "derivation_path": "m",
                              "addresses": {
                                  "bc1qc3qcxs025ka9l6qn0q5cyvmnpwrqw2z49qwrx5": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  },
                                  "bc1qr4r8vryfzexvhjrx5fh5uj0s2ead8awpqspqra": {
                                      "amount": "0.5", "usd_value": "3770.075"
                                  }
                          }}]
              }},
              "totals": {
                  "assets": {"BTC": {"amount": "1", "usd_value": "7540.15"}},
                  "liabilities": {}
              }
          },
          "message": ""
      }

   :resjson object result: An object containing the ``"per_account"`` and ``"totals"`` keys as also defined `here <blockchain_balances_result_>`_.
   :statuscode 200: Accounts successfully deleted
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to remove contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occurred when re-querying the balances after addition. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as Etherscan. Check message for details.

Getting manually tracked balances
====================================
.. http:get:: /api/(version)/balances/manual/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a GET on the manually tracked balances endpoint will return all the manually tracked balance accounts from the database.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/balances/manual HTTP/1.1
      Host: localhost:5042


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
          "balances": [{
                  "id": 1,
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "50.315",
                  "usd_value": "2370.13839",
                  "tags": ["public"],
                  "location": "blockchain"
              }, {
                  "id": 2,
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }, {
                  "id": 3,
                  "asset": "ZEC",
                  "label" "My favorite wallet",
                  "amount": "76.2"
                  "usd_value": "6067.77",
                  "tags": ["private", "inheritance"],
                  "location": "blockchain"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances successfully queried
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

Adding manually tracked balances
====================================

.. http:put:: /api/(version)/balances/manual/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the the manually tracked balances endpoint you can add a balance for an asset that rotki can't automatically detect, along with a label identifying it for you and any number of tags.

   .. _manually_tracked_balances_section:


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/balances/manual/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "balances": [{
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "50.315",
                  "tags": ["public"],
                  "location": "blockchain"
              }, {
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "location": "blockchain"
              }]
      }

   :reqjson list[object] balances: A list of manually tracked balances to add to rotki
   :reqjsonarr string asset: The asset that is being tracked
   :reqjsonarr string label: A label to describe where is this balance stored. Must be unique between all manually tracked balance labels.
   :reqjsonarr string amount: The amount of asset that is stored.
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the this manually tracked balance.
   :reqjsonarr string location: The location where the balance is saved. Can be one of: ["external", "kraken", "poloniex", "bittrex", "binance", "bitmex", "coinbase", "banks", "blockchain", "coinbasepro", "gemini", "ftx", "ftxus", "independentreserve"]

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
          "balances": [{
                  "id": 1,
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "50.315",
                  "usd_value": "2370.13839",
                  "tags": ["public"],
                  "location": "blockchain"
              }, {
                  "id" :2,
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }, {
                  "id": 3
                  "asset": "ZEC",
                  "label" "My favorite wallet",
                  "amount": "76.2"
                  "usd_value": "6067.77",
                  "tags": ["private", "inheritance"]
                  "location": "blockchain"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances successfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The balances to add contained invalid assets or were an empty list. One of the balance labels already exist.
   :statuscode 409: User is not logged in. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as Cryptocompare. Check message for details.

Editing manually tracked balances
====================================

.. http:patch:: /api/(version)/balances/manual

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PATCH on the the manual balances endpoint allows you to edit a number of manually tracked balances by id.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/balances/manual/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "balances": [{
                  "id": 1,
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "4.5",
                  "location": "blockchain"
                  },{
                  "id": 3,
                  "asset": "ETH"    ,
                  "label": "My favorite wallet",
                  "amount": "10",
                  "tags": [],
                  "location": "kraken"
              }]
      }

   :reqjson list[object] accounts: A list of manual balances to edit. As defined `here <manually_tracked_balances_section_>`__.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
          "balances": [{
                  "id" 1,
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "4.5",
                  "usd_value": "210.548",
                  "tags": ["public"],
                  "location": "blockchain"
              }, {
                  "id": 2,
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }, {
                  "id": 3,
                  "asset": "ZEC",
                  "label" "My favorite wallet",
                  "amount": "10"
                  "usd_value": "1330.85"
                  "location": "kraken"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances successfully edited
   :statuscode 400: Provided JSON or data is in some way malformed. The balances to add contained invalid assets or were an empty list.
   :statuscode 409: User is not logged in. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as Cryptocompare. Check message for details.

Deleting manually tracked balances
======================================

.. http:delete:: /api/(version)/balances/manual/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a DELETE on the the manual balances endpoint with a list of ids of manually tracked balances will remove these balances from the database for the current user.
    If one of the given ids to remove is invalid the entire request will fail.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/balances/manual HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"ids": [1, 3]}

   :reqjson list[string] balances: A list of labels of manually tracked balances to delete

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
          "balances": [{
                  "id": 2,
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances successfully delete
   :statuscode 400: Provided JSON or data is in some way malformed. One of the labels to remove did not exist.
   :statuscode 409: User is not logged in. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as Cryptocompare. Check message for details.

Getting watchers
=====================================
.. http:get:: /api/(version)/watchers

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the watchers endpoint, will return the currently installed watchers from the rotki server.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/watchers HTTP/1.1
      Host: localhost:5042

   .. _watchers_schema_section:

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
            "identifier": "6h3m7vRrLLOipwNmzhAVdo6FaGlr0XKGYLyjHqWa2KQ=",
            "type": "makervault_collateralization_ratio",
            "args": {"ratio": "200.5", "op": "gt", "vault_id": "24"}
            }, {
             "identifier": "7a4m7vRrLLOipwNmzhAVdo6FaGgr0XKGYLyjHqWa2KQ=",
             "type": "makervault_collateralization_ratio",
             "args": {"ratio": "185.55", "op": "lt","vault_id": "456"}
            }],
          "message": ""
      }

   :resjson object result: An list containing all the watcher results.
   :reqjsonarr string identifier: The identifier with which to identify this vault. It's unique per user and vault args + watcher combination. The client needs to keep this identifier. If the entry is edited, the identifier changes.
   :reqjsonarr string type: The type of the watcher. Valid types are: "makervault_collateralization_ratio".
   :reqjsonarr object args: An object containing the args for the vault. Depending on the vault type different args are possible. Check `here <watcher_types_section_>`__ to see the different options.
   :statuscode 200: Watchers successfully queried
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not connect to or got unexpected response format from rotki server


   .. _watcher_types_section:

   For makervault ratio the possible arguments are:
    - vault_id: The id of the vault to watcher
    - ratio: The target ratio to watch for
    - op: The comparison operator:
        * lt: less than the given ratio
        * le: less than or equal to the given ratio
        * gt: greater than the the given ratio
        * ge: greater than or equal to the given ratio

Adding new watcher
====================

.. http:put:: /api/(version)/watchers/

   .. note::
      This endpoint is only available for premium users

   Doing a PUT on the the watchers endpoint you can install new watchers for watching to the server.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/watchers/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "watchers": [{
            "type": "makervault_collateralization_ratio",
            "args": {"ratio": "200.5", "op": "gt", "vault_id": "24"}
            }, {
             "type": "makervault_collateralization_ratio",
             "args": {"ratio": "185.55", "op": "lt","vault_id": "456"}
            }]
      }

   :reqjson list[object] watchers: A list of watchers to add as defined in the `above section <watchers_schema_section>`__ but without an identifier. The identifier is created server-side and returned in the response.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
            "identifier": "6h3m7vRrLLOipwNmzhAVdo6FaGlr0XKGYLyjHqWa2KQ=",
            "type": "makervault_collateralization_ratio",
            "args": {"ratio": "200.5", "op": "gt", "vault_id": "24"}
            }, {
             "identifier": "7a4m7vRrLLOipwNmzhAVdo6FaGgr0XKGYLyjHqWa2KQ=",
             "type": "makervault_collateralization_ratio",
             "args": {"ratio": "185.55", "op": "lt","vault_id": "456"}
            }],
          "message": ""
      }

   :resjson object result: An object containing all the watchers, including the ones that were added. The watchers follow the schema defined `above <watchers_schema_section_>`__.
   :statuscode 200: Watchers successfully added
   :statuscode 400: Provided JSON or data is in some way malformed. Or the same watcher already exists for this user in the DB.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not connect to or got unexpected response format from rotki server

Editing watchers
==================

.. http:patch:: /api/(version)/watchers

   .. note::
      This endpoint is only available for premium users

   Doing a PATCH on the the watchers endpoint allows you to edit a number of watchers by identifier. If one of the identifier is not found, the whole method fails.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/watchers/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "watchers": [{
            "identifier": "6h3m7vRrLLOipwNmzhAVdo6FaGlr0XKGYLyjHqWa2KQ=",
            "type": "makervault_collateralization_ratio",
            "args": {"ratio": "200.5", "op": "gt", "vault_id": "24"}
            }, {
             "identifier": "7a4m7vRrLLOipwNmzhAVdo6FaGgr0XKGYLyjHqWa2KQ=",
             "type": "makervault_collateralization_ratio",
             "args": {"ratio": "185.55", "op": "lt","vault_id": "456"}
            }]
      }

   :reqjson list[object] watchers: A list of watcher to edit. As defined `here <watchers_schema_section>`__.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
            "identifier": "6h3m7vRrLLOipwNmzhAVdo6FaGlr0XKGYLyjHqWa2KQ=",
            "type": "makervault_collateralization_ratio",
            "args": {"ratio": "200.5", "op": "gt", "vault_id": "24"}
            }, {
             "identifier": "7a4m7vRrLLOipwNmzhAVdo6FaGgr0XKGYLyjHqWa2KQ=",
             "type": "makervault_collateralization_ratio",
             "args": {"ratio": "185.55", "op": "lt","vault_id": "456"}
            }],
          "message": ""
      }

   :resjson object result: An object containing all the watchers as defined `here <watchers_schema_section_>`__
   :statuscode 200: Watchers successfully edited
   :statuscode 400: Provided JSON or data is in some way malformed. Or a given identifier does not exist in the DB.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not connect to or got unexpected response format from rotki server

Deleting watchers
==================

.. http:delete:: /api/(version)/watchers/

   .. note::
      This endpoint is only available for premium users

   Doing a DELETE on the the watchers endpoint with a list of identifiers will delete either all or none of them.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/watchers HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"watchers": ["6h3m7vRrLLOipwNmzhAVdo6FaGlr0XKGYLyjHqWa2KQ", "92Jm7vRrLLOipwNXzhAVdo6XaGAr0XKGYLyjHqWa2KA"]}


   :reqjson list[string] watchers: A list of identifier of watchers to delete

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
            "identifier": "6h3m7vRrLLOipwNmzhAVdo6FaGlr0XKGYLyjHqWa2KQ=",
            "type": "makervault_collateralization_ratio",
            "args": {"ratio": "200.5", "op": "gt", "vault_id": "24"}
           }],
          "message": ""
      }

   :resjson object result: An object containing all the watchers after deletion. The watchers follow the schema defined `above <watchers_schema_section_>`__.
   :statuscode 200: Watchers successfully delete
   :statuscode 400: Provided JSON or data is in some way malformed. One of the identifiers  to remove did not exist.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not connect to or got unexpected response format from rotki server

Dealing with ignored assets
===========================

.. http:get:: /api/(version)/assets/ignored/

   Doing a GET on the ignored assets endpoint will return a list of all assets that the user has set to have ignored.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/ignored HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["eip155:1/erc20:0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7", "eip155:1/erc20:0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets successfully queried
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/assets/ignored/

   Doing a PUT on the ignored assets endpoint will add new assets to the ignored assets list. Returns the new list with the added assets in the response.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/ignored HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"assets": ["eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96"]}

   :reqjson list assets: A list of asset symbols to add to the ignored assets.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["eip155:1/erc20:0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7", "eip155:1/erc20:0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413", "eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets successfully added
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. One of the assets provided is already on the list.
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/assets/ignored/

   Doing a DELETE on the ignored assets endpoint will remove the given assets from the ignored assets list. Returns the new list without the removed assets in the response.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/ignored HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"assets": ["eip155:1/erc20:0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413"]}

   :reqjson list assets: A list of asset symbols to remove from the ignored assets.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["eip155:1/erc20:0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets successfully removed
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. One of the assets provided is not on the list.
   :statuscode 500: Internal rotki error

.. http:post:: /api/(version)/assets/ignored/

   Doing a POST on the ignored assets endpoint will update the list of ignored assets using cryptoscamdb as source.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   :resjson int result: The number of assets that were added to the ignore list.
   :statuscode 200: Ignored assets successfully updated
   :statuscode 500: Internal rotki error
   :statuscode 502: Remote error downloading list of assets from cryptoscamdb

Dealing with ignored actions
==============================

.. http:get:: /api/(version)/actions/ignored

   Doing a GET on the ignored actions endpoint will return a mapping of lists of all action identifiers that the user has set to have ignored during accounting. User can also specify a specific action type to get only that type's mapping.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/actions/ignored HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"action_type": "trade"}

   :reqjson str action_type: A type of actions whose ignored ids to return. If it is not specified a mapping of all action types is returned. Valid action types are: ``trade``, ``asset movement``, ``ethereum_transaction`` and ``ledger action``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "trade": ["X124-JYI", "2325"],
              "ethereum_transaction": ["0xfoo", "0xboo"]
          },
          "message": ""
      }

   :resjson list result: A mapping to a list of action identifiers that will be ignored during accounting for each type of action.
   :statuscode 200: Actions successfully queried
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/actions/ignored

   Doing a PUT on the ignored actions endpoint will add action identifiers for ignoring of a given action type during accounting. Returns the list of all ignored action identifiers of the given type after the addition.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/actions/ignored HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"action_type": "ledger action", "action_ids": ["Z231-XH23K"]}

   :reqjson str action_type: A type of actions whose ignored ids to add. Defined above.
   :reqjson list action_ids: A list of action identifiers to add to the ignored actions for accounting

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"ledger_action": ["Z231-XH23K", "X124-JYI", "2325"]},
          "message": ""
      }

   :resjson list result: A mapping to a list of action identifiers that are ignored during accounting for the given action type.
   :statuscode 200: Action ids successfully added
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. One of the action ids provided is already on the list.
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/actions/ignored/

   Doing a DELETE on the ignored actions endpoint removes action ids from the list of actions of the given type to be ignored during accounting.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/actions/ignored HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"action_type": "asset movement", "action_ids": ["2325"]}

   :reqjson str action_type: A type of actions whose ignored ids to remove. Defined above.
   :reqjson list action_ids: A list of action identifiers to remove from the ignored action ids list for the action type.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"asset movement": ["Z231-XH23K", "X124-JYI"]},
          "message": ""
      }

   :resjson list result: A list of action identifiers that are currently ignored during accounting.
   :statuscode 200: Action ids successfully removed
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. One of the action ids provided is not on the list.
   :statuscode 500: Internal rotki error


Querying general information
==============================

.. http:get:: /api/(version)/info

   Doing a GET on the info endpoint will return general information about rotki. Under the version key we get info on the current version of rotki. When ``check_for_updates`` is ``true`` if there is a newer version then ``"download_url"`` will be populated. If not then only ``"our_version"`` and ``"latest_version"`` will be. There is a possibility that latest version may not be populated due to github not being reachable. Also we return the data directory

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/info HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"check_for_updates": true}

   :reqjson bool check_for_updates: If true will perform an external query to check the latest version available and get the download link.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "version": {
                  "our_version": "1.0.3",
                  "latest_version": "1.0.4",
                  "download_url": "https://github.com/rotki/rotki/releases/tag/v1.0.4"
              },
              "data_directory": "/home/username/.local/share/rotki/data"
              "log_level": "DEBUG",
          },
          "message": ""
      }

   :resjson str our_version: The version of rotki present in the system
   :resjson str latest_version: The latest version of rotki available
   :resjson str download_url: URL link to download the latest version
   :resjson str data_directory: The rotki data directory
   :resjson str log_level: The log level used in the backend. Can be ``DEBUG``, ``INFO``, ``WARN``, ``ERROR`` or ``CRITICAL``.

   :statuscode 200: Information queried successfully
   :statuscode 500: Internal rotki error


Sending a Ping
====================

.. http:get:: /api/(version)/ping

   Doing a GET on the ping endpoint will return true. It serves as a very fast way to check the connection to the API and that everything necessary for other calls has initialized.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/ping HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.

   :statuscode 200: Ping successful
   :statuscode 500: Internal rotki error

Data imports
=============

.. http:put:: /api/(version)/import

   Doing a PUT on the data import endpoint will facilitate importing data from external sources. The arguments are the source of data import and the filepath to the data for importing.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/import HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"source": "cointracking", "filepath": "/path/to/data/file", "timestamp_format": "%d/%m/%Y %H:%M:%S"}

   :reqjson str source: The source of the data to import. Valid values are ``"cointracking"``, ``"cryptocom"``, ``"blockfi_transactions"``, ``"blockfi_trades"``, ``"nexo"``,  ``"shapeshift_trades"``, ``"uphold_transactions"``, ``"bisq_trades"``, ``"binance"``, ``"rotki_events"``, ``"rotki_trades"``.
   :reqjson str filepath: The filepath to the data for importing
   :reqjson str timestamp_format: Optional. Custom format to use for dates in the CSV file. Should follow rules at `Datetime docs <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes>`__.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: Data imported. Check user messages for warnings.
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. Or premium was needed for the import and not found.
   :statuscode 500: Internal rotki error

ERC20 token info
====================

.. http:get:: /api/(version)/blockchains/ETH/erc20details

   Doing a GET to this endpoint will return basic information about a token by calling the ``decimals/name/symbol`` methods.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/erc20details HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"address": "0x6B175474E89094C44Da98b954EedeAC495271d0F"}

   :reqjson str address: The checksumed address of a contract
   :reqjson bool async_query: A boolean denoting whether the query should be made asynchronously or not. Missing defaults to false.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
             "decimals": 18,
             "symbol": "DAI",
             "name": "Dai Stablecoin"
           },
          "message": ""
      }

   :resjson object result: The result field in this response is a object with a minimum of one attribute.
   :resjson int decimals: Number of decimals for the requested contract. ``null`` if this information is not available on chain.
   :resjson str symbol: Symbol for the requested contract. ``null`` if this information is not available on chain.
   :resjson str name: Name for the requested contract. ``null`` if this information is not available on chain.
   :resjson str message: Empty string if there is no issues with the contract, for example, it not existing on the chain.
   :statuscode 200: No critical error found.
   :statuscode 409: There is an error with the address.
   :statuscode 500: Internal rotki error.

All Binance markets
======================

.. http:get:: /api/(version)/exchanges/binance/pairs

   Doing a GET to this endpoint will return all the market pairs available at binance.

   .. note::
      This endpoint will only return information if either Binance or Binance US are configured

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/exchanges/binance/pairs?location=binance HTTP/1.1
      Host: localhost:5042


   :query string location: Either ``binance`` or ``binanceus`` locations. This argument will filter the result based on the exchange type.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["BTCUSD", "ETHUSD", "XRPUSD"],
          "message": ""
      }

   :statuscode 200: Pairs successfully queried
   :statuscode 502: Failed to query pairs from the binance API and the database.

User selected Binance markets
================================

.. http:get:: /api/(version)/exchanges/binance/pairs/(exchange account name)

   Doing a GET to this endpoint will return the market pairs that the user has selected to be queried at binance.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/exchanges/binance/pairs/testExchange HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["BTCUSD", "ETHUSD"],
          "message": ""
      }


Querying  NFTs
============================

.. http:get:: /api/(version)/nfts

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a GET on the NFTs endpoint will query all NFTs for all user tracked addresses.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/nfts HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": false, "ignore_cache": true}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :param bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "addresses": {
            "0xeE3766e4F996DC0e0F8c929954EAAFef3441de87": [
              {
                "token_identifier": "8636",
                "name": "BASTARD GAN PUNK V2 #8636",
                "background_color": null,
                "image_url": "https://lh3.googleusercontent.com/kwF-39qZlluEalQnNv-yMxbntzNdc3g00pK2xALkpoir9ooWttVUO2hVFWOgPtOkJOHufYRajfn-nNFdjruRQ4YaMgOYHEB8E4CdjBk",
                "external_link": "https://www.bastardganpunks.club/v2/8636",
                "price_eth": "0.025",
                "price_usd": "250",
                "collection": {
                  "name": "BASTARD GAN PUNKS V2",
                  "banner_image": "https://lh3.googleusercontent.com/InX38GA4YmuR2ukDhN0hjf8-Qj2U3Tdw3wD24IsbjuXNtrTZXNwWiIeWR9bJ_-rEUOnQgkpLbj71TDKrzNzHLHkOSRdLo8Yd2tE3_jg=s2500",
                  "description": "VERSION 2 OF BASTARD GAN PUNKS ARE COOLER, BETTER AND GOOFIER THAN BOTH BOOMER CRYPTOPUNKS & VERSION 1 BASTARD GAN PUNKS. THIS TIME, ALL CRYPTOPUNK ATTRIBUTES ARE EXTRACTED AND A NEW DATASET OF ALL COMBINATIONS OF THEM ARE TRAINED WITH GAN TO GIVE BIRTH TO EVEN MORE BADASS ONES. ALSO EACH ONE HAS A UNIQUE STORY GENERATED FROM MORE THAN 10K PUNK & EMO SONG LYRICS VIA GPT-2 LANGUAGE PROCESSING ALGORITHM. \r\n\r\nBASTARDS ARE SLOWLY DEGENERATING THE WORLD. ADOPT ONE TO KICK EVERYONE'S ASSES!\r\n\r\nDISCLAIMER: THIS PROJECT IS NOT AFFILIATED WITH LARVA LABS",
                  "large_image": "https://lh3.googleusercontent.com/vF8johTucYy6yycIOJTM94LH-wcDQIPTn9-eKLMbxajrm7GZfJJWqxdX6uX59pA4n4n0QNEn3bh1RXcAFLeLzJmq79aZmIXVoazmVw=s300"
                }
              }
            ]
          },
          "entries_found": 95,
          "entries_limit": 500
        },
        "message": ""
      }


   :resjson object addresses: A mapping of ethereum addresses to list of owned NFTs.
   :resjson int entries_found: The number of NFT entries found. If non-premium and the free limit has been hit this will be equal to the limit, since we stop searching after the limit.
   :resjson int entries_limit: The free limit for NFTs.
   :resjson string token_identifier: The identifier of the specific NFT token for the given contract type. This is not a unique id across all NFTs.
   :resjson string background_color: [Optional]. A color for the background of the image of the NFT. Can be Null.
   :resjson string image_url: [Optional]. Link to the image of the NFT. Can be Null.
   :resjson string name: [ Optional] The name of the NFT. Can be Null.
   :resjson string external_link: [Optional]. A link to the page of the creator of the NFT. Can be Null.
   :resjson string permalink: [Optional]. A link to the NFT in opensea.
   :resjson string price_eth: The last known price of the NFT in ETH. Can be zero.
   :resjson string price_usd: The last known price of the NFT in USD. Can be zero.
   :statuscode 200: NFTs successfully queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or nft module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as opensea could not be reached or returned unexpected response.


Show NFT Balances
=======================

.. http:get:: /api/(version)/nfts/balances

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a GET on the NFTs balances endpoint will query all NFTs for all user tracked addresses and return those whose price can be detected.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/nfts/balances HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": false, "ignore_cache": false}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :param bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

        {
            "result": {
                "0xeE3766e4F996DC0e0F8c929954EAAFef3441de87": [
                    {
                        "id": "unique id",
                        "name": "a name",
                        "collection_name": "A collection name",
                        "manually_input": true,
                        "price_asset": "ETH",
                        "price_in_asset": "1",
                        "usd_price": "2501.15"
                        "image_url": "https://storage.opensea.io/files/305952feb5321a50d5d4f6ab6c16da1f.mov",
                        "is_lp": false
                    }, {
                        "id": "unique id 2",
                        "name": null,
                        "collection_name": "A collection name",
                        "manually_input": false,
                        "price_asset": "USD",
                        "price_in_asset": "150.55",
                        "usd_price": "150.55"
                        "image_url": "https://lh3.googleusercontent.com/xJpOAw7P96jdPgs91w7ZQMTq91tvcCva4J2RYHh7LjFufod_UP9FE0bVjhp1cYpbx2p1qFFj2NDFf3oS0eEcNI3L5w",
                        "is_lp": true
                }],
            },
            "message": ""
        }


   :resjson object addresses: A mapping of ethereum addresses to list assets and balances. ``name`` can also be null. ``collection_name`` can be null if nft does not have a collection.
   :statuscode 200: NFT balances successfully queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or nft module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as opensea could not be reached or returned unexpected response.


Querying database information
=================================

.. http:get:: /api/(version)/database/info


   Doing a GET on the database information will query information about the global database. If a user is logged in it will also query info on the user's DB and potential backups.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history/database/info HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "globaldb": {"globaldb_assets_version": 10, "globaldb_schema_version": 2},
              "userdb": {
                  "info": {
                      "filepath": "/home/username/.local/share/rotki/data/user/rotkehlchen.db",
                      "size": 5590482,
                      "version": 30
                  },
                  "backups": [{
                      "size": 323441, "time": 1626382287, "version": 27
                  }, {
                      "size": 623441, "time": 1623384287, "version": 24
                  }]
          }
          "message": ""
      }

   :resjson object globaldb: An object with information on the global DB
   :resjson int globaldb_assets_version: The version of the global database's assets.
   :resjson int globaldb_schema_version: The version of the global database's schema.
   :resjson object userdb: An object with information on the currently logged in user's DB. If there is no currently logged in user this is an empty object.
   :resjson object info: Under the userdb this contains the info of the currently logged in user. It has the path to the DB file, the size in bytes and the DB version.
   :resjson list backups: Under the userdb this contains the list of detected backups (if any) for the user db. Each list entry is an object with the size in bytes of the backup, the unix timestamp in which it was taken and the user DB version.
   :statuscode 200: Data were queried successfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.

Creating a database backup
=================================

.. http:put:: /api/(version)/database/backups


   Doing a PUT on the database backups endpoint will immediately create a backup of the current user's database.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/history/database/backups HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": "/path/to/created/1633042045_rotkehlchen_db_v28.backup",
          "message": ""
      }

   :resjson string result: The full path of the newly created database backup

   :statuscode 200: Backup was created successfully.
   :statuscode 409: No user is currently logged in or failure to create the DB backup.
   :statuscode 500: Internal rotki error.

Deleting a database backup
=================================

.. http:delete:: /api/(version)/database/backups


   Doing a DELETE on the database backups endpoint with the backup filepath will delete it.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/history/database/backups HTTP/1.1
      Host: localhost:5042

      {"file": "/path/to/created/1633042045_rotkehlchen_db_v28.backup"}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: True for success

   :statuscode 200: Backup was deleted successfully.
   :statuscode 400: The given filepath does not exist
   :statuscode 409: No user is currently logged in or failure to delete the backup or the requested file to delete is not in the user's data directory.
   :statuscode 500: Internal rotki error.

Downloading a database backup
=================================

.. http:get:: /api/(version)/database/backups


   Doing a GET on the database backups endpoint with the backup filepath will download it.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history/database/backups HTTP/1.1
      Host: localhost:5042

      {"file": "/path/to/created/1633042045_rotkehlchen_db_v28.backup"}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/octet-stream


   :statuscode 200: Backup was downloaded successfully.
   :statuscode 400: The given filepath does not exist
   :statuscode 409: No user is currently logged in or failure to download the backup or the requested file to download is not in the user's data directory.
   :statuscode 500: Internal rotki error.

Get associated locations
========================

.. http:get:: /api/(version)/locations/associated

   Doing a GET on this endpoint will return a list of locations where the user has information. It contains locations imported in CSV, exchanges and DeFi locations.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/locations/associated HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["nexo", "kraken", "uniswap"],
          "message": ""
      }

   :statuscode 200: Locations successfully queried.
   :statuscode 409: User is not logged in. Check error message for details.
   :statuscode 500: Internal Rotki error

Staking events
==============

.. http:get:: /api/(version)/staking/kraken

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on this endpoint will return all staking events for the desired location. At the moment
   the only valid location is kraken. If the retrieval of new information fails the information at the
   database will be returned

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/staking/kraken HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "only_cache": false}

   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: Optional. This is the list of attributes of the history by which to order the results. If none is given 'timestamp' is assumed. Valid values are: ['timestamp', 'location', 'amount'].
   :reqjson list[bool] ascending: Optional. False by default. Defines the order by which results are returned depending on the chosen order by attribute.
   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson bool only_cache: Optional.If this is true then the equivalent exchange/location is not queried, but only what is already in the DB is returned.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "events": [
                {
                    "event_type": "unstake asset",
                    "asset": "ETH2",
                    "timestamp": 1636740198,
                    "location": "kraken",
                    "amount": "0.0600000000",
                    "usd_value": "278.7345000000000"
                },
                {
                  "event_type": "get reward",
                  "asset": "ETH2",
                  "timestamp": 1636864588,
                  "location": "kraken",
                  "amount": "0.0000103220",
                  "usd_value": "0.0478582110500"
                },
                {
                    "event_type": "stake asset",
                    "asset": "ETH",
                    "timestamp": 1636738550,
                    "location": "kraken",
                    "amount": "0.0600000000",
                    "usd_value": "278.7345000000000"
                }
              ],
              "entries_found": 3,
              "entries_total": 3,
              "entries_limit": -1,
              "total_usd_value": "0.02",
              "assets": ["ETH2", "ETH"],
              "received": [
                  {
                      "asset": "ETH2",
                      "amount": "0.0000103220",
                      "usd_value": "0.21935353362"
                  }
              ]
          },
          "message": ""
      }

   :resjsonarr int timestamp: The timestamp at which the event occurred
   :resjsonarr string location: A valid location at which the event happened
   :resjsonarr string amount: The amount related to the event
   :resjsonarr string asset: Asset involved in the event
   :resjsonarr string event_type: Type of event. Can be `reward`, `deposit asset` or  `remove asset`.
   :resjsonarr string message: It won't be empty if the query to external services fails for some reason.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_limit: The limit of entries if free version. -1 for premium.
   :resjson int entries_total: The number of total entries ignoring all filters.
   :resjsonarr string total_usd_value: Sum of the USD value for the assets received computed at the time of acquisition of each event.
   :resjson list[string] assets: Assets involved in events ignoring all filters.
   :resjson list[object] received: Assets received with the total amount received for each asset and the aggregated USD value at time of acquisition.

   :statuscode 200: Events are successfully returned
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in, kraken is not active or some parameter for filters is not valid.
   :statuscode 500: Internal rotki error


Export assets added by the user
===============================

.. http:put:: /api/(version)/assets/user

   Calling this endpoint with PUT and action `download` will create a zip file with the assets that are not included by default with vanilla rotki. If no destination folder is provided the generated file is returned with headers `application/zip`.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/user HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"action": "download", "destination": "/home/user/Downloads"}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
                "file": "/home/user/Downloads/assets.zip"
          },
          "message": ""
      }

   :resjsonarr string action: Action performed on the endpoint
   :resjsonarr string destination: Folder where the generated files will be saved

   :statuscode 200: Response file is correctly generated
   :statuscode 409: No user is logged in.
   :statuscode 507: Failed to create the file.


Import assets added by the user
===============================

.. http:put:: /api/(version)/assets/user
.. http:post:: /api/(version)/assets/user

   Doing a put or a post to this endpoint will import the assets in the json file provided. The file has to follow the rotki expected format and will be verified.

   .. note::
      If doing a POST the `action` field is not required.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/user HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"action": "upload", "file": "/tmp/assets.zip"}


   :resjsonarr string action: Action performed on the endpoint
   :resjsonarr string file: The path to the file to upload for PUT. The file itself for POST.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :statuscode 200: Assets correctly imported
   :statuscode 409: No user is logged in, imported file is for an older version of the schema or file can't be loaded or format is not valid.
   :statuscode 500: Internal rotki error
   :statuscode 507: Filesystem error, probably related to size.


Handling snapshot manipulation
================================

.. http:get:: /api/(version)/snapshots/(timestamp)

   Doing a GET on this endpoint without any action query parameter will return the database snapshot for the specified timestamp in JSON.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/snapshots/149095883 HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "balances_snapshot": [
                    {
                        "timestamp": 149095883,
                        "category": "asset",
                        "asset_identifier": "AVAX",
                        "amount": "1000.00",
                        "usd_value": "12929.00",
                    }
                ],
              "location_data_snapshot": [
                    {
                        "timestamp": 149095883,
                        "location": "external",
                        "usd_value": "12929.00"
                    },
                    {
                        "timestamp": 149095883,
                        "location": "total",
                        "usd_value": "12929.00"
                    }
              ]
          },
          "message": ""
      }

   :resjson object result: A dictionary representing the snapshot at the specified timestamp.
   :statuscode 200: Snapshot was retrieved successfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 404: No snapshot data found for the given timestamp.
   :statuscode 500: Internal rotki error.


.. http:get:: /api/(version)/snapshots/(timestamp)

   Doing a GET on this endpoint with action ``'export'`` will export the database snapshot for the specified timestamp to CSV files and save them in the given directory.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/snapshots/149095883?action=export&path=/home/user/documents HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

   :reqquery str path: The directory in which to write the exported CSV files.
   :reqquery str action: The action to be performed by the endpoint. Can be one of ``'export'``, ``'download'``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :resjson bool result: Boolean denoting success or failure of the query.
   :statuscode 200: Files were exported successfully.
   :statuscode 400: Provided query parameter(s) is in some way malformed or given path is not a directory.
   :statuscode 409: No user is currently logged in. No snapshot data found for the given timestamp. No permissions to write in the given directory. Check error message.
   :statuscode 500: Internal rotki error.


.. http:get:: /api/(version)/snapshots/(timestamp)

   Doing a GET on this endpoint with action ``'download'`` will download database snapshot for the specified timestamp as a zip file.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/snapshots/149095883?action=download HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

   :reqquery str action: The action to be performed by the endpoint. Can be one of ``'export'``, ``'download'``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip


   :statuscode 200: Snapshot was downloaded successfully.
   :statuscode 400: Provided query parameter(s) is in some way malformed.
   :statuscode 409: No user is currently logged in. No snapshot data found for the given timestamp. No permissions to write in the given directory. Check error message.
   :statuscode 500: Internal rotki error.


.. http:delete:: /api/(version)/snapshots

   Doing a DELETE on this endpoint will delete the snapshot for the specified timestamp.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/snapshots HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"timestamp": 149095883}

   :reqjson int timestamp: The epoch timestamp representing the time of the snapshot to be deleted.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip


   :statuscode 200: Snapshot was deleted successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. No snapshot found for the specified timestamp.Check error message.
   :statuscode 500: Internal rotki error.


.. http:patch:: /api/(version)/snapshots/(timestamp)

   Doing a PATCH on this endpoint will replace the snapshot at the specified timestamp with the provided payload.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/snapshots/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

        {
            "balances_snapshot": [
                {
                    "timestamp": 149095883,
                    "category": "asset",
                    "asset_identifier": "AVAX",
                    "amount": "1000.00",
                    "usd_value": "12929.00"
                }
            ],
            "location_data_snapshot": [
                {
                    "timestamp": 149095883,
                    "location": "external",
                    "usd_value": "12929.00"
                },
                {
                    "timestamp": 149095883,
                    "location": "total",
                    "usd_value": "12929.00"
                }
            ]
        }

   :reqjson list balances_snapshot: The list of objects representing the balances of an account to be updated. All fields are required i.e ``"timestamp"``, ``"category"``, ``"asset_identifier"``, ``"amount"``, ``"usd_value"``.
   :reqjson list location_data_snapshot: The list of objects representing the location data to be updated. All fields are required i.e ``"timestamp"``, ``"location"``, ``"usd_value"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip


   :statuscode 200: Snapshot was updated successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. JSON has different timestamps. Snapshot contains an unknown asset. JSON has invalid headers. Check error message.
   :statuscode 500: Internal rotki error.


.. http:put:: /api/(version)/snapshots
.. http:post:: /api/(version)/snapshots

   Doing either a PUT or a POST on this import endpoint will import database snapshot from the specified paths in the request body.
   PUT expect paths to the files to be imported. POST expects the files to be uploaded as multipart/form-data.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/snapshots HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "balances_snapshot_file": "/path/to/balances_snapshot_import.csv",
          "location_data_snapshot_file": "/path/to/location_data_snapshot.csv"
      }

   :reqjson str balances_snapshot_file: The path to a `balances_snapshot_import.csv` file that was previously exported.
   :reqjson str location_data_snapshot_file: The path to a `location_data_snapshot.csv` file that was previously exported.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip


   :statuscode 200: Snapshot was imported successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. Csv file has different timestamps. Snapshot contains an unknown asset. Csv file has invalid headers. Check error message.
   :statuscode 500: Internal rotki error.


Get ENS names
=============================================

.. http:post:: /api/(version)/names/ens/reverse

   Doing a POST on the ENS reverse endpoint will return the ENS names for
   the given ethereum addresses from cache if found and from blockchain otherwise.
   If ignore_cache is true, then the entire cache will be recreated

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/names/ens/reverse HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "ethereum_addresses": ["0x1", "0x2"]
      }

    .. http:example:: curl wget httpie python-requests

          POST /api/1/naminens/reverse HTTP/1.1
          Host: localhost:5042
          Content-Type: application/json;charset=UTF-8

          {
              "ethereum_addresses": ["0x1", "0x2"],
              "ignore_cache": true
          }

   :reqjson list ethereum_addresses: A list of ethereum addresses to get names for.
   :reqjson bool ignore_cache: If true, the entire cache will be updated.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0x1": "name1",
              "0x2": "name2"
          },
          "message": "",
      }

   :resjson object result: A dictionary of ethereum address to ENS name.
   :resjson str message: Error message if any errors occurred.
   :statuscode 200: Names were returned successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: Failed to query names or no user is currently logged in or addresses have incorrect format.
   :statuscode 500: Internal rotki error.


Get mappings from addressbook
==============================

.. http:post:: /api/(version)/names/addressbook

    Doing a POST on the addressbook endpoint with either /global or /private postfix with a list of addresses will return found address mappings for specified addresses. If addresses parameter isn't specified, all known mappings are returned.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        POST /api/1/names/addressbook/global HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "addresses": ["0x9531c059098e3d194ff87febb587ab07b30b1306", "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD"]
        }

    :reqjson object addresses: List of addresses that the backend should find names for

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": [
                { "address": "0x9531c059098e3d194ff87febb587ab07b30b1306", "name": "My dear friend Tom" },
                { "address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD", "name": "Neighbour Frank" }
            ],
            "message": ""
        }

    :resjson object result: A dictionary of mappings. Address -> name.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Mappings were returned successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: No user is currently logged in or addresses have incorrect format.
    :statuscode 500: Internal rotki error.


Insert mappings into addressbook
================================

.. http:put:: /api/(version)/names/addressbook

    Doing a PUT on the addressbook endpoint with either /global or /private postfix with a list of entries, each entry containing address and a name will add these entries to the addressbook.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        PUT /api/1/names/addressbook/private HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "entries": [
            {"address": "0x9531c059098e3d194ff87febb587ab07b30b1306", "name": "Dude ABC"},
            {"address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD", "name": "Dude XYZ"}
          ]
        }

    :reqjson object entries: A list of entries to be added to the addressbook

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": True,
            "message": ""
        }

    :resjson bool result: A boolean which is true in the case that entries were added successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Entries were added successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: Some of the provided entries already exist in the addressbook or no user is currently logged in or addresses have incorrect format.
    :statuscode 500: Internal rotki error.


Update mappings in the addressbook
==================================

.. http:patch:: /api/(version)/names/addressbook

    Doing a PATCH on the addressbook endpoint with either /global or /private postfix with a list of entries, each entry containing address and a name will updates these entries' names in the addressbook

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        PATCH /api/1/names/addressbook/private HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "entries": [
            {"address": "0x9531c059098e3d194ff87febb587ab07b30b1306", "name": "Dude ABC"},
            {"address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD", "name": "Dude XYZ"}
          ]
        }

    :reqjson object entries: A list of entries to be updated in the addressbook

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": True,
            "message": ""
        }

    :resjson bool result: A boolean which is true in case if entries were updated successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Entries were updated successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: Some of the provided entries don't exist in the addressbook or no user is currently logged in or addresses have incorrect format.
    :statuscode 500: Internal rotki error.


Delete mappings in the addressbook
==================================

.. http:delete:: /api/(version)/names/addressbook

    Doing a DELETE on the addressbook endpoint with either /global or /private postfix with a list of addresses will delete mappings in the addressbook of the specified addresses

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        DELETE /api/1/names/addressbook/global HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "addresses": ["0x9531c059098e3d194ff87febb587ab07b30b1306", "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD"]
        }

    :reqjson object entries: A list of addresses to be deleted from the addressbook

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": True,
            "message": ""
        }

    :resjson bool result: A boolean which is true in case if entries were deleted successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Entries were deleted successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: Some of the provided entries don't exist in the addressbook or no user is currently logged in or addresses have incorrect format.
    :statuscode 500: Internal rotki error.


Search for all known names of an address
========================================

.. http:post:: /api/(version)/names

    Doing a POST on all names endpoint with a list of addresses will search for names of these addresses in all places and return a name for each address if found. Only one name is returned. The priority of the returned names adheres to the following order: private addressbook > blockchain account labels > global addressbook > ethereum tokens > hardcoded mappings > ENS names.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        POST /api/1/names HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "addresses": ["0x9531c059098e3d194ff87febb587ab07b30b1306", "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD"]
        }

    :reqjson object addresses: List of addresses that the backend should find names for

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": {
                "0x9531c059098e3d194ff87febb587ab07b30b1306": "My blockchain account 1",
                "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD": "Neighbour Frank",
            },
            "message": ""
        }

    :resjson object result: A dictionary of mappings. Address -> name.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Mappings were returned successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: No user is currently logged in or addresses have incorrect format.
    :statuscode 500: Internal rotki error.


Handling user notes
================================

.. http:post:: /api/(version)/notes

   Doing a POST on this endpoint will return all the user notes present in the database.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/notes HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 12345677, "to_timestamp": 12345679, "title_substring": "#"}

   :reqjson int limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: This is the list of attributes of the note by which to order the results. By default we sort using ``last_update_timestamp``.
   :reqjson list[bool] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.
   :reqjson int from_timestamp: The timestamp after which to return transactions. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return transactions. If not given all transactions from ``from_timestamp`` until now are returned.
   :reqjson string title_substring: The substring to use as filter for the title of the notes.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
                "entries": [{
                        "identifier": 1,
                        "title": "#1",
                        "content": "Hello, World!",
                        "location": "manual balances",
                        "last_update_timestamp": 12345678,
                        "is_pinned": true
                    },
                    {
                        "identifier": 2,
                        "title": "#2",
                        "content": "Hi",
                        "location": "manual balances",
                        "last_update_timestamp": 12345699,
                        "is_pinned": false
                }],
                "entries_found": 2,
                "entries_total": 2,
                "entries_limit": -1
            },
          "message": ""
      }

   :resjson object result: An array of objects representing user note entries.
   :resjson int identifier: The unique identifier of the user note.
   :resjson str title: The title of the note.
   :resjson str content: The content of the note.
   :resjson str location: The location inside the application the note was taken.
   :resjson int last_update_timestamp: The timestamp the note was last updated.
   :resjson bool is_pinned: Whether the note has been pinned by the user or not.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_limit: The limit of entries if free version. -1 for premium.
   :resjson int entries_total: The number of total entries ignoring all filters.

   :statuscode 200: User notes were retrieved successfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.

.. http:delete:: /api/(version)/notes

   Doing a DELETE on this endpoint will delete a user note for the specified identifier.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/notes HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"identifier": 149095883}

   :reqjson int identifier: The identifier of the user note you're trying to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip

      {"result": true, "message": ""}

   :statuscode 200: User note was deleted successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. No user note found. Check error message.
   :statuscode 500: Internal rotki error.


.. http:patch:: /api/(version)/notes

   Doing a PATCH on this endpoint will update the content of an already existing user note.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/notes HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

        {
            "identifier": 2,
            "title": "#2",
            "content": "Go to bed",
            "location": "manual balances",
            "last_update_timestamp": 12345699,
            "is_pinned": false
        }

   :reqjson int identifier: The unique identifier of the user note.
   :reqjson str title: The title of the note.
   :reqjson str content: The content of the note.
   :reqjson str location: The location inside the application the note was taken.
   :reqjson int last_update_timestamp: The timestamp the note was last updated.
   :resjson bool is_pinned: Whether the note has been pinned by the user or not.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip

      {"result": true, "message": ""}

   :statuscode 200: User note was updated successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. User note does not exist.
   :statuscode 500: Internal rotki error.


.. http:put:: /api/(version)/notes

   Doing a PUT on this endpoint will add a new user note to the DB.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/notes HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
            "title": "#5",
            "content": "Go to bed now",
            "location": "ledger actions"
      }

   :reqjson str title: The title of the note to be created.
   :reqjson str content: The content of the note to be created.
   :reqjson str location: The location inside the application the note was taken.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 201 OK
      Content-Type: application/zip

      {"result": 1, "message": ""}

   :resjson int result: The unique identifier of the note created.

   :statuscode 200: User note was added successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. User note with the given title already exists. User has reached the limit of available notes. Check error message.
   :statuscode 500: Internal rotki error.


Custom Assets
================

.. http:post:: /api/(version)/assets/custom

   Doing a POST on this endpoint will return all the custom assets present in the database using the filter parameters.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/assets/custom HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"name": "land", "custom_asset_type": "real estate"}

   :reqjson int[optional] limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int[optional] offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson string[optional] name: The name of the custom asset to be used as a filter.
   :reqjson string[optional] identifier: The identifier of the custom asset to be used as a filter.
   :reqjson string[optional] custom_asset_type: The type of the custom asset to be used as a filter.
   :reqjson list[string][optional] order_by_attributes: This is the list of attributes of the custom asset by which to order the results. By default we sort using ``name``.
   :reqjson list[bool][optional] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
                "entries": [{
                        "identifier": "00fe5f97-882b-42e5-b0e0-39ebd3a99156'",
                        "name": "House",
                        "notes": "Apartment purchase",
                        "custom_asset_type": "real estate"
                    },
                    {
                        "identifier": "333c248f-7c64-41f4-833b-2fad96c4ea6b",
                        "name": "Ferrari",
                        "notes": "Exotic car inheritance from lineage",
                        "custom_asset_types": "vehicles"
                }],
                "entries_found": 2,
                "entries_total": 2,
            },
          "message": ""
      }

   :resjson object result: An array of objects representing custom assets entries.
   :resjson str identifier: The unique identifier of the custom asset.
   :resjson str name: The name of the custom asset.
   :resjson str notes: The notes used as a description of the custom asset. This field can be null.
   :resjson str custom_asset_type: The type/category of the custom asset.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_total: The number of total entries ignoring all filters.

   :statuscode 200: Custom assets were retrieved successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.

.. http:delete:: /api/(version)/assets/custom

   Doing a DELETE on this endpoint will delete a custom asset for the specified identifier.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/custom HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"identifier": "aca42c5d-36f1-4a8b-af28-5aeb322748b5"}

   :reqjson str identifier: The identifier of the custom asset you're trying to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip

      {"result": true, "message": ""}

   :statuscode 200: Custom asset was deleted successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. No custom asset found. Check error message.
   :statuscode 500: Internal rotki error.


.. http:patch:: /api/(version)/assets/custom

   Doing a PATCH on this endpoint will update the content of an already existing custom asset.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/assets/custom HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

        {
            "identifier": "de0b49aa-65e1-4b4e-94b5-d1cd3e4baee1",
            "name": "Hotel",
            "notes": "Hotel from ma",
            "custom_asset_type": "real estate"
        }

   :reqjson str identifier: The unique identifier of the custom asset to update.
   :reqjson str name: The name of the custom asset.
   :reqjson str custom_asset_type: The type/category of the custom asset.
   :reqjson str[optional] notes: The notes that serve as a description of the custom asset. This is optional.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/zip

      {"result": true, "message": ""}

   :statuscode 200: Custom asset was updated successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. Custom asset name and type is already being used. Custom asset does not exist.  Check error message.
   :statuscode 500: Internal rotki error.


.. http:put:: /api/(version)/assets/custom

   Doing a PUT on this endpoint will add a new custom asset to the DB.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/custom HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
            "name": "Yacht",
            "custom_asset_type": "flex"
      }

   :reqjson str name: The name of the custom asset to be created.
   :reqjson str custom_asset_type: The type/category of the custom asset.
   :reqjson str[optional] notes: The notes of the custom asset to be created. This is optional.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 201 OK
      Content-Type: application/zip

      {"result": "c0c991f0-6511-4b0d-83fc-40fde8495874", "message": ""}

   :resjson str result: The unique identifier of the custom asset created.

   :statuscode 200: Custom asset was created successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in. Custom asset with the given name and type already exists. Check error message.
   :statuscode 500: Internal rotki error.


.. http:get:: /api/(version)/assets/custom/types

   Doing a GET on this endpoint will return all the custom asset types in the DB sorted in ascending order.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/custom/types HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 201 OK
      Content-Type: application/zip

      {"result": ["medals", "real estate", "stocks"], "message": ""}

   :resjson list[str] result: The list of custom asset types in the DB.

   :statuscode 200: Custom asset types retrieved successfully.
   :statuscode 409: No user is currently logged in. Check error message.
   :statuscode 500: Internal rotki error.
