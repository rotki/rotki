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


In the case of a succesful response the ``"result"`` attribute is populated and is not ``null``. The message is almost always going to be empty but may at some cases also contain some informational message.

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
   :statuscode 200: Users query is succesful
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
            "initial_settings": {
                "submit_usage_analytics": false
            }
      }

   :reqjson string name: The name to give to the new user
   :reqjson string password: The password with which to encrypt the database for the new user
   :reqjson string[optional] premium_api_key: An optional api key if the user has a rotki premium account.
   :reqjson string[optional] premium_api_secret: An optional api secret if the user has a rotki premium account.
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
                  "eth_rpc_endpoint": "http://localhost:8545",
                  "ksm_rpc_endpoint": "http://localhost:9933",
                  "main_currency": "USD",
                  "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
                  "last_balance_save": 1571552172,
                  "submit_usage_analytics": true,
                  "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"],
                  "current_price_oracles": ["cryptocompare", "coingecko"],
                  "historical_price_oracles": ["cryptocompare", "coingecko"],
                  "taxable_ledger_actions": ["income", "airdrop"]
              }
          },
          "message": ""
      }

   :resjson object result: For succesful requests, result contains the currently connected exchanges, and the user's settings. For details on the user settings refer to the `Getting or modifying settings`_ section.
   :statuscode 200: Adding the new user was succesful
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User already exists. Another user is already logged in. Given Premium API credentials are invalid. Permission error while trying to access the directory where rotki saves data.
   :statuscode 500: Internal rotki error

.. http:patch:: /api/(version)/users/(username)

   By doing a ``PATCH`` at this endpoint with action ``'login'`` you can login to the user with ``username``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/users/john HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "action": "login",
          "password": "supersecurepassword",
          "sync_approval": "unknown"
      }

   :reqjson string action: The action to perform. Can only be one of ``"login"`` or ``"logout"`` and for the login case has to be ``"login"``
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
                  "eth_rpc_endpoint": "http://localhost:8545",
                  "ksm_rpc_endpoint": "http://localhost:9933",
                  "main_currency": "USD",
                  "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
                  "last_balance_save": 1571552172,
                  "submit_usage_analytics": true,
                  "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"],
                  "current_price_oracles": ["cryptocompare", "coingecko"],
                  "historical_price_oracles": ["cryptocompare", "coingecko"],
                  "taxable_ledger_actions": ["income", "airdrop"]
              }
          },
          "message": ""
      }

   :resjson object result: For succesful requests, result contains the currently connected exchanges,and the user's settings. For details on the user settings refer to the `Getting or modifying settings`_ section.
   :statuscode 200: Logged in succesfully
   :statuscode 300: Possibility of syncing exists and the login was sent with sync_approval set to ``"unknown"``. Consumer of api must resend with ``"yes"`` or ``"no"``. In this case the result will contain an object with a payload for the message under the ``result`` key and the message under the ``message`` key. The payload has the following keys: ``local_size``, ``remote_size``, ``local_last_modified``, ``remote_last_modified``.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: Provided password is wrong for the user or some other authentication error.
   :statuscode 409: Another user is already logged in. User does not exist. There was a fatal error during the upgrade of the DB. Permission error while trying to access the directory where rotki saves data.
   :statuscode 500: Internal rotki error

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

   :reqjson string action: The action to perform. Can only be one of ``"login"`` or ``"logout"`` and for the logout case has to be ``"logout"``

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: Logged out succesfully
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
   :statuscode 200: API key/secret deleted succesfully
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
   :statuscode 200: Password changed succesfully
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
              "alethio": {"api_key": "goooookey"}
          },
          "message": ""
      }

   :resjson object result: The result object contains as many entries as the external services. Each entry's key is the name and the value is another object of the form ``{"api_key": "foo"}``
   :statuscode 200: Querying of external service credentials was succesful
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
   :reqjsonarr string name: Each entry in the list should have a name for the service. Valid ones are ``"etherscan"``, ``"cryptocompare"`` and ``"alethio"``.
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
   :statuscode 200: Saving new external service credentials was succesful
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

   :reqjson list services: A list of service names to delete. The only possible names at the moment are ``"etherscan"``, ``"cryptocompare"`` and ``"alethio"``.

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
   :statuscode 200: Deleting external service credentials was succesful
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
              "eth_rpc_endpoint": "http://localhost:8545",
              "ksm_rpc_endpoint": "http://localhost:9933",
              "main_currency": "USD",
              "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
              "last_balance_save": 1571552172,
              "submit_usage_analytics": true,
              "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"],
              "current_price_oracles": ["coingecko"],
              "historical_price_oracles": ["cryptocompare", "coingecko"],
              "taxable_ledger_actions": ["income", "airdrop"]
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
   :resjson string eth_rpc_endpoint: A URL denoting the rpc endpoint for the ethereum node to use when contacting the ethereum blockchain. If it can not be reached or if it is invalid etherscan is used instead.
   :resjson string ksm_rpc_endpoint: A URL denoting the rpc endpoint for the Kusama node to use when contacting the Kusama blockchain. If it can not be reached or if it is invalid any default public node (e.g. Parity) is used instead.
   :resjson string main_currency: The asset to use for all profit/loss calculation. USD by default.
   :resjson string date_display_format: The format in which to display dates in the UI. Default is ``"%d/%m/%Y %H:%M:%S %Z"``.
   :resjson int last_balance_save: The timestamp at which the balances were last saved in the database.
   :resjson bool submit_usage_analytics: A boolean denoting wether or not to submit anonymous usage analytics to the rotki server.
   :resjson list active_module: A list of strings denoting the active modules with which rotki is running.
   :resjson list current_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting current prices.
   :resjson list historical_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting historical prices.
   :resjson list taxable_ledger_actions: A list of strings denoting the ledger action types that will be taken into account in the profit/loss calculation during accounting. All others will only be taken into account in the cost basis and will not be taxed.

   :statuscode 200: Querying of settings was succesful
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
   :reqjson string[optional] eth_rpc_endpoint: A URL denoting the rpc endpoint for the ethereum node to use when contacting the ethereum blockchain. If it can not be reached or if it is invalid etherscan is used instead.
   :reqjson string[optional] ksm_rpc_endpoint: A URL denoting the rpc endpoint for the Kusama node to use when contacting the Kusama blockchain. If it can not be reached or if it is invalid any default public node (e.g. Parity) is used instead.
   :reqjson string[optional] main_currency: The FIAT currency to use for all profit/loss calculation. USD by default.
   :reqjson string[optional] date_display_format: The format in which to display dates in the UI. Default is ``"%d/%m/%Y %H:%M:%S %Z"``.
   :reqjson bool[optional] submit_usage_analytics: A boolean denoting wether or not to submit anonymous usage analytics to the rotki server.
   :reqjson list active_module: A list of strings denoting the active modules with which rotki should run.
   :reqjson list current_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting current prices.
   :reqjson list historical_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting historical prices.
   :reqjson list taxable_ledger_actions: A list of strings denoting the ledger action types that will be taken into account in the profit/loss calculation during accounting. All others will only be taken into account in the cost basis and will not be taxed.

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
              "eth_rpc_endpoint": "http://localhost:8545",
              "ksm_rpc_endpoint": "http://localhost:9933",
              "main_currency": "USD",
              "date_display_format": "%d/%m/%Y %H:%M:%S %Z",
              "last_balance_save": 1571552172,
              "submit_usage_analytics": true,
              "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"],
              "current_price_oracles": ["cryptocompare"],
              "historical_price_oracles": ["coingecko", "cryptocompare"],
              "taxable_ledger_actions": ["income", "airdrop"]
          },
          "message": ""
      }

   :resjson object result: Same as when doing GET on the settings

   :statuscode 200: Modifying settings was succesful
   :statuscode 400: Provided JSON is in some way malformed, of invalid value for a setting.
   :statuscode 409: No user is logged in or tried to set eth rpc endpoint that could not be reached.
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

   :statuscode 200: Querying was succesful
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

   :statuscode 200: The task's outcome is succesfully returned or pending
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 404: There is no task with the given task id
   :statuscode 409: No user is currently logged in
   :statuscode 500: Internal rotki error

Query the current price of assets
===================================

.. http:get:: /api/(version)/assets/prices/current

   Querying this endpoint with a list of assets and a target asset will return an object with the the price of the assets in the target asset currency. Providing an empty list or no target asset is an error.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/prices/current HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "assets": ["BTC", "ETH", "_ceth_0x514910771AF9Ca656af840dff83E8264EcF986CA", "USD", "EUR"],
          "target_asset": "USD",
          "ignore_cache": true
      }

   :reqjson list assets: A list of assets to query their current price.
   :reqjson string target_asset: The target asset against which to return the price of each asset in the list.
   :reqjson bool async_query: A boolean denoting whether the query should be made asynchronously or not. Missing defaults to false.
   :reqjson bool ignore_cache: A boolean denoting whether to ignore the current price query cache. Missing defaults to false.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "assets": {
                  "BTC": "34758.11",
                  "ETH": "1302.62",
                  "EUR": "1.209",
                  "GBP": "1.362",
                  "_ceth_0x514910771AF9Ca656af840dff83E8264EcF986CA": "20.29",
                  "USD": "1"
              },
              "target_asset": "USD"
          },
          "message": ""
      }

   :resjson object result: A JSON object that contains the price of the assets in the target asset currency.
   :resjson object assets: A map between an asset and its price.
   :resjson string target_asset: The target asset against which to return the price of each asset in the list.
   :statuscode 200: The USD prices have been sucesfully returned
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as cryptocompare/coingecko could not be reached or returned unexpected response.

Query the current exchange rate for select assets
======================================================

.. http:get:: /api/(version)/exchange_rates

   Querying this endpoint with a list of strings representing some assets will return a dictionary of their current exchange rates compared to USD.

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
   :statuscode 200: The exchange rates have been sucesfully returned
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
   :statuscode 200: The historical USD prices have been sucesfully returned
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
            "from_asset": "_ceth_0xD71eCFF9342A5Ced620049e616c5035F1dB98620",
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
            "from_asset": "_ceth_0xD71eCFF9342A5Ced620049e616c5035F1dB98620",
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
          "from_asset": "_ceth_0xD71eCFF9342A5Ced620049e616c5035F1dB98620"
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
              "from_asset": "_ceth_0xD533a949740bb3306d119CC777fa900bA034cd52",
              "to_asset": "USD",
              "timestamp": 1611166335,
              "price": "1.20"
            }, 
            {
              "from_asset": "_ceth_0xD533a949740bb3306d119CC777fa900bA034cd52",
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
        "from_asset": "_ceth_0xD71eCFF9342A5Ced620049e616c5035F1dB98620",
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
   :statuscode 200: The exchanges list has been sucesfully setup
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
   :statuscode 200: The exchange has been sucesfully setup
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
   :statuscode 200: The exchange has been sucesfully deleted
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
   :statuscode 200: The exchange has been sucesfully edited
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

   :resjson object result: If succesful contains the balances of each asset held in the exchange. Each key of the object is an asset's symbol. Then the value is another object.  In the ``"amount"`` key of that object is the amount held in the asset. And in the ``"usd_value"`` key is the equivalent $ value as of this moment.
   :statuscode 200: Balances succesfully queried.
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

   :resjson object result: If succesful contains the balances of each asset held in the exchange. Each key of the object is an asset's symbol. Then the value is another object.  In the ``"amount"`` key of that object is the amount held in the asset. And in the ``"usd_value"`` key is the equivalent $ value as of this moment.
   :statuscode 200: Balances succesfully queried.
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

   :statuscode 200: Data succesfully purged.
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

   :statuscode 200: Data succesfully purged.
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

   :statuscode 200: Data succesfully purged.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
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

   :statuscode 200: Cache succesfully created.
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

   :statuscode 200: Cache succesfully delete.
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

   :statuscode 200: Cache succesfully delete.
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

   :statuscode 200: Oracles succesfully queried
   :statuscode 500: Internal rotki error

Query supported ethereum modules
=====================================

.. http:get:: /api/(version)/blockchains/ETH/modules/

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

   :statuscode 200: Data succesfully purged.
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error

Querying ethereum transactions
=================================

.. http:get:: /api/(version)/blockchains/ETH/transactions/(address)

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a GET on the transactions endpoint for ETH will query all ethereum transactions for all the tracked user addresses. Caller can also specify an address to further filter the query as a from address. Also he can limit the queried transactions by timestamps. If the user is not premium and has more than 500 transaction then the returned transaction will be limited to that number. Any filtering will also be limited to those first 500 transaction. Transactions are returned most recent first.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/transactions/0xdAC17F958D2ee523a2206206994597C13D831ec7/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1514764800, "to_timestamp": 1572080165, "only_cache": false}

   :reqjson int from_timestamp: The timestamp after which to return transactions. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return transactions. If not given all transactions from ``from_timestamp`` until now are returned.
   :reqjson bool only_cache: If true then only the ethereum transactions in the DB are queried.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result":
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
               "ignored_in_accounting": false
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
                "ignored_in_accounting": true
            }],
            "entries_found": 95,
            "entries_limit": 500,
        "message": ""
      }

   :statuscode 200: Transactions succesfull queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

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

   :statuscode 200: Tags succesfully queried.
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
                  "description": "Accounts that are not publically associated with me",
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

   :reqjson object result: A mapping of the tags rotki knows about including our newley edited tag. Explanation of the response format is seen `here <tags_response_>`_

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

   Doing a GET on the blockchains balances endpoint will query on-chain balances for the accounts of the user. Doing a GET on a specific blockchain will query balances only for that chain. Available blockchain names are: ``BTC``, ``ETH`` and ``KSM``.

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
                           "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "15", "usd_value": "15.21"}
                       },
                       "liabilities": {
                           "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "20", "usd_value": "20.35"}
                       }
                  }}
              },
              "totals": {
                  "assets": {
                      "BTC": {"amount": "1", "usd_value": "7540.15"},
                      "ETH": {"amount": "10", "usd_value": "1650.53"},
                      "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "15", "usd_value": "15.21"}
                  },
                  "liabilities": {
                      "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "20", "usd_value": "20.35"}
                  }
              }
          },
          "message": ""
      }

   :resjson object per_account: The blockchain balances per account per asset. Each element of this object has a blockchain asset as its key. Then each asset has an address for that blockchain as its key and each address an object with the following keys: ``"amount"`` for the amount stored in the asset in the address and ``"usd_value"`` for the equivalent $ value as of the request. Ethereum accounts have a mapping of tokens owned by each account. ETH accounts may have an optional liabilities key. This would be the same as assets. BTC accounts are separated in standalone accounts and in accounts that have been derived from an xpub. The xpub ones are listed in a list under the ``"xpubs"`` key. Each entry has the xpub, the derivation path and the list of addresses and their balances.
   :resjson object total: The blockchain balances in total per asset. Has 2 keys. One for assets and one for liabilities. The liabilities key may be missing if no liabilities exist.

   :statuscode 200: Balances succesfully queried.
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

.. http:get:: /api/(version)/balances/

   Doing a GET on the balances endpoint will query all balances/debt across all locations for the user. That is exchanges, blockchains and all manually tracked balances. And it will return an overview of all queried balances. This also includes any debt/liabilities.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/balances/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": true}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.
   :reqjson bool save_data: Boolean denoting whether to force save data even if the balance save frequency has not lapsed (see `here <balance_save_frequency_>`_ ).
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
                   "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {
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

.. http:get:: /api/(version)/assets/all

   Doing a GET on the all assets endpoint will return a mapping of all supported assets and their details. The keys are the unique symbol identifier and the values are the details for each asset.

The details of each asset can contain the following keys:

- **type**: The type of asset. Valid values are ethereum token, own chain, omni token and more. For all valid values check here: https://github.com/rotki/rotki/blob/develop/rotkehlchen/assets/resolver.py#L7
- **started**: An optional unix timestamp denoting where we know price data for the asset started
- **name**: The long name of the asset. Does not need to be the same as the unique symbol identifier
- **forked**: An optional attribute representing another asset out of which this asset forked from. For example ``ETC`` would have ``ETH`` here.
- **swapped_for**: An optional attribute representing another asset for which this asset was swapped for. For example ``VEN`` tokens were at some point swapped for ``VET`` tokens.
- **symbol**: The symbol used for this asset. This is not guaranteed to be unique. Unfortunately some assets use the same symbol as others.
- **ethereum_address**: If the type is ``ethereum_token`` then this will be the hexadecimal address of the token's contract.
- **ethereum_token_decimals**: If the type is ``ethereum_token`` then this will be the number of decimals the token has
- **cryptocompare**: The cryptocompare identifier for the asset. can be missing if not known. If missing the symbol is attempted to be queried.
- **coingecko**: The coingecko identifier for the asset. can be missing if not known.
- **protocol**: An optional string for ethereum tokens denoting the protocol they belong to. For example uniswap, for uniswap LP tokens.
- **underlying_tokens**: Optional. If the token is an LP token or a token set or something similar which represents a pool of multiple other tokens, then this is a list of the underlying token addresses and a percentage that each token contributes to the pool.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/all HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "_ceth_0xB6eD7644C69416d67B522e20bC294A9a9B405B31": {
                  "ethereum_address": "0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
                  "ethereum_token_decimals": 8,
                  "name": "0xBitcoin",
                  "started": 1517875200,
                  "symbol": "0xBTC",
                  "type": "ethereum token"
              },
              "DCR": {
                  "name": "Decred",
                  "started": 1450137600,
                  "symbol": "DCR",
                  "type": "own chain"
              },
              "_ceth_0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38": {
                  "ethereum_address": "0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38",
                  "ethereum_token_decimals": 18,
                  "name": "DigitalDevelopersFund",
                  "started": 1498504259,
                  "symbol": "DDF",
                  "type": "ethereum token"
              },
              "ETC": {
                  "forked": "ETH",
                  "name": "Ethereum classic",
                  "started": 1469020840,
                  "symbol": "ETC",
                  "type": "own chain"
              },
              "KRW": {
                  "name": "Korean won",
                  "symbol": "KRW",
                  "type": "fiat"
              },
              "_ceth_0xD850942eF8811f2A866692A623011bDE52a462C1": {
                  "ethereum_address": "0xD850942eF8811f2A866692A623011bDE52a462C1",
                  "ethereum_token_decimals": 18,
                  "name": "Vechain Token",
                  "started": 1503360000,
                  "swapped_for": "VET",
                  "symbol": "VEN",
                  "type": "ethereum token",
		  "coingecko": "vechain"
              },
          },
          "message": ""
      }


   :resjson object result: A mapping of asset symbol identifiers to asset details
   :statuscode 200: Assets succesfully queried.
   :statuscode 500: Internal rotki error

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
   :statuscode 200: Assets succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error

Getting custom ethereum tokens
==================================

.. http:get:: /api/(version)/assets/ethereum

   Doing a GET on the ethereum assets endpoint will return a list of all custom ethereum tokens. You can also optionally specify an ethereum address to get its token details. If you query by address only a single object is returned. If you query without, a list of objects.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/ethereum HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"address": "0x1169C72f36A843cD3a3713a76019FAB9503B2807"}

   :reqjson string address: An optional address to query for ethereum token info. If given only token info of this address are returned. As an object. **not a list**. If not given, a list of all known tokens is returned.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [{
              "identifier": "_ceth_0x1169C72f36A843cD3a3713a76019FAB9503B2807",
              "address": "0x1169C72f36A843cD3a3713a76019FAB9503B2807",
              "decimals": 18,
              "name": "foo",
              "symbol": "FTK",
              "started": 1614636432,
              "swapped_for": "SCT",
              "coingecko": "foo-coin",
              "cryptocompare": "FOO",
              "protocol": "uniswap",
              "underlying_tokens": [
                  {"address": "0x4a363BDcF9C139c0B77d929C8c8c5f971a38490c", "weight": "15.45"},
                  {"address": "0xf627B24754583896AbB6376b1e231A3B26d86c99", "weight": "35.65"},
                  {"address": "0x2B18982803EF09529406e738f344A0c1A54fA1EB", "weight": "39"}
              ]
          }, {
              "address": "0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e",
              "decimals": 4
          }],
          "message": ""
      }

   .. _custom_ethereum_token:

   :resjson list result: A list of ethereum tokens
   :resjsonarr string identifier: The rotki identifier of the token. This is only returned from the GET endpoint and not input from the add/edit one.
   :resjsonarr string address: The address of the token. Can not be optional.
   :resjsonarr integer decimals: Ethereum token decimals. Can be missing if not known.
   :resjsonarr string name: Asset name. Can be missing if not known.
   :resjsonarr string symbol: Asset symbol. Can be missing if not known.
   :resjsonarr integer started: The timestamp of the token deployment. Can be missing if not known.
   :resjsonarr string swapped_for: If this token was swapped for another one then here we would have the identifier of that other token. If not this is null.
   :resjsonarr string coingecko: The coingecko identifier for the asset. can be missing if not known.
   :resjsonarr string cryptocompare: The cryptocompare identifier for the asset. can be missing if not known.
   :resjsonarr string protocol: A name for the protocol the token belongs to. For example uniswap for all uniswap LP tokens. Can be missing if not known or there is no protocol the token belongs to.
   :resjsonarr list underlying_tokens: Optional. If the token is an LP token or a token set or something similar which represents a pool of multiple other tokens, then this is a list of the underlying token addresses and a percentage that each token contributes to the pool.
   :statuscode 200: Assets succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 404: Queried by address and no token was found.
   :statuscode 500: Internal rotki error

Adding custom ethereum tokens
==================================

.. http:put:: /api/(version)/assets/ethereum

   Doing a PUT on the ethereum assets endpoint will allow you to add a new ethereum token in the global rotki DB. Returns the asset identifier of the new custom token. For ethereum ones it's ``_ceth_0xADDRESS``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/ethereum HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"token": {
          "address": "0x1169C72f36A843cD3a3713a76019FAB9503B2807",
          "decimals": 18,
          "name": "foo",
          "symbol": "FTK",
          "started": 1614636432,
          "swapped_for": "SCT",
          "coingecko": "foo-coin",
          "cryptocompare": "FOO",
          "protocol": "uniswap",
          "underlying_tokens": [
              {"address": "0x4a363BDcF9C139c0B77d929C8c8c5f971a38490c", "weight": "15.45"},
                  {"address": "0xf627B24754583896AbB6376b1e231A3B26d86c99", "weight": "35.65"},
                  {"address": "0x2B18982803EF09529406e738f344A0c1A54fA1EB", "weight": "39"}
         ]
       }}

   :reqjson object token: A token to add. For details on the possible fields see `here <custom_ethereum_token_>`_.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"identifier": "_ceth_0x1169C72f36A843cD3a3713a76019FAB9503B2807"},
          "message": ""
      }


   :resjson string identifier: The identifier of the newly added token.
   :statuscode 200: Asset succesfully addedd.
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
          "result": {"identifier": "_ceth_0x1169C72f36A843cD3a3713a76019FAB9503B2807"},
          "message": ""
      }


   :resjson string identifier: The identifier of the edited token.
   :statuscode 200: Asset succesfully edited.
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
   :statuscode 200: Asset succesfully deleted.
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
   :statuscode 200: Asset types succesfully queries
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
   :statuscode 200: Asset succesfully addedd.
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


   :statuscode 200: Asset succesfully edited.
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


   :statuscode 200: Asset succesfully deleted.
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
   :statuscode 200: Pending asset updates information is succesfully queried
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
	      "_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015": "local",
	      "_ceth_0xD178b20c6007572bD1FD01D205cC20D32B4A6015": "remote",
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
   :statuscode 200: Update was succesfully applied (if any).
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Conflicts were found during update. The conflicts should also be returned.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error while trying to reach the remote for asset updates.

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

   :statuscode 200: Asset succesfully replaced.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Some conflict at replacing or user is not loggged in.
   :statuscode 500: Internal rotki error

Querying asset icons
======================

.. http:get:: /api/(version)/assets/(identifier)/icon

   Doing a GET on the asset icon endpoint will return the icon of the given asset.
   If we have no icon for an asset a 404 is returned.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e/icon HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: image/png

   :result: The data of the image
   :statuscode 200: Icon succesfully queried
   :statuscode 304: Icon data has not changed. Should be cached on the client. This is returned if the given If-Match or If-None-Match header match the etag of the previous response.
   :statuscode 400: Provided JSON is in some way malformed. Either unknown asset or invalid size.
   :statuscode 404: We have no icon for that asset
   :statuscode 500: Internal rotki error


Uploading custom asset icons
===============================

.. http:put:: /api/(version)/assets/(identifier)/icon
.. http:post:: /api/(version)/assets/(identifier)/icon

   Doing either a PUT or a POST on the asset icon endpoint with appropriate arguments will upload a custom icon for an asset. That icon will take precedence over what rotki already knows for the asset if anything.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/ACUSTOMICON/icon/large HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"file": "/path/to/file"}

   :reqjson string file: The path to the image file to upload for PUT. The file itself for POST.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {"result": {"identifier": "_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96"}, "message": ""}

   :resjson strin identifier: The identifier of the asset for which the icon was uploaded.
   :statuscode 200: Icon succesfully uploaded
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
   :statuscode 200: Netvalue statistics succesfuly queried.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 500: Internal rotki error.

Statistics for asset balance over time
======================================

.. http:get:: /api/(version)/statistics/balance/(asset identifier)

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the statistics asset balance over time endpoint will return all saved balance entries for an asset. Optionally you can filter for a specific time range by providing appropriate arguments.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/balance/BTC HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1514764800, "to_timestamp": 1572080165}

   :reqjson int from_timestamp: The timestamp after which to return saved balances for the asset. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return saved balances for the asset. If not given all balances until now are returned.
   :param int from_timestamp: The timestamp after which to return saved balances for the asset. If not given zero is considered as the start.
   :param int to_timestamp: The timestamp until which to return saved balances for the asset. If not given all balances until now are returned.

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

   :statuscode 200: Single asset balance statistics succesfuly queried
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

   :statuscode 200: Value distribution succesfully queried.
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

   :statuscode 200: Value distribution succesfully queried.
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
   :statuscode 200: Rendering code succesfully returned.
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

   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string location: Optionally filter trades by location. A valid location name has to be provided. If missing location filtering does not happen.
   :param int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :param int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :param string location: Optionally filter trades by location. A valid location name has to be provided. If missing location filtering does not happen.
   :param bool only_cache: Optional.If this is true then the equivalent exchange/location is not queried, but only what is already in the DB is returned.

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
              "entries_limit": 250,
          "message": ""
      }

   :resjson object entries: An array of trade objects and their metadata. Each entry is composed of the main trade entry under the ``"entry"`` key and other metadata like ``"ignored_in_accounting"`` for each trade.
   :resjsonarr string trade_id: The uniquely identifying identifier for this trade.
   :resjsonarr int timestamp: The timestamp at which the trade occured
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
   :resjson int entries_found: The amount of trades found for the user. That disregards the filter and shows all trades found.
   :resjson int entries_limit: The trades limit for the account tier of the user. If unlimited then -1 is returned.
   :statuscode 200: Trades are succesfully returned
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

   :reqjson int timestamp: The timestamp at which the trade occured
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
   :statuscode 200: Trades was succesfully added.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error

.. http:patch:: /api/(version)/trades

   Doing a PATCH on this endpoint edits an existing trade in rotki's currently logged in user using the ``trade_id``.

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

   :reqjson string trade_id: The ``trade_id`` of the trade to edit
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

   :resjson object result: A trade with the same schema as seen in `this <trades_schema_section_>`_ section.
   :statuscode 200: Trades was succesfully edited.
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

   :resjson bool result: Boolean indicating succes or failure of the request.
   :statuscode 200: Trades was succesfully deleted.
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

   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string location: Optionally filter trades by location. A valid location name has to be provided. Valid locations are for now only exchanges for deposits/widthrawals.
   :param bool only_cache: Optional. If this is true then the equivalent exchange/location is not queried, but only what is already in the DB is returned.


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
              "entries_limit": 100,
          "message": ""
      }

   :resjson object entries: An array of deposit/withdrawal objects and their metadata. Each entry is composed of the main movement entry under the ``"entry"`` key and other metadata like ``"ignored_in_accounting"`` for each asset movement.
   :resjsonarr string identifier: The uniquely identifying identifier for this asset movement
   :resjsonarr string location: A valid location at which the deposit/withdrawal occured
   :resjsonarr string category: Either ``"deposit"`` or ``"withdrawal"``
   :resjsonarr string address: The source address if this is a deposit or the destination address if this is a withdrawal.
   :resjsonarr string transaction_id: The transaction id
   :resjsonarr integer timestamp: The timestamp at which the deposit/withdrawal occured
   :resjsonarr string asset: The asset deposited or withdrawn
   :resjsonarr string amount: The amount of asset deposited or withdrawn
   :resjsonarr string fee_asset: The asset in which ``fee`` is denominated in
   :resjsonarr string fee: The fee that was paid, if anything, for this deposit/withdrawal
   :resjsonarr string link: Optional unique exchange identifier for the deposit/withdrawal
   :resjson int entries_found: The amount of deposit/withdrawals found for the user. That disregards the filter and shows all asset movements found.
   :resjson int entries_limit: The movements query limit for the account tier of the user. If unlimited then -1 is returned.
   :statuscode 200: Deposits/withdrawals are succesfully returned
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

   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string location: Optionally filter actions by location. A valid location name has to be provided. If missing location filtering does not happen.
   :param int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :param int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :param string location: Optionally filter actions by location. A valid location name has to be provided. If missing location filtering does not happen.

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
                      "asset": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
		      "rate": "0.85",
		      "rate_asset": "EUR",
                      "link": "https://etherscan.io/tx/0xea5594ad7a1e552f64e427b501676cbba66fd91bac372481ff6c6f1162b8a109"
                      "notes": "The DAI I lost in the pickle finance hack"
                  },
                  "ignored_in_accounting": false
              }],
              "entries_found": 1,
              "entries_limit": 50,
          "message": ""
      }

   :resjson object entries: An array of action objects and their metadata. Each entry is composed of the ledger action entry under the ``"entry"`` key and other metadata like ``"ignored_in_accounting"`` for each action.
   :resjsonarr int identifier: The uniquely identifying identifier for this action.
   :resjsonarr int timestamp: The timestamp at which the action occured
   :resjsonarr string action_type: The type of action. Valid types are: ``income``, ``loss``, ``donation received``, ``expense`` and ``dividends income``.
   :resjsonarr string location: A valid location at which the action happened.
   :resjsonarr string amount: The amount of asset for the action
   :resjsonarr string asset: The asset for the action
   :resjsonarr string rate: Optional. If given then this is the rate in ``rate_asset`` for the ``asset`` of the action.
   :resjsonarr string rate_asset: Optional. If given then this is the asset for which ``rate`` is given.
   :resjsonarr string link: Optional unique identifier or link to the action. Can be an empty string
   :resjsonarr string notes: Optional notes about the action. Can be an empty string
   :resjson int entries_found: The amount of actions found for the user. That disregards the filter and shows all actions found.
   :resjson int entries_limit: The actions limit for the account tier of the user. If unlimited then -1 is returned.
   :statuscode 200: Actions are succesfully returned
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

   :resjson object result: The identifier ofthe newly created ledger action
   :statuscode 200: Ledger action was succesfully added.
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
   :statuscode 200: Actions was succesfully edited.
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

      {"identifier" : 55}

   :reqjson integer identifier: The ``identifier`` of the action to delete.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "entries": [{
                  "entry": {
                      "identifier": 35,
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

   :resjson object entries: An array of action objects after deletion. Same schema as the get method.
   :resjson int entries_found: The amount of actions found for the user. That disregards the filter and shows all actions found.
   :resjson int entries_limit: The actions limit for the account tier of the user. If unlimited then -1 is returned.
   :statuscode 200: Action was succesfully removed.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal rotki error

Querying messages to show to the user
=====================================

.. http:get:: /api/(version)/messages/

   Doing a GET on the messages endpoint will pop all errors and warnings from the message queue and return them. The message queue is a queue where all errors and warnings that are supposed to be see by the user are saved and are supposed to be popped and read regularly.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/messages/ HTTP/1.1
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

   :statuscode 200: Messages popped and read succesfully.
   :statuscode 500: Internal rotki error.

Querying complete action history
================================

.. http:get:: /api/(version)/history/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the history endpoint will trigger a query and processing of the history of all actions (trades, deposits, withdrawals, loans, eth transactions) within a specific time range. Passing them as a query arguments here would be given as: ``?async_query=true&from_timestamp=1514764800&to_timestamp=1572080165``.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history/ HTTP/1.1
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
          "result": {
              "overview": {
                  "loan_profit": "1500",
                  "defi_profit_loss": "140",
                  "ledger_actions_profit_loss": "1500",
                  "margin_positions_profit_loss": "500",
                  "settlement_losses": "200",
                  "ethereum_transaction_gas_costs": "2.5",
                  "asset_movement_fees": "3.45",
                  "general_trade_profit_loss": "5002",
                  "taxable_trade_profit_loss": "5002",
                  "total_taxable_profit_loss": "6936.05",
                  "total_profit_loss": "6936.05"
              },
              "events_processed": 1000,
              "events_limit": 1000,
              "first_processed_timestamp": 1428994442,
              "all_events": [{
                  "type": "buy",
                  "paid_in_profit_currency": "4000",
                  "paid_asset": "BTC",
                  "paid_in_asset": "0.5",
                  "taxable_amount": "not applicable",
                  "taxable_bought_cost_in_profit_currency": "not applicable",
                  "received_asset": "ETH",
                  "taxable_received_in_profit_currency": "0",
                  "received_in_asset": "24",
                  "net_profit_or_loss": "0",
                  "time": 1514765800,
                  "cost_basis": null,
                  "is_virtual": false
              }, {
                  "type": "sell",
                  "paid_in_profit_currency": "0",
                  "paid_asset": "BTC",
                  "paid_in_asset": "0.2",
                  "taxable_amount": "0.1",
                  "taxable_bought_cost_in_profit_currency": "600",
                  "received_asset": "EUR",
                  "taxable_received_in_profit_currency": "800",
                  "received_in_asset": "1600",
                  "net_profit_or_loss": "200",
                  "time": 1524865800,
                  "cost_basis": {
                      "is_complete": true,
                      "matched_acquisitions": [{
                          "time": 15653231,
                          "description": "trade",
                          "location": "kraken",
                          "used_amount": "0.1",
                          "amount": "1",
                          "rate": "500",
                          "fee_rate": "0.1",
                      }, {
                          "time": 15654231,
                          "description": "trade",
                          "location": "bittrex",
                          "used_amount": "0.1",
                          "amount": "1",
                          "rate": "550",
                          "fee_rate": "0",
                      }]
                  },
                  "is_virtual": false
              }],
          },
          "message": ""
      }

   The overview part of the result is a dictionary with the following keys:

   :resjson str loan_profit: The profit from loans inside the given time period denominated in the user's profit currency.
   :resjson str defi_profit_loss: The profit/loss from Decentralized finance events inside the given time period denominated in the user's profit currency.
   :resjson str ledger_actions_profit_loss: The profit/loss from all the manually input ledger actions. Income, loss, expense and more.
   :resjson str margin_positions_profit_loss: The profit/loss from margin positions inside the given time period denominated in the user's profit currency.
   :resjson str settlement_losses: The losses from margin settlements inside the given time period denominated in the user's profit currency.
   :resjson str ethereum_transactions_gas_costs: The losses from ethereum gas fees inside the given time period denominated in the user's profit currency.
   :resjson str asset_movement_fees: The losses from exchange deposit/withdral fees inside the given time period denominated in the user's profit currency.
   :resjson str general_trade_profit_loss: The profit/loss from all trades inside the given time period denominated in the user's profit currency.
   :resjson str taxable_trade_profit_loss: The portion of the profit/loss from all trades that is taxable and is inside the given time period denominated in the user's profit currency.
   :resjson str total_taxable_profit_loss: The portion of all profit/loss that is taxable and is inside the given time period denominated in the user's profit currency.
   :resjson str total_profit_loss: The total profit loss inside the given time period denominated in the user's profit currency.
   :resjson int events_processed: The total number of events processed. This also includes events in the past which are not exported due to the requested PnL range.
   :resjson int events_limit: The limit of the events for the user's tier. -1 stands for unlimited. If the limit is hit then the event processing stops and only all events and PnL calculation up to the limit is returned.
   :resjson int first_processed_timestamp: The timestamp of the very first event processed. This can be before the query period since we always query from the beginning of history to have a full cost basis.

   The all_events part of the result is a list of events with the following keys:

   :resjson str type: The type of event. Can be one of ``"buy"``, ``"sell"``, ``"tx_gas_cost"``, ``"asset_movement"``, ``"loan_settlement"``, ``"interest_rate_payment"``, ``"margin_position_close"``
   :resjson str paid_in_profit_currency: The total amount paid for this action in the user's profit currency. This will always be zero for sells and other actions that only give profit.
   :resjson str paid_asset: The asset that was paid for in this action.
   :resjson str paid_in_asset: The amount of ``paid_asset`` that was used in this action.
   :resjson str taxable_amount: For sells and other similar actions this is the part of the ``paid_in_asset`` that is considered taxable. Can differ for jurisdictions like Germany where after a year of holding trades are not taxable. For buys this will have the string ``"not applicable"``.
   :resjson str taxable_bought_cost_in_profit_currency: For sells and other similar actions this is the part of the ``paid_in_asset`` that is considered taxable. Can differ for jurisdictions like Germany where after a year of holding trades are not taxable. For buys this will have the string ``"not applicable"``.
   :resjson str received_asset: The asset that we received from this action. For buys this is the asset that we bought and for sells the asset that we got by selling.
   :resjson str taxable_received_in_profit_currency: The taxable portion of the asset that we received from this action in profit currency. Can be different than the price of ``received_in_asset`` in profit currency if not the entire amount that was exchanged was taxable. For buys this would be 0.
   :resjson str received_in_asset: The amount of ``received_asset`` that we received from this action.
   :resjson str net_profit_or_loss: The net profit/loss from this action denoted in profit currency.
   :resjson int time: The timestamp this action took place in.
   :resjson bool is_virtual: A boolean denoting whether this is a virtual action. Virtual actions are special actions that are created to make accounting for crypto to crypto trades possible. For example, if you sell BTC for ETH a virtual trade to sell BTC for EUR and then a virtual buy to buy BTC with EUR will be created.
   :resjson object cost_basis: An object describing the cost basis of the event if it's a spend event. Contains a boolean attribute ``"is_complete"`` to denoting if we have complete cost basis information for the spent asset or not. If not then this means that rotki does not know enough to properly calculate cost basis. The other attribute is ``"matched_acquisitions"`` a list of matched acquisition events from which the cost basis is calculated. Each event has ``"time"``, ``"description"``, ``"location"`` attributes which are self-explanatory. Then it also has the ``"amount"`` which is the amount that was acquired in that event and the ``"used_amount"`` which is how much of that is used in this spend action. Then there is the ``"rate"`` key which shows the rate in the profit currency with which 1 unit of the asset was acquired at the event. And finally the ``"fee_rate"`` denoting how much of the profit currency was paid for each unit of the asset bought.

   :statuscode 200: History processed and returned succesfully
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in.
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

   :resjson bool result: Boolean denoting succes or failure of the query
   :statuscode 200: File were exported succesfully
   :statuscode 400: Provided JSON is in some way malformed or given string is not a directory.
   :statuscode 409: No user is currently logged in. No history has been processed. No permissions to write in the given directory. Check error message.
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
   :statuscode 200: Data were queried succesfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.

Querying periodic data
======================

.. http:get:: /api/(version)/periodic/


   Doing a GET on the periodic data endpoint will return data that would be usually frequently queried by an application. Check the example response to see what these data would be.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/periodict/ HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "last_balance_save": 1572345881,
              "eth_node_connection": true,
              "last_data_upload_ts": 0
          }
          "message": ""
      }

   :resjson int last_balance_save: The last time (unix timestamp) at which balances were saved in the database.
   :resjson bool eth_node_connection: A boolean denoting if the application is connected to an ethereum node. If ``false`` that means we fall back to etherscan.
   :statuscode 200: Data were queried succesfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.


Getting blockchain account data
===============================
.. http:get:: /api/(version)/blockchains/(name)/

   .. note::
      Supported blockchains: ``"BTC", "ETH", "KSM"``

   Doing a GET on the blokchcains endpoint with a specific blockchain queries account data information for that blockchain.

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
   :resjsonarr string address: The address, which is the unique identifier of each account. For BTC blockchain query and if the entry is an xpub then this attribute is misssing.
   :resjsonarr string xpub: The extended public key. This attribute only exists for BTC blockchain query and if the entry is an xpub
   :resjsonarr string label: The label to describe the account. Can also be null.
   :resjsonarr list tags: A list of tags associated with the account. Can also be null.

   :statuscode 200: Account data succesfully queried.
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

   :statuscode 200: Account data succesfully queried.
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
   :resjsonarr string underlying_balances: A list of underlying DefiBalances supporting the base balance. Can also be an empty list. The format of each balance is thesame as that of base_balance. For lending this is going to be the normal token. For example for aDAI this is DAI. For cBAT this is BAT etc. For pools this list contains all tokens that are contained in the pool.

   :statuscode 200: Balances succesfully queried.
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

   :statuscode 200: DSR succesfully queried.
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
   :resjsonarr int block_number: The block number at which the deposit or withdrawal occured.
   :resjsonarr int tx_hash: The transaction hash of the DSR movement

   :statuscode 200: DSR history succesfully queried.
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
              "collateral_asset": "_ceth_0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
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
   :statuscode 200: Vaults succesfuly queried
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
              "collateral_asset": "_ceth_0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
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
   :resjson object events: A list of all events that occured for this vault
   :resjsonarr string event_type: The type of the event. Valid types are: ``["deposit", "withdraw", "generate", "payback", "liquidation"]``
   :resjsonarr string value: The amount/usd_value associated with the event. So collateral deposited/withdrawn, debt generated/paid back, amount of collateral lost in liquidation.
   :resjsonarr int timestamp: The unix timestamp of the event
   :resjsonarr string tx_hash: The transaction hash associated with the event.

   :statuscode 200: Vault details succesfuly queried
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
                      "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                          "balance": {
                              "amount": "350.0",
                              "usd_value": "351.21"
                          },
                          "apy": "3.51%"
                      },
                      "_ceth_0xdd974D5C2e2928deA5F71b9825b8b646686BD200": {
                          "balance": {
                              "amount": "220.21",
                              "usd_value": "363.3465"
                          },
                          "apy": "0.53%"
                      },
                  },
                  "borrowing": {
                      "_ceth_0x80fB784B7eD66730e8b1DBd9820aFD29931aab03": {
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
                      "_ceth_0x0D8775F648430679A709E98d2b0Cb6250d2887EF": {
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

   :statuscode 200: Aave balances succesfully queried.
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
                      "asset": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
                      "atoken": "_ceth_0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d",
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
                      "asset": "_ceth_0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d",
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
                      "asset": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
                      "atoken": "_ceth_0xfC1E690f61EFd961294b3e1Ce3313fBD8aa4f85d",
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
                      "asset": "_ceth_0xE41d2489571d322189246DaFA5ebDe1F4699F498",
                      "atoken": "_ceth_0x6Fb0855c404E09c47C3fBCA25f08d4E41f9F062f",
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
                      "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                          "amount": "0.9482",
                          "usd_value": "1.001"
                      },
                      "_ceth_0xE41d2489571d322189246DaFA5ebDe1F4699F498": {
                          "amount": "0.523",
                          "usd_value": "0.0253"
                      }
                  },
                  "total_lost": {
                      "_ceth_0xFC4B8ED459e00e5400be803A9BB3954234FD50e3": {
                          "amount": "0.3212",
                          "usd_value": "3560.32"
                      }
                  }
              },
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                  "events": [{
                      "event_type": "deposit",
                      "asset": "_ceth_0x0D8775F648430679A709E98d2b0Cb6250d2887EF",
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
                      "_ceth_0x0D8775F648430679A709E98d2b0Cb6250d2887EF": {
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
   :resjsonarr int timestamp: The unix timestamp at which the event occured.
   :resjsonarr int block_number: The block number at which the event occured. If the graph is queried this is unfortunately always 0, so UI should not show it.
   :resjsonarr string tx_hash: The transaction hash of the event.
   :resjsonarr int log_index: The log_index of the event. For the graph this is indeed a unique number in combination with the transaction hash, but it's unfortunately not the log index.
   :resjsonarr string asset: This attribute appears in all event types except for ``"liquidation"``. It shows the asset that this event is about. This can only be an underlying asset of an aToken.
   :resjsonarr string atoken: This attribute appears in ``"deposit"`` and ``"withdrawals"``. It shows the aToken involved in the event.
   :resjsonarr object value: This attribute appears in all event types except for ``"liquidation"``. The value (amount and usd_value mapping) of the asset for the event. The rate is the asset/USD rate at the events's timestamp.
   :resjsonarr string borrow_rate_mode: This attribute appears only in ``"borrow"`` events. Signifies the type of borrow. Can be either ``"stable"`` or ``"variable"``.
   :resjsonarr string borrow_rate: This attribute appears only in ``"borrow"`` events. Shows the rate at which the asset was borrowed. It's a floating point number. For example ``"0.155434"`` would means 15.5434% interest rate for this borrowing.
   :resjsonarr string accrued_borrow_interest: This attribute appears only in ``"borrow"`` events. Its a floating point number showing the acrrued interest for borrowing the asset so far
   :resjsonarr  object fee: This attribute appears only in ``"repay"`` events. The value (amount and usd_value mapping) of the fee for the repayment. The rate is the asset/USD rate at the events's timestamp.
   :resjsonarr string collateral_asset: This attribute appears only in ``"liquidation"`` events. It shows the collateral asset that the user loses due to liquidation.
   :resjsonarr string collateral_balance: This attribute appears only in ``"liquidation"`` events. It shows the value (amount and usd_value mapping) of the collateral asset that the user loses due to liquidation. The rate is the asset/USD rate at the events's timestamp.
   :resjsonarr string principal_asset: This attribute appears only in ``"liquidation"`` events. It shows the principal debt asset that is repaid due to the liquidation due to liquidation.
   :resjsonarr string principal_balance: This attribute appears only in ``"liquidation"`` events. It shows the value (amount and usd_value mapping) of the principal asset whose debt is repaid due to liquidation. The rate is the asset/USD rate at the events's timestamp.
   :resjson object total_earned_interest: A mapping of asset identifier to total earned (amount + usd_value mapping) for each asset's interest earnings. The total earned is essentially the sum of all interest payments plus the difference between ``balanceOf`` and ``principalBalanceOf`` for each asset.
   :resjson object total_lost: A mapping of asset identifier to total lost (amount + usd_value mapping) for each asset. The total losst for each asset is essentially the accrued interest from borrowing and the collateral lost from liquidations.
   :resjson object total_earned_liquidations: A mapping of asset identifier to total earned (amount + usd_value mapping) for each repaid assets during liquidations.

   :statuscode 200: Aave history succesfully queried.
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

   :statuscode 200: AdEx balances succesfully queried.
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
                        "token": "_ceth_0xADE00C28244d5CE17D72E40330B1c318cD12B7c3",
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
                        "token": "_ceth_0xADE00C28244d5CE17D72E40330B1c318cD12B7c3",
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

   :statuscode 200: AdEx events history succesfully queried.
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
                  "token": "_ceth_0xFC4B8ED459e00e5400be803A9BB3954234FD50e3",
                  "total_amount": "2326.81686488",
                  "user_balance": {
                    "amount": "331.3943886097855861540937492",
                    "usd_value": "497.0915829146783792311406238"
                  },
                  "usd_price": "1.5",
                  "weight": "50"
                },
                {
                  "token": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
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
                  "token": "_ceth_0x2ba592F78dB6436527729929AAf6c908497cB200",
                  "total_amount": "3728.283461100135483274",
                  "user_balance": {
                    "amount": "3115.861971106915456546519315",
                    "usd_value": "4673.792956660373184819778972"
                  },
                  "usd_price": "1.5",
                  "weight": "75.0"
                },
                {
                  "token": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
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

   :statuscode 200: Balancer balances succesfully queried.
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
                      { "token": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "weight": "20" },
                      { "token": "_ceth_0xba100000625a3754423978a60c9317c58a424e3D", "weight": "80" }
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
                          "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "0.05",
                          "_ceth_0xba100000625a3754423978a60c9317c58a424e3D": "0"
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
                          "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "0.010687148200906598",
                          "_ceth_0xba100000625a3754423978a60c9317c58a424e3D": "0.744372160905819159"
                        }
                      }
                    ],
                    "profit_loss_amounts": {
                      "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2": "-0.039312851799093402",
                      "_ceth_0xba100000625a3754423978a60c9317c58a424e3D": "0.744372160905819159"
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

   :statuscode 200: Balancer events succesfully queried.
   :statuscode 409: User is not logged in. Or Balancer module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as the graph node could not be reached or returned unexpected response.

Getting Balancer trades
=========================

.. http:get:: /api/(version)/blockchains/ETH/modules/balancer/history/trades

   Doing a GET on the Balancer trades history resource will return the history of all Balancer trades.

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/balancer/history/trades HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "0x029f388aC4D5C8BfF490550ce0853221030E822b": [
                {
                    "address": "0x029f388aC4D5C8BfF490550ce0853221030E822b",
                    "amount": "0.075627332013165531",
                    "base_asset": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                    "fee": "0",
                    "fee_currency": "_ceth_0x4a220E6096B25EADb88358cb44068A3248254675",
                    "location": "balancer",
                    "quote_asset": "_ceth_0x4a220E6096B25EADb88358cb44068A3248254675",
                    "rate": "0.02194014031410883771422129499",
                    "swaps": [
                        {
                            "amount0_in": "3.446984883890308608",
                            "amount0_out": "0",
                            "amount1_in": "0",
                            "amount1_out": "0.075627332013165531",
                            "from_address": "0x0000000000007F150Bd6f54c40A34d7C3d5e9f56",
                            "log_index": 37,
                            "to_address": "0x6545773483142Fd781023EC74ee008d93aD5466B",
                            "token0": "_ceth_0x4a220E6096B25EADb88358cb44068A3248254675",
                            "token1": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                            "tx_hash": "0x9a5c2c73762ef2e8af326e7b286488a4b238b9855d3fd749370bb3074aabf6e5"
                        }
                    ],
                    "timestamp": 1606924530,
                    "trade_id": "0x9a5c2c73762ef2e8af326e7b286488a4b238b9855d3fd749370bb3074aabf6e5-0",
                    "trade_type": "buy",
                    "tx_hash": "0x9a5c2c73762ef2e8af326e7b286488a4b238b9855d3fd749370bb3074aabf6e5"
                },
                {
                    "address": "0x029f388aC4D5C8BfF490550ce0853221030E822b",
                    "amount": "3.214606868598057153",
                    "base_asset": "_ceth_0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
                    "fee": "0",
                    "fee_currency": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                    "location": "balancer",
                    "quote_asset": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                    "rate": "1.068431955314709719236410104",
                    "swaps": [
                        {
                            "amount0_in": "3.008714642619599872",
                            "amount0_out": "0",
                            "amount1_in": "0",
                            "amount1_out": "3.214606868598057153",
                            "from_address": "0x0000000000007F150Bd6f54c40A34d7C3d5e9f56",
                            "log_index": 334,
                            "to_address": "0x987D7Cc04652710b74Fff380403f5c02f82e290a",
                            "token0": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                            "token1": "_ceth_0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
                            "tx_hash": "0xe8f02a2c1105a0dd093d6bff6983bbc6ac662424e116fe4d53ea4f2fd4d36497"
                        }
                    ],
                    "timestamp": 1606921757,
                    "trade_id": "0xe8f02a2c1105a0dd093d6bff6983bbc6ac662424e116fe4d53ea4f2fd4d36497-0",
                    "trade_type": "buy",
                    "tx_hash": "0xe8f02a2c1105a0dd093d6bff6983bbc6ac662424e116fe4d53ea4f2fd4d36497"
                }
            ]
        },
        "message": "",
      }

   :resjson object result: A mapping between accounts and their Balancer trades history
   :resjson string address: The address of the user who initiated the trade
   :resjson object base_asset: Either an identifier if it's a known token or the address/symbol/name object for the base asset of the trade. That which is bought.
   :resjson object quote_asset: Either an identifier if it's a known token or the address/symbol/name object for the quote asset of the trade. That which is sold to buy the base asset.
   :resjson string amount: In case of a trade_type buy (and for Balancer all are buys) this is the amount of ``"base_asset"`` that is bought.
   :resjson string rate: How much of each quote asset was given for the base asset amount. Essentially ``"amount"`` / ``"rate"`` will give you what you paid in ``"quote_asset"``.
   :resjson string location: Always balancer.
   :resjson string fee: Always 0 for now.
   :resjson string fee_currency: Always quote_asset.
   :resjson int timestamp: The timestamp of the trade
   :resjson string trade_id: A combination of transaction hash plus a unique id (for custom trades that are virtually made by us)
   :resjson string trade_type: Always buy
   :resjson string tx_hash: The transaction hash
   :resjson list[object] swaps: A list of all the swaps that the trade is made of. Each swap is an object with the following attributes:

       - token0: Either an identifier if it's a known token or the address/symbol/name object for token0 of the swap.
       - token1: Either an identifier if it's a known token or the address/symbol/name object for token1 of the swap.
       - amount0_in: The amount (can be zero) of token0 that the user is putting in the swap.
       - amount1_in: The amount (can be zero) of token1 that the user is putting in the swap.
       - amount0_out: The amount (can be zero) of token0 that the user is getting out of the swap.
       - amount1_out: The amount (can be zero) of token1 that the user is getting out of the swap.
       - from_address: The address that is putting tokens in the swap. Can be many different parties in a multi swap.
       - to_address: The address that is getting tokens out of the swap. Can be many different parties in a multi swap.
       - address: Always the same address of the user, associated with the trade the swaps belong to.
       - location: Always balancer.
       - tx_hash: The transaction hash of the swap (always the same for swaps of the same transaction/trade).
       - log_index: The index of the swap in the transaction/trade.

   :statuscode 200: Balancer trades succesfully queried.
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
                      "_ceth_0xc00e94Cb662C3520282E6f5717214004A7f26888": {
                          "balance" :{
                              "amount": "3.5",
                              "usd_value": "892.5",
                          }
                      }
                  },
                  "lending": {
                      "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                          "balance": {
                              "amount": "350.0",
                              "usd_value": "351.21"
                          },
                          "apy": "3.51%"
                      },
                      "_ceth_0xFC4B8ED459e00e5400be803A9BB3954234FD50e3": {
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
                      "_ceth_0x0D8775F648430679A709E98d2b0Cb6250d2887EF": {
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

   :statuscode 200: Compound balances succesfully queried.
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
                  "asset": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
                  "value": {
                      "amount": "10.5",
                      "usd_value": "10.86"
                  },
                  "to_asset": "_ceth_0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643",
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
                  "asset": "_ceth_0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643",
                  "value": {
                      "amount": "165.21",
                      "usd_value": "12.25"
                  },
                  "to_asset": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
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
                  "asset": "_ceth_0xE41d2489571d322189246DaFA5ebDe1F4699F498",
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
                  "asset": "_ceth_0xE41d2489571d322189246DaFA5ebDe1F4699F498",
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
                  "to_asset": "_ceth_0xE41d2489571d322189246DaFA5ebDe1F4699F498",
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
                  "asset": "_ceth_0xc00e94Cb662C3520282E6f5717214004A7f26888",
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
                      "_ceth_0xc00e94Cb662C3520282E6f5717214004A7f26888": {
                              "amount": "3.5",
                              "usd_value": "892.5",
                          },
                       "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {
                              "amount": "250",
                              "usd_value": "261.1",
                      }
                  },
                  "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                      "_ceth_0xE41d2489571d322189246DaFA5ebDe1F4699F498": {
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
                      "_ceth_0xc00e94Cb662C3520282E6f5717214004A7f26888": {
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
   :resjsonarr int timestamp: The unix timestamp at which the event occured.
   :resjsonarr int block_number: The block number at which the event occured.
   :resjsonarr string asset: The asset involved in the event.
       - For ``"mint"`` events this is the underlying asset.
       - For ``"redeem"`` events this is the cToken.
       - For ``"borrow"`` and ``"repay"`` events this is the borrowed asset
       - For ``"liquidation"`` events this is the part of the debt that was repaid by the liquidator.
       - For ``"comp"`` events this the COMP token.
   :resjsonarr object value: The value of the asset for the event. The rate is the asset/USD rate at the events's timestamp.
   :resjsonarr string to_asset: [Optional] The target asset involved in the event.
       - For ``"mint"`` events this is the cToken.
       - For ``"redeem"`` events this is the underlying asset.
       - For ``"borrow"`` and ``"repay"`` this is missing.
       - For ``"liquidation"`` events this is asset lost to the liquidator.
   :resjsonarr object to_value: [Optional] The value of the ``to_asset`` for the event. The rate is the asset/USD rate at the events's timestamp.
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

   :statuscode 200: Compound history succesfully queried.
   :statuscode 409: User is not logged in. Or compound module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting Uniswap balances
==============================

.. http:get:: /api/(version)/blockchains/ETH/modules/uniswap/balances

   Doing a GET on the uniswap balances resource will return the balances locked in Uniswap Liquidity Pools (LPs or pools).

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/uniswap/balances HTTP/1.1
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
                  "asset": "_ceth_0xdAC17F958D2ee523a2206206994597C13D831ec7",
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

   :statuscode 200: Uniswap balances succesfully queried.
   :statuscode 409: User is not logged in. Or Uniswap module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

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
                      "token0": "_ceth_0x0e2298E3B3390e3b945a5456fBf59eCc3f55DA16",
                      "token1": "_ceth_0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
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


   :statuscode 200: Uniswap events succesfully queried.
   :statuscode 409: User is not logged in. Or Uniswap module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting Uniswap trades
=========================

.. http:get:: /api/(version)/blockchains/ETH/modules/uniswap/history/trades

   Doing a GET on the uniswap trades history resource will return the history of all uniswap trades.

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/uniswap/history/trades HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "0x21d05071cA08593e13cd3aFD0b4869537e015C92": [{
              "address": "0x21d05071cA08593e13cd3aFD0b4869537e015C92",
              "amount": "1411.453463704718081611",
              "base_asset": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
              "fee": "0",
              "fee_currency": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
              "location": "uniswap",
              "quote_asset": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
              "rate": "371.4351220275573898976315789",
              "swaps": [{
                  "amount0_in": "0",
                  "amount0_out": "1411.453463704718081611",
                  "amount1_in": "3.8",
                  "amount1_out": "0",
                  "from_address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                  "log_index": 90,
                  "to_address": "0x21d05071cA08593e13cd3aFD0b4869537e015C92",
                  "token0": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
                  "token1": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                  "tx_hash": "0xf6272151d26f391886232263a384d1d9fb84c54e33119d014bc0b556dc27e900"}],
              "timestamp": 1603056982,
              "trade_id": "0xf6272151d26f391886232263a384d1d9fb84c54e33119d014bc0b556dc27e900-0",
              "trade_type": "buy",
              "tx_hash": "0xf6272151d26f391886232263a384d1d9fb84c54e33119d014bc0b556dc27e900"}, {
              "address": "0x21d05071cA08593e13cd3aFD0b4869537e015C92",
              "amount": "904.171423330858608178",
              "base_asset": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
              "fee": "0",
              "fee_currency": "ALEPH",
              "location": "uniswap",
              "quote_asset": "_ceth_0x27702a26126e0B3702af63Ee09aC4d1A084EF628",
              "rate": "0.1604821621994156262081817395",
              "swaps": [{
                  "amount0_in": "5634.092979176915803392",
                  "amount0_out": "0",
                  "amount1_in": "0",
                  "amount1_out": "2.411679959413889526",
                  "from_address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                  "log_index": 98,
                  "to_address": "0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11",
                  "token0": "_ceth_0x27702a26126e0B3702af63Ee09aC4d1A084EF628",
                  "token1": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                  "tx_hash": "0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6"}, {
                  "amount0_in": "0",
                  "amount0_out": "904.171423330858608178",
                  "amount1_in": "2.411679959413889526",
                  "amount1_out": "0",
                  "from_address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                  "log_index": 101,
                  "to_address": "0x21d05071cA08593e13cd3aFD0b4869537e015C92",
                  "token0": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
                  "token1": "_ceth_0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                  "tx_hash": "0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6"}],
              "timestamp": 1602796833,
              "trade_id": "0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6-0",
              "trade_type": "buy",
              "tx_hash": "0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6"}
          ],
        },
        "message": "",
      }

   :resjson object result: A mapping between accounts and their Uniswap trades history
   :resjson string address: The address of the user who initiated the trade
   :resjson object base_asset: Either an identifier if it's a known token or the address/symbol/name object for the base asset of the trade. That which is bought.
   :resjson object quote_asset: Either an identifier if it's a known token or the address/symbol/name object for the quote asset of the trade. That which is sold to buy the base asset.
   :resjson string amount: In case of a trade_type buy (and for uniswap all are buys) this is the amount of ``"base_asset"`` that is bought.
   :resjson string rate: How much of each quote asset was given for the base asset amount. Essentially ``"amount"`` / ``"rate"`` will give you what you paid in ``"quote_asset"``.
   :resjson string location: Always uniswap.
   :resjson string fee: Always 0 for now.
   :resjson string fee_currency: Always quote_asset.
   :resjson int timestamp: The timestamp of the trade
   :resjson string trade_id: A combination of transaction hash plus a unique id (for custom trades that are virtually made by us)
   :resjson string trade_type: Always buy
   :resjson string tx_hash: The transaction hash
   :resjson list[object] swaps: A list of all the swaps that the trade is made of. Each swap is an object with the following attributes:

       - token0: The identifier of the token.
       - token1: The identifier of the token.
       - amount0_in: The amount (can be zero) of token0 that the user is putting in the swap.
       - amount1_in: The amount (can be zero) of token1 that the user is putting in the swap.
       - amount0_out: The amount (can be zero) of token0 that the user is getting out of the swap.
       - amount1_out: The amount (can be zero) of token1 that the user is getting out of the swap.
       - from_address: The address that is putting tokens in the swap. Can be many different parties in a multi swap.
       - to_address: The address that is getting tokens out of the swap. Can be many different parties in a multi swap.
       - address: Always the same address of the user, associated with the trade the swaps belong to.
       - tx_hash: The transaction hash of the swap (always the same for swaps of the same transaction/trade).
       - log_index: The index of the swap in the transaction/trade.


   :statuscode 200: Uniswap trades succesfully queried.
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
                      "underlying_token": "_ceth_0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                      "vault_token": "_ceth_0x5dbcF33D8c2E976c6b560249878e6F1491Bca25c",
                      "underlying_value": {
                          "amount": "25", "usd_value": "150"
                      },
                      "vault_value": {
                          "amount": "19", "usd_value": "150"
                      },
                      "roi": "25.55%",
                  },
                  "YYFI Vault": {
                      "underlying_token": "_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e",
                      "vault_token": "_ceth_0xBA2E7Fed597fd0E3e70f5130BcDbbFE06bB94fe1",
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
                      "underlying_token": "_ceth_0xA64BD6C70Cb9051F6A9ba1F163Fdc07E0DfB5F84",
                      "vault_token": "_ceth_0x29E240CFD7946BA20895a7a02eDb25C210f9f324",
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


   :statuscode 200: Yearn vault balances succesfully queried.
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
                          "from_asset": "_ceth_0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                          "from_value": {
                              "amount": "115000", "usd_value": "119523.23"
                          },
                          "to_asset": "_ceth_0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
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
                          "from_asset": "_ceth_0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
                          "from_value": {
                              "amount": "108230.234", "usd_value": "125321.24"
                          },
                          "to_asset": "_ceth_0xdF5e0e81Dff6FAF3A7e52BA697820c5e32D806A8",
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
                          "from_asset": "_ceth_0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e",
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
                          "from_asset": "_ceth_0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3",
                          "from_value": {
                              "amount": "20", "usd_value": "205213.12"
                          },
                          "to_asset": "_ceth_0x7Ff566E1d69DEfF32a7b244aE7276b9f90e9D0f6",
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
   :resjsonarr int timestamp: The unix timestamp at which the event occured.
   :resjsonarr int block_number: The block number at which the event occured.
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

   :statuscode 200: Yearn vaults history succesfully queried.
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
                  "underlying_token":"_ceth_0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                  "vault_token":"_ceth_0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9",
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
                  "underlying_token":"_ceth_0x111111111117dC0aa78b770fA6A738034120C302",
                  "vault_token":"_ceth_0xB8C3B7A2A618C552C23B1E4701109a9E756Bab67",
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


   :statuscode 200: Yearn vault V2 balances succesfully queried.
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
              "_ceth_0xF29AE508698bDeF169B89834F76704C3B205aedf":{
                  "events":[
                    {
                        "event_type":"deposit",
                        "block_number":12588754,
                        "timestamp":1623087604,
                        "from_asset":"_ceth_0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F",
                        "from_value":{
                          "amount":"273.682277822922514201",
                          "usd_value":"273.682277822922514201"
                        },
                        "to_asset":"_ceth_0xF29AE508698bDeF169B89834F76704C3B205aedf",
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
              "_ceth_0x1C6a9783F812b3Af3aBbf7de64c3cD7CC7D1af44":{
                  "events":[
                    {
                        "event_type":"deposit",
                        "block_number":12462638,
                        "timestamp":1621397797,
                        "from_asset":"_ceth_0x94e131324b6054c0D789b190b2dAC504e4361b53",
                        "from_value":{
                          "amount":"32064.715735449204040742",
                          "usd_value":"32064.715735449204040742"
                        },
                        "to_asset":"_ceth_0x1C6a9783F812b3Af3aBbf7de64c3cD7CC7D1af44",
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
                        "from_asset":"_ceth_0x1C6a9783F812b3Af3aBbf7de64c3cD7CC7D1af44",
                        "from_value":{
                          "amount":"32064.715735449204040742",
                          "usd_value":"32064.715735449204040742"
                        },
                        "to_asset":"_ceth_0x94e131324b6054c0D789b190b2dAC504e4361b53",
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
   :resjsonarr int timestamp: The unix timestamp at which the event occured.
   :resjsonarr int block_number: The block number at which the event occured.
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

   :statuscode 200: Yearn vaults V2 history succesfully queried.
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
                    "_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96": {
                        "amount": "1",
                        "usd_value": "5"
                    }
            }]
        },
        "message": ""
      }

   :resjson object result: A mapping between accounts and their balances

   :statuscode 200: Loopring balances succesfully queried.
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
              "daily_stats": [{
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
          }, {
              "eth1_depositor": "0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397",
              "index": 10,
              "public_key": "0xa256e41f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cf14",
              "balance": {"amount": "32.101", "usd_value": "11399"},
              "performance_1d": {"amount": "0.1", "usd_value": "100"},
              "performance_1w": {"amount": "0.7", "usd_value": "700"},
              "performance_1m": {"amount": "3", "usd_value": "3000"},
              "performance_1y": {"amount": "36.5", "usd_value": "36500"},
              "daily_stats": [],
          }, {
              "eth1_depositor": "0xaee017635291ea8E3C70FeAC5B86e1d3B0e23341",
              "index": 155,
              "public_key": "0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3",
              "balance": {"amount": "32", "usd_value": "19000"},
              "performance_1d": {"amount": "0", "usd_value": "0"},
              "performance_1w": {"amount": "0", "usd_value": "0"},
              "performance_1m": {"amount": "0", "usd_value": "0"},
              "performance_1y": {"amount": "0", "usd_value": "0"},
              "daily_stats": [],
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

   For the daily stats the fields are:
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

   :statuscode 200: Eth2 staking details succesfully queried
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

   :statuscode 200: Eth2 staking deposits succesfully queried
   :statuscode 409: User is not logged in. Or eth2 module is not activated.
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
                      "asset": "_ceth_0x111111111117dC0aa78b770fA6A738034120C302",
                      "link": "https://app.uniswap.org/"
                  }
              },
              "0x0B89f648eEcCc574a9B7449B5242103789CCD9D7": {
                  "1inch": {
                      "amount": "1823.23",
                      "asset": "_ceth_0x111111111117dC0aa78b770fA6A738034120C302",
                      "link": "https://1inch.exchange/"
                  },
                  "uniswap": {
                      "amount": "400",
                      "asset": "_ceth_0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
                      "link": "https://app.uniswap.org/"
                  }
              },
          "message": ""
      }

   :reqjson object result: A mapping of addresses to protocols for which claimable airdrops exist

   :statuscode 200: Tags succesfully queried.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not query an airdrop file

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
   :statuscode 200: The addresses have been queried succesfully
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
   :statuscode 200: The address has been added succesfully.
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
   :statuscode 200: The address has been removed succesfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The address is not in the addresses to query for that protocol.
   :statuscode 500: Internal rotki error

Adding blockchain accounts
===========================

.. http:put:: /api/(version)/blockchains/(name)/

   .. note::
      Supported blockchains: ``"BTC", "ETH", "KSM"``

      Supported blockchains with ENS domains: ``"BTC", "ETH", "KSM"``

      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the the blockchains endpoint with a specific blockchain URL and a list of account data in the json data will add these accounts to the tracked accounts for the given blockchain and the current user. The updated balances after the account additions are returned.
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
   :reqjsonarr string[optional] label: An optional label to describe the new account
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the new account
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
                           "_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96": {"amount": "1", "usd_value": "50"},
                           "_ceth_0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6": {"amount": "1", "usd_value": "1.5"}
                       },
                       "liabilities": {}
                   },
                   "KSM": { "G7UkJAutjbQyZGRiP8z5bBSBPBJ66JbTKAkFDq3cANwENyX": {
                       "assets": {
                           "KSM": {"amount": "12", "usd_value": "894.84"}
                        },
                       "liabilities": {}
                    }
              },
              "totals": {
                  "assets": {
                      "BTC": {"amount": "1", "usd_value": "7540.15"},
                      "ETH": {"amount": "10", "usd_value": "1650.53"},
                      "KSM": {"amount": "12", "usd_value": "894.84"},
                      "_ceth_0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6": {"amount": "1", "usd_value": "1.5"},
                      "_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96": {"amount": "1", "usd_value": "50"}
                  },
                  "liabilities": {}
          },
          "message": ""
      }

   :resjson object result: An object containing the ``"per_account"`` and ``"totals"`` keys as also defined `here <blockchain_balances_result_>`_.
   :statuscode 200: Accounts succesfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occured with some external service query such as Etherscan. Check message for details.


Adding BTC xpubs
========================

.. http:put:: /api/(version)/blockchains/BTC/xpub

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the BTC xpubs endpoint will add an extended public key for bitcoin mainnet. All derived addresses that have ever had a transaction from this xpub and derivation path will be found and added for tracking in rotki.


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
   :reqjsonarr string[optional] xpub_type: An optional type to denote the type of the given xpub. If omitted the prefix xpub/ypub/zpub is used to determine the type. The valid xpub types are: ``"p2pkh"``, ``"p2sh_p2wpkh"`` and ``"wpkh"``.
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
   :statuscode 200: Xpub succesfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occured with some external service query such as blockstream. Check message for details.

Editing BTC xpubs
========================

.. http:patch:: /api/(version)/blockchains/BTC/xpub

   Doing a PATCH on the BTC xpubs endpoint will edit the label and tag of an extended public key for bitcoin mainnet.


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
   :statuscode 200: Xpub succesfully editted
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error

Deleting BTC xpubs
========================

.. http:delete:: /api/(version)/blockchains/BTC/xpub

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a DELETE on the BTC xpubs endpoint will remove an extended public key for bitcoin mainnet. All derived addresses from the xpub will also be deleted.


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
   :statuscode 200: Xpub succesfully removed
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occured with some external service query such as blockstream. Check message for details.

Editing blockchain account data
=================================

.. http:patch:: /api/(version)/blockchains/(name)/

   .. note::
      Supported blockchains: ``"BTC", "ETH", "KSM"``

      Supported blockchains with ENS domains: ``"BTC", "ETH", "KSM"``

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
   :reqjsonarr string[optional] label: An optional label to edit for the account
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

   :statuscode 200: Accounts succesfully edited
   :statuscode 400: Provided JSON or data is in some way malformed. Given list to edit is empty.
   :statuscode 409: User is not logged in. An account given to edit does not exist or a given tag does not exist.
   :statuscode 500: Internal rotki error

Removing blockchain accounts
==============================

.. http:delete:: /api/(version)/blockchains/(name)/

   .. note::
      Supported blockchains: ``"BTC", "ETH", "KSM"``

      Supported blockchains with ENS domains: ``"BTC", "ETH", "KSM"``

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
   :statuscode 200: Accounts succesfully deleted
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to remove contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occured with some external service query such as Etherscan. Check message for details.

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
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "50.315",
                  "usd_value": "2370.13839",
                  "tags": ["public"],
                  "location": "blockchain"
              }, {
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }, {
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
   :statuscode 200: Balances succesfully queried
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
   :reqjsonarr string location: The location where the balance is saved. Can be one of: ["external", "kraken", "poloniex", "bittrex", "binance", "bitmex", "coinbase", "banks", "blockchain", "coinbasepro", "gemini", "ftx", "independentreserve"]

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
          "balances": [{
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "50.315",
                  "usd_value": "2370.13839",
                  "tags": ["public"],
                  "location": "blockchain"
              }, {
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }, {
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
   :statuscode 200: Balances succesfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The balances to add contained invalid assets or were an empty list. One of the balance labels already exist.
   :statuscode 409: User is not logged in. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occured with some external service query such as Cryptocompare. Check message for details.

Editing manually tracked balances
====================================

.. http:patch:: /api/(version)/balances/manual

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PATCH on the the manual balances endpoint allows you to edit a number of manually tracked balances by label.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/balances/manual/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "balances": [{
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "4.5",
                  "location": "blockchain"
                  },{
                  "asset": "ETH",
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
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "4.5",
                  "usd_value": "210.548",
                  "tags": ["public"],
                  "location": "blockchain"
              }, {
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }, {
                  "asset": "ZEC",
                  "label" "My favorite wallet",
                  "amount": "10"
                  "usd_value": "1330.85"
                  "location": "kraken"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances succesfully edited
   :statuscode 400: Provided JSON or data is in some way malformed. The balances to add contained invalid assets or were an empty list.
   :statuscode 409: User is not logged in. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occured with some external service query such as Cryptocompare. Check message for details.

Deleting manually tracked balances
======================================

.. http:delete:: /api/(version)/balances/manual/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a DELETE on the the manual balances endpoint with a list of labels to of manually tracked balances will remove these balances from the database for the current user.
    If one of the given labels to remove is invalid the entire request will fail.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/balances/manual HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"labels": ["My monero wallet", "My favorite wallet"]}

   :reqjson list[string] balances: A list of labels of manually tracked balances to delete

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
          "balances": [{
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "4.5",
                  "usd_value": "210.548",
                  "tags": ["public"]
                  "location": "blockchain"
              }, {
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }, {
                  "asset": "ZEC",
                  "label" "My favorite wallet",
                  "amount": "10"
                  "usd_value": "1330.85"
                  "location": "blockchain"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances succesfully delete
   :statuscode 400: Provided JSON or data is in some way malformed. One of the labels to remove did not exist.
   :statuscode 409: User is not logged in. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occured with some external service query such as Cryptocompare. Check message for details.

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
   :statuscode 200: Watchers succesfully queried
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
   :statuscode 200: Watchers succesfully added
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
   :statuscode 200: Watchers succesfully edited
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
   :statuscode 200: Watchers succesfully delete
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
          "result": ["_ceth_0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7", "_ceth_0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets succesfully queried
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

      {"assets": ["_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96"]}

   :reqjson list assets: A list of asset symbols to add to the ignored assets.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["_ceth_0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7", "_ceth_0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413", "_ceth_0x6810e776880C02933D47DB1b9fc05908e5386b96"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets succesfully added
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

      {"assets": ["_ceth_0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413"]}

   :reqjson list assets: A list of asset symbols to remove from the ignored assets.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["_ceth_0xAf30D2a7E90d7DC361c8C4585e9BB7D2F6f15bc7"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets succesfully removed
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. One of the assets provided is not on the list.
   :statuscode 500: Internal rotki error


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
   :statuscode 200: Actions succesfully queried
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
   :statuscode 200: Action ids succesfully added
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
   :statuscode 200: Action ids succesfully removed
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. One of the action ids provided is not on the list.
   :statuscode 500: Internal rotki error


Querying general information
==============================

.. http:get:: /api/(version)/info

   Doing a GET on the info endpoint will return general information about rotki. Under the version key we get info on the version of rotki. If there is a newer version then ``"download_url"`` will be populated. If not then only ``"our_version"`` and ``"latest_version"`` will be. There is a possibility that latest version may not be populated due to github not being reachable. Also we return the data directory


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/version HTTP/1.1
      Host: localhost:5042

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
          },
          "message": ""
      }

   :resjson str our_version: The version of rotki present in the system
   :resjson str latest_version: The latest version of rotki available
   :resjson str url: URL link to download the latest version
   :resjson str data_directory: The rotki data directory

   :statuscode 200: Information queried succesfully
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


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/import HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"source": "cointracking.info", "filepath": "/path/to/data/file"}

   :reqjson str source: The source of the data to import. Valid values are ``"cointracking.info"``, ``"cryptocom"``, ``"blockfi-transactions"``, ``"blockfi-trades"``, ``"nexo"``, ``"gitcoin"``.
   :reqjson str filepath: The filepath to the data for importing

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

.. http:get:: /api/(version)/blockchains/ETH/erc20details/

   Doing a GET to this endpoint will return basic information about a token by calling the ``decimals/name/symbol`` methods.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/erc20details/ HTTP/1.1
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
   :resjson str message: Empty string if there is no isues with the contract, for example, it not existing on the chain.
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

      GET /api/1/exchanges/binance/pairs HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["BTCUSD", "ETHUSD", "XRPUSD"],
          "message": ""
      }

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

Gitcoin gather event data
==========================

.. http:post:: /api/(version)/gitcoin/events

   Doing a POST to this endpoint will initiate a query for all gitcoin events for a specific grant in a specific period. Events will be aggregated from querying the gitcoin api and the local database.


   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/gitcoin/events HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 0, "to_timestamp": 1624828416, "grant_id": 149, "only_cache": false }

   :reqjson integer from_timestamp: The timestamp from which to query grant events
   :reqjson integer to_timestamp: The timestamp until which to query grant events
   :reqjson integer grant_id: The id of the grant for which to query events. In the case of only_cache, this can be omitted so that all saved events are returned from the DB.
   :reqjson bool only_cache: Signifying if caller only wants what's in the DB or if the remote API should also be queried.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              149: {
                  "events": [{
                      "timestamp": 1624791600,
                      "amount": "0.00053",
                      "asset": "ETH",
                      "usd_value": "1.55",
                      "grant_id": 149,
                      "tx_id": "0x00298f72ad40167051e111e6dc2924de08cce7cf0ad00d04ad5a9e58426536a1",
                      "tx_type": "ethereum",
                      "clr_round": null,
                  }, {
                      "timestamp": 1624791600,
                      "amount": "5",
                      "asset": "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F",
                      "usd_value": "5.01",
                      "grant_id": 149,
                      "tx_id": "5612f84bc20cda25b911af39b792c973bdd5916b3b6868db2420b5dafd705a90",
                      "tx_type": "zksync",
                      "clr_round": 9,
                  }],
                  "name": "rotki",
		  "created_on": 1624791600
             }
          },
          "message": ""
      }

   :resjson object result: A mapping of integer grant ids to events, grant name and created_on.
   :resjson string name: The name of the grant. Can be null if there was a problem querying it.
   :resjson integer created_on: The timestamp the grant was created in. Can be null if there was a problem querying it.
   :resjson integer timestamp: The timestamp of the event
   :resjson string amount: The amount donated in asset
   :resjson string asset: The identifier of the donated asset.
   :resjson string usd_value: The value of the donated asset amount in usd.
   :resjson integer grant_id: The identifier of the grant for which the event is
   :resjson string tx_id: The etherscan or zksync transaction identifier.
   :resjson string tx_type: The type of transaction. Either "ethereum" or "zksync".
   :resjson string clr_round: Optional. Can be null. The CLR round the event belongs to.
   :statuscode 200: Events succesfully queried
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error.


Gitcoin delete event data
==========================

.. http:delete:: /api/(version)/gitcoin/events

   Doing a DELETE to this endpoint will delete all gitcoin event data for the given grant id or if no grant id is given for all grants.



   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/gitcoin/events HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"grant_id": 149 }

   :reqjson integer grant_id: The id of the grant for which to delete events. If not given all gitcoin events are deleted.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :statuscode 200: Events succesfully deleted
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error.


Gitcoin report
===================

.. http:put:: /api/(version)/gitcoin/report

   Doing a PUT to this endpoint will process a report for the user's gitcoin grant events in the given period and return it. Each report contains a breakdown of how much was earned in the current profit currency in total. And also how much was earned in the current profit currency per asset and what amount per asset.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/gitcoin/report HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 0, "to_timestamp": 1624828416, "grant_id": 149 }

   :reqjson integer from_timestamp: The timestamp from which to start the report
   :reqjson integer to_timestamp: The timestamp until which to perform the report.
   :reqjson integer grant_id: Optional. The id of the grant for which to create the report. If missing all grant events in the given range are used from the DB.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
	      "profit_currencty": "EUR",
	      "reports": {
		  "149": {
		      "per_asset": {
			  "ETH": {
			      "amount": "5",
			      "value": "5500"
			  },
			  "_ceth_0x1A175474E89094C44Da98b954EedeAC495271d9A": {
			      "amount": "150",
			      "value": "131.44"
			  },
			  "_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F": {
			      "amount": "101",
			      "value": "93.21"
			  }
		      },
		      "total": "5724.65"
	          },
		  "184": {
		      "per_asset": {
			  "ETH": {
			      "amount": "5",
			      "value": "5500"
			  },
		      },
		      "total": "5500"
		  }
	  }
          "message": ""
      }

   :resjson object reports: A mapping of grant ids to report results.
   :resjson string profit_currency: The profit currency used in the report. The "value" field is in this currency.
   :resjson object per_asset: A mapping of each asset to amount earned in the given period and its value in the user chosen profit currency.
   :resjson string total: The total amount earned in profit currency during the given period.
   :statuscode 200: Report succesfully generated
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error
