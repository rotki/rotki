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

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

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
   :reqjson object[optional] initial_settings: Optionally provide DB settings to set when creating the new user. If not provided, default settings are used. The default value for `submit_usage_analytics` is `True`.

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
                  "ssf_graph_multiplier": 2,
                  "non_sync_exchanges": [{"location": "binance", "name": "binance1"}]
              }
          },
          "message": ""
      }

   :resjson object result: For successful requests, result contains the currently connected exchanges, and the user's settings. For details on the user settings refer to the `Getting or modifying settings`_ section.
   :statuscode 200: Adding the new user was successful
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Another user is already logged in. User already exists. Given Premium API credentials are invalid. Permission error while trying to access the directory where rotki saves data.
   :statuscode 500: Internal rotki error

.. http:post:: /api/(version)/users/(username)

   By doing a ``POST`` at this endpoint, you can login to the user with ``username``.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/users/john HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "password": "supersecurepassword",
          "sync_approval": "unknown",
          "resume_from_backup": false
      }

   :reqjson string password: The password that unlocks the account
   :reqjson bool sync_approval: A string denoting if the user approved an initial syncing of data from premium. Valid values are ``"unknown"``, ``"yes"`` and ``"no"``. Should always be ``"unknown"`` at first and only if the user approves should a login with approval as ``"yes`` be sent. If he does not approve a login with approval as ``"no"`` should be sent. If there is the possibility of data sync from the premium server and this is ``"unknown"`` the login will fail with an appropriate error asking the consumer of the api to set it to ``"yes"`` or ``"no"``.
   :reqjson bool resume_from_backup: An optional boolean denoting if the user approved a resume from backup. This is used to handle the case where the encrypted user database is in a semi upgraded state during user login. If not given, the value defaults to ``false`` so if a semi upgraded database exists during login, the consumer of the api will receive a response with a status '300 Multiple Choices', an explanatory message and an empty result. If the value is ``true`` then the latest backup will be used and the login will proceed as usual.

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
                  "ssf_graph_multiplier": 2,
                  "non_sync_exchanges": [{"location": "binance", "name": "binance1"}]
              }
          },
          "message": ""
      }

   :resjson object result: For successful requests, result contains the currently connected exchanges,and the user's settings. For details on the user settings refer to the `Getting or modifying settings`_ section.
   :statuscode 200: Logged in successfully
   :statuscode 300: This would be the response status in the following two cases:

        - There is an unfinished upgrade to the encrypted user database, and the login was sent with resume_from_backup set to ``false``. The consumer of the api can resend with resume_from_backup set to ``true``, so that the user will login using the latest backup of the encrypted database. In this case the response will contain an empty ``result`` key and an explanatory ``message`` on the message key.
        - Possibility of syncing exists and the login was sent with sync_approval set to ``"unknown"``. Consumer of api must resend with ``"yes"`` or ``"no"``. In this case the result will contain an object with a payload for the message under the ``result`` key and the message under the ``message`` key. The payload has the following keys: ``local_size``, ``remote_size``, ``local_last_modified``, ``remote_last_modified``.

   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: Provided password is wrong for the user or some other authentication error.
   :statuscode 409: User does not exist.  Another user is already logged in. There was a fatal error during the upgrade of the DB. Permission error while trying to access the directory where rotki saves data.
   :statuscode 500: Generic internal rotki error
   :statuscode 542: Internal rotki error relating to the database. Check message for more details.

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
   :statuscode 403: Provided API key/secret does not authenticate.
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
   :statuscode 403: Logged in User does not have premium.
   :statuscode 409: User is not logged in, or user does not exist, or db operation error
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/premium/sync

   By doing a ``PUT`` at this endpoint you can backup or restore the database for the logged-in user using premium sync.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/premium/sync HTTP/1.1
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
   :statuscode 200: Password changed successful
   :statuscode 400: Provided call is in some way malformed. For example a user who is not logged in has been specified.
   :statuscode 401: Password mismatch
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
         "result":{
            "etherscan":{
               "eth": {"api_key":"key1"},
               "arbitrum_one": {"api_key":"key3"}
            },
            "cryptocompare": {"api_key":"boooookey"},
            "opensea": {"api_key":"goooookey"},
            "monerium": {"username":"Ben", "password":"secure"}
         },
         "message":""
      }

   :resjson object result: The result object contains as many entries as the external services. Each entry's key is the name and the value is another object of the form ``{"api_key": "foo"}``. For etherscan services all are grouped under the ``etherscan`` key. If there are no etherscan services this key won't be present. The ``monerium`` service has a different structure than the rest. Has ``username`` and ``password`` keys.
   :statuscode 200: Querying of external service credentials was successful
   :statuscode 401: There is no logged in user
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/external_services

   By doing a PUT on the external services endpoint you can save credentials
   for external services such as etherscan, cryptocompare e.t.c.
   If a credential already exists for a service it is overwritten.

   Some credentials like monerium can't be input if the user is not premium.

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
   :reqjsonarr string name: Each entry in the list should have a name for the service. Valid ones are ``"etherscan"``, ``"cryptocompare"``, ``"beaconchain"``, ``"loopring"``, ``"opensea"``, ``blockscout``, ``monerium``.
   :reqjsonarr string[optional] api_key: Each entry in the list should have an api_key entry except for monerium.
   :reqjsonarr string[optional] username: The monerium entry should have a username key. For monerium the user should have premium.
   :reqjsonarr string[optional] password: The monerium entry should have a password key. For monerium the user should have premium.

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

   :resjson object result: The result object contains as many entries as the external services.
   :statuscode 200: Saving new external service credentials was successful
   :statuscode 400: Provided JSON is in some way malformed, of invalid value provided.
   :statuscode 401: There is no logged in user
   :statuscode 403: Logged in user does not have premium and requested to add credentials that can only work for premium.
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
              "ssf_graph_multiplier": 2,
              "non_sync_exchanges": [{"location": "binance", "name": "binance1"}],
              "cost_basis_method": "fifo",
              "oracle_penalty_threshold_count": 5,
              "oracle_penalty_duration": 1800,
              "auto_create_calendar_reminders": true,
              "address_name_priority": ["private_addressbook", "blockchain_account",
                                        "global_addressbook", "ethereum_tokens",
                                        "hardcoded_mappings", "ens_names"],
              "ask_user_upon_size_discrepancy": true,
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
   :resjson int ssf_graph_multiplier: A multiplier to the snapshot saving frequency for zero amount graphs. Originally 0 by default. If set it denotes the multiplier of the snapshot saving frequency at which to insert 0 save balances for a graph between two saved values.
   :resjson string cost_basis_method: Defines which method to use during the cost basis calculation. Currently supported: fifo, lifo.
   :resjson string address_name_priority: Defines the priority to search for address names. From first to last location in this array, the first name found will be displayed.
   :resjson bool infer_zero_timed_balances: A boolean denoting whether to infer zero timed balances for assets that have no balance at a specific time. This is useful for showing zero balance periods in graphs.
   :resjson int query_retry_limit: The number of times to retry a query to external services before giving up. Default is 5.
   :resjson int connect_timeout: The number of seconds to wait before giving up on establishing a connection to an external service. Default is 30.
   :resjson int read_timeout: The number of seconds to wait for the first byte after a connection to an external service has been established. Default is 30.
   :resjson int oracle_penalty_threshold_count: The number of failures after which an oracle is penalized. Default is 5.
   :resjson int oracle_penalty_duration: The duration in seconds for which an oracle is penalized. Default is 1800.
   :resjson bool auto_create_calendar_reminders: A boolean denoting whether reminders are created automatically for calendar entries based on the decoded history events. Default is ``true``.
   :resjson bool ask_user_upon_size_discrepancy: A boolean denoting whether to prompt the user for confirmation each time the remote database is bigger than the local one or directly force push. Default is ``true``.

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
   :reqjson string[optional] beacon_rpc_endpoint: A URL denoting the rpc endpoint for the ethereum consensus layer beacon node to use when contacting the consensus layer. If it can not be reached or if it is invalid beaconcha.in is used.
   :reqjson string[optional] main_currency: The FIAT currency to use for all profit/loss calculation. USD by default.
   :reqjson string[optional] date_display_format: The format in which to display dates in the UI. Default is ``"%d/%m/%Y %H:%M:%S %Z"``.
   :reqjson bool[optional] submit_usage_analytics: A boolean denoting whether or not to submit anonymous usage analytics to the rotki server.
   :reqjson list active_module: A list of strings denoting the active modules with which rotki should run.
   :reqjson list current_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting current prices.
   :reqjson list historical_price_oracles: A list of strings denoting the price oracles rotki should query in specific order for requesting historical prices.
   :reqjson list non_syncing_exchanges: A list of objects with the keys ``name`` and ``location`` of the exchange. These exchanges will be ignored when querying the trades. Example: ``[{"name": "my_exchange", "location": "binance"}]``.
   :resjson int ssf_graph_multiplier: A multiplier to the snapshot saving frequency for zero amount graphs. Originally 0 by default. If set it denotes the multiplier of the snapshot saving frequency at which to insert 0 save balances for a graph between two saved values.
   :resjson bool infer_zero_timed_balances: A boolean denoting whether to infer zero timed balances for assets that have no balance at a specific time. This is useful for showing zero balance periods in graphs.
   :resjson int query_retry_limit: The number of times to retry a query to external services before giving up. Default is 5.
   :resjson int connect_timeout: The number of seconds to wait before giving up on establishing a connection to an external service. Default is 30.
   :resjson int read_timeout: The number of seconds to wait for the first byte after a connection to an external service has been established. Default is 30.
   :resjson int oracle_penalty_threshold_count: The number of failures after which an oracle is penalized. Default is 5.
   :resjson int oracle_penalty_duration: The duration in seconds for which an oracle is penalized. Default is 1800.
   :resjson bool[optional] auto_create_calendar_reminders: A boolean denoting whether reminders are created automatically for calendar entries based on the decoded history events.
   :resjson bool[optional] ask_user_upon_size_discrepancy: A boolean denoting whether to prompt the user for confirmation each time the remote database is bigger than the local one or directly force push.

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
              "ssf_graph_multiplier": 2,
              "non_sync_exchanges": [{"location": "binance", "name": "binance1"}]
              "auto_create_calendar_reminders": true,
              "ask_user_upon_size_discrepancy": true,
          },
          "message": ""
      }

   :resjson object result: Same as when doing GET on the settings

   :statuscode 200: Modifying settings was successful
   :statuscode 400: Provided JSON is in some way malformed, of invalid value for a setting.
   :statuscode 401: No user is logged in.
   :statuscode 409: Tried to set eth rpc endpoint that could not be reached.
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

      GET /api/1/blockchains/eth/nodes HTTP/1.1
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
                "blockchain": "eth"
            },
            {
                "identifier": 2,
                "name": "mycrypto",
                "endpoint": "https://api.mycryptoapi.com/eth",
                "owned": false,
                "weight": "20.00",
                "active": true,
                "blockchain": "eth"
            },
            {
                "identifier": 3,
                "name": "blockscout",
                "endpoint": "https://mainnet-nethermind.blockscout.com/",
                "owned": false,
                "weight": "20.00",
                "active": true,
                "blockchain": "eth"
            },
            {
                "identifier": 4,
                "name": "avado pool",
                "endpoint": "https://mainnet.eth.cloud.ava.do/",
                "owned": false,
                "weight": "20.00",
                "active": true,
                "blockchain": "eth"
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

      PUT /api/1/blockchains/eth/nodes HTTP/1.1
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
   :statuscode 409: No user is logged or entry couldn't be created.
   :statuscode 500: Internal rotki error

.. http:patch:: /api/(version)/blockchains/(blockchain)/nodes

   By doing a PATCH on this endpoint you will be able to edit an already existing node entry with the information provided.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/blockchains/eth/nodes HTTP/1.1
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
   :statuscode 409: No user is logged or entry couldn't be updated.
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/blockchains/(blockchain)/nodes

   By doing a DELETE on this endpoint you will be able to delete an already existing node.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/eth/nodes HTTP/1.1
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
   :statuscode 401: No user is currently logged in
   :statuscode 404: There is no task with the given task id
   :statuscode 500: Internal rotki error
   :statuscode 502: Problem contacting a remote service


Cancel ongoing async tasks
=============================

   .. http:delete:: /api/(version)/tasks/(task_id)

      By calling this endpoint with a particular task identifier you can cancel the ongoing task with that identifier. Keep in mind that this may leave stuff half-finished since the canceled task may be stopped in the middle.

      **Example Request**:

      .. http:example:: curl wget httpie python-requests

	 DELETE /api/1/tasks/42 HTTP/1.1
	 Host: localhost:5042

      **Example Response**:

      The following is an example response of a succesfully canceled task

      .. sourcecode:: http

	 HTTP/1.1 200 OK
	 Content-Type: application/json

	 {
	     "result": true, "message": ""
	 }

      :resjson bool result: True if the task was canceled and false otherwise.

      :statuscode 200: The task was successfully canceled.
      :statuscode 400: Provided JSON is in some way malformed.
      :statuscode 401: No user is currently logged in
      :statuscode 404: There is no task with the given task id.
      :statuscode 500: Internal rotki error


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
                "manualcurrent": 5,
                "blockchain": 6,
                "fiat": 7
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

.. http:post:: /api/(version)/nfts/prices

   Get current prices and whether they have been manually input or not for NFT assets.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/nfts/prices HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"lps_handling": "all_nfts"}

    :reqjson string[optional] lps_handling: A flag to specify how to handle LP NFTs. Possible values are `'all_nfts'` (default), `'only_lps'` and `'exclude_lps'`. You can use 'only_lps' if you want to only include LPs NFTs in the result or you can use 'exclude_lps' if you want NFTs not marked as LP positions.


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

   Retrieve all the manually input latest prices stored in the database, including prices for nfts.

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
            },
            {
              "from_asset": "_nft_custom",
              "to_asset": "ETH",
              "price_in_asset": "1"
            }
          ],
          "message": ""
      }

   :resjson object result: A list of results with the prices along their `from_asset` and `to_asset`.
   :statuscode 200: Successful query
   :statuscode 401: No user is logged in.
   :statuscode 500: Internal rotki error


Add manual current price for an asset
=============================================

.. http:put:: /api/(version)/assets/prices/latest

   Giving a unique asset identifier and a price via this endpoint stores the current price for an asset. If given, this overrides all other current prices. At the moment this will only work for non fungible assets.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/prices/latest HTTP/1.1
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

.. http:delete:: /api/(version)/assets/prices/latest

   Deletes an asset that has as manual price set. IF the asset is not found or a manual price is not set a 409 is returned. At the moment this only works for nfts.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/prices/latest HTTP/1.1
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

    Manually adds the price of an asset against another asset at a certain timestamp to the database. If a manual price for the specified asset pair and timestamp already exists, it is replaced with the new price provided.


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
   :statuscode 401: No user is logged in.
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

      {"name": "my kraken key", "location": "kraken", "api_key": "ddddd", "api_secret": "ffffff", "passphrase": "secret", "binance_markets": ["ETHUSDC", "BTCUSDC"]}

   :reqjson string name: A name to give to this exchange's key
   :reqjson string location: The location of the exchange to setup
   :reqjson string api_key: The api key with which to setup the exchange
   :reqjson string api_secret: The api secret with which to setup the exchange
   :reqjson string passphrase: An optional passphrase, only for exchanges, like coinbase pro, which need a passphrase.
   :reqjson string kraken_account_type: An optional setting for kraken. The type of the user's kraken account. Valid values are "starter", "intermediate" and "pro".
   :reqjson list binance_markets: An optional setting for binance and binanceus. A list of string for markets that should be queried.

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
   :statuscode 401: No user is logged in
   :statuscode 409: The exchange has already been registered. The API key/secret is invalid or some other error.
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
   :statuscode 401: No user is logged in.
   :statuscode 409: The exchange is not registered or some other error
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
   :statuscode 401: No user is logged in.
   :statuscode 409: The exchange can not be found. The new exchange credentials were invalid.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Exchange is not registered or some other exchange query error. Check error message for details.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some exchange query error. Check error message for details.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Exchange is not registered or some other error. Check error message for details.
   :statuscode 500: Internal rotki error

Deleting locally saved blockchain transactions
=================================================

.. http:delete:: /api/(version)/blockchains/transactions

   Doing a DELETE on the blockchain transactions endpoint will either delete locally saved transaction data. If nothing is given all transaction data will be deleted. Can specify the chain to only delete all transactions of that chain. Or even further chain and tx_hash to delete only a specific transaction's data.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/transactions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"chain": "eth", "tx_hash": "0x6826b8646578ff457ba01bfe6a2cc77e3d6e40a849e45a97ca12dfd9150cd901"}

   :reqjson string chain: Optional. The name of the chain for which to delete transaction. ``"eth"``, ``"optimism"``, ``"zksync_lite"`` etc. If not given all transactions for all chains are purged. This is using the backend's SupportedBlockchain with the limitation being only chains for which we save transactions.
   :reqjson string tx_hash: Optional. The transaction to delete. If given only the specific transaction is deleted. This should always be given in combination with the chain argument.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Data successfully purged.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: User is not logged.
   :statuscode 409: Other error. Check error message for details.
   :statuscode 500: Internal rotki error


Decode transactions that haven't been decoded yet
=================================================

.. http:post:: /api/(version)/blockchains/(chaintype)/transactions/decode

   Doing a POST on the transactions decoding endpoint will start the decoding process for all the transactions that haven't been decoded yet for the given chain and addresses combination. Transactions already decoded won't be re-decoded unless ignore_cache is set to true . ``chaintype`` can be either ``evm`` or ``evmlike``

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/blockchains/evm/transactions/decode HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "async_query": false,
	  "ignore_cache": false,
          "chains": ["ethereum", "optimism"]
      }

   :reqjson bool ignore_cache: Defaults to false. If set to true then all events will be redecoded, not only those that have not yet been decoded.
   :reqjson list chains: A list specifying the evm/evmlike chains for which to decode tx_hashes. The possible values are limited to the chains with evm transactions for evm and to zksynclite for evmlike. If the list is not provided all transactions from all the chains will be decoded.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": {"decoded_tx_number": {"ethereum": 4, "optimism": 1}}, "message": "" }

   :resjson object decoded_tx_number: A mapping of how many transactions were decoded per requested chain. If a chain was not requested no key will exist in the mapping.
   :statuscode 200: Transactions successfully decoded.
   :statuscode 401: User is not logged in.
   :statuscode 409: Some other error. Check error message for details.
   :statuscode 500: Internal rotki error

.. http:get:: /api/(version)/blockchains/(chaintype)/transactions/decode

   Doing a GET on the transactions decoding endpoint will return a breakdown of the number of transactions that are not decoded. ``chaintype`` can be either ``evm`` or ``evmlike``

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/evm/transactions/decode HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"async_query": false}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {"result": {"ethereum": {"undecoded": 1, "total": 2}, "optimism": {"undecoded": 1, "total": 1}, "base": {"undecoded": 1, "total": 1}}, "message": "" }

   :resjson object result: A mapping of the chain name to the number of transactions missing the decoding and the total number of transactions. If a chain doesn't have undecoded transactions it doesn't appear on the mapping.

   :statuscode 200: Transactions successfully counted.
   :statuscode 401: User is not logged in.
   :statuscode 409: Other error. Check error message for details.
   :statuscode 500: Internal rotki error


Purging locally saved data for ethereum modules
====================================================

.. http:delete:: /api/(version)/blockchains/eth/modules/(name)/data

   Doing a DELETE on the data of a specific ETH module will purge all locally saved data for the module. Can also purge all module data by doing a ``DELETE`` on ``/api/(version)/blockchains/eth/modules/data`` in which case all module data will be purged.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/eth/modules/uniswap/data HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {}

   :reqjson string name: The name of the module whose data to delete. Can be one of the supported ethereum modules. The name can be omitted by doing a ``DELETE`` on ``/api/(version)/blockchains/eth/modules/data`` in which case all module data will be purged.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Data successfully purged.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: User is not logged in.
   :statuscode 409: Some other error. Check error message for details.
   :statuscode 500: Internal rotki error


Getting all supported chains
==============================

.. http:get:: /api/(version)/blockchains/supported

    Doing a GET on the supported chains will return all supported chains along with their type. If it is an EVM chain it will also contain the name of the EVM chain.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

    GET /api/(version)/blockchains/supported HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

    {}

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "result": [
                {
                    "id": "eth",
                    "name": "ethereum",
                    "type": "evm",
                    "native_token": "ETH",
                    "image": "ethereum.svg",
                    "evm_chain_name": "ethereum"
                },
                {
                    "id": "eth2",
                    "name": "Ethereum Staking",
                    "type": "eth2",
                    "native_token": "ETH2",
                    "image": "ethereum.svg"
                },
                {
                    "id": "btc",
                    "name": "bitcoin",
                    "type": "bitcoin",
                    "native_token": "BTC",
                    "image": "bitcoin.svg"
                },
                {
                    "id": "bch",
                    "name": "bitcoin cash",
                    "type": "bitcoin",
                    "native_token": "BCH",
                    "image": "bitcoin-cash.svg"
                },
                {
                    "id": "ksm",
                    "name": "kusama",
                    "type": "substrate",
                    "native_token": "KSM",
                    "image": "kusama.svg"
                },
                {
                    "id": "avax",
                    "name": "avalanche",
                    "type": "evm",
                    "native_token": "AVAX",
                    "image": "avalanche.svg",
                    "evm_chain_name": "avalanche"
                },
                {
                    "id": "dot",
                    "name": "polkadot",
                    "type": "substrate",
                    "native_token": "DOT",
                    "image": "polkadot.svg"
                },
                {
                    "id": "optimism",
                    "name": "optimism",
                    "type": "evm",
                    "native_token": "ETH",
                    "image": "optimism.svg",
                    "evm_chain_name": "optimism"
                },
                {
                    "id": "polygon_pos",
                    "name": "Polygon PoS",
                    "type": "evm",
                    "native_token": "eip155:137/erc20:0x0000000000000000000000000000000000001010",
                    "image": "polygon_pos.svg",
                    "evm_chain_name": "polygon_pos"
                },
                {
                    "id": "arbitrum_one",
                    "name": "Arbitrum One",
                    "type": "evm",
                    "native_token": "ETH",
                    "image": "arbitrum_one.svg",
                    "evm_chain_name": "arbitrum_one"
                },
                {
                    "id": "base",
                    "name": "base",
                    "type": "evm",
                    "native_token": "ETH",
                    "image": "base.svg",
                    "evm_chain_name": "base"
                },
                {
                    "id": "gnosis",
                    "name": "gnosis",
                    "type": "evm",
                    "native_token": "XDAI",
                    "image": "gnosis.svg",
                    "evm_chain_name": "gnosis"
                },
                {
                    "id": "zksync_lite",
                    "name": "zksync",
                    "type": "evmlike",
                    "native_token": "ETH",
                    "image": "zksync_lite.svg",
                }
            ],
            "message": ""
        }

    :resjson object result: Contains all supported chains' ID, name, type, EVM chain name (if applicable).
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some other error. Check error message for details.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some other error. Check error message for details.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some other error. Check error message for details.
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

.. http:get:: /api/(version)/blockchains/eth/modules

   Doing a GET on this endpoint will return all supported ethereum modules

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/eth/modules HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some other error. Check error message for details.
   :statuscode 500: Internal rotki error

Querying evm transactions
=================================

.. http:post:: /api/(version)/blockchains/evm/transactions/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a POST on the evm transactions endpoint will query all evm transactions for all the tracked user addresses and save them to the DB. Caller can also specify a chain and/or an address to further filter the query.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/blockchains/evm/transactions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "accounts": [{
              "address": "0x3CAdbeB58CB5162439908edA08df0A305b016dA8",
              "evm_chain": "optimism"
          }, {
              "address": "0xF2Eb18a344b2a9dC769b1914ad035Cbb614Fd238"
          }],
          "from_timestamp": 1514764800,
          "to_timestamp": 1572080165
      }

   :reqjson list[string] accounts: List of accounts to filter by. Each account contains an ``"address"`` key which is required and is an evm address. It can also contains an ``"evm_chain"`` field which is the specific chain for which to limit the address.
   :reqjson int from_timestamp: The timestamp after which to return transactions. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return transactions. If not given all transactions from ``from_timestamp`` until now are returned.
   :reqjson string evm_chain: Optional. The name of the evm chain by which to filter all transactions. ``"ethereum"``, ``"optimism"`` etc.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

   :resjson object result: true for success

   :statuscode 200: Transactions successfully queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: User is not logged in.
   :statuscode 409: Some other error. Check error message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Request specific EVM transaction repulling and event decoding
===================================================================

.. http:put:: /api/(version)/blockchains/evm/transactions

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the evm transactions endpoint will request a decoding of the given transaction and generation of decoded events. That basically entails deleteing and re-querying all the transaction data. Transaction, internal transactions, receipts and all log for each hash and then decoding all events. Also requeries prices for assets involved in these events.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/evm/transactions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "async_query": true,
          "evm_chain": "ethereum",
          "tx_hash": "0xe33041d0ae336cd4c588a313b7f8649db07b79c5107424352b9e52a6ea7a9742"
      }

   :reqjson str evm_chain: A string specifying the evm chain for which the transaction is.
   :reqjson str tx_hash: The transaction hash whose data to repull and redecode events
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true,
        "message": ""
      }


   :statuscode 200: Transaction successfully repulled and decoded.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: The given hashe does not correspond to a transaction according to the nodes we contacted.
   :statuscode 500: Internal rotki error
   :statuscode 502: Problem contacting a remote service

Request specific EVMlike transaction repulling and event decoding
===================================================================

.. http:put:: /api/(version)/blockchains/evmlike/transactions

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the evmlike transactions endpoint will request a decoding of the given transactions and generation of decoded events. Transaction data will also be deleted and requeried and events redecoded.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/evm/transactions HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "async_query": true,
          "chain": "zksync_lite",
          "tx_hash": "0xe33041d0ae336cd4c588a313b7f8649db07b79c5107424352b9e52a6ea7a9742"
      }

   :reqjson list data[optional]: A list of data to decode. Each data entry consists of a ``"chain"`` key specifying the evmlike chain for which to decode tx_hashes and a ``"tx_hashes"`` key which is an optional list of transaction hashes to request decoding for in that chain. If the list of transaction hashes is not passed then all transactions for that chain are decoded. Passing an empty list is not allowed.
   :reqjson str evm_chain: A string specifying the chain for which the transaction is. Can only be zksync lite for now.
   :reqjson str tx_hash: The transaction hash whose data to repull and redecode events
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true,
        "message": ""
      }


   :statuscode 200: Transaction successfully decoded.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: Given hash does not correspond to a transaction according to the nodes we contacted.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some other error. Check error message for details.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Tag with the same name already exists.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Tag with the given name does not exist.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Tag with the given name does not exist.
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
                  "btc": {
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
                   "eth": { "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B": {
                       "assets": {
                           "ETH": {"amount": "10", "usd_value": "1650.53"},
                           "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "15", "usd_value": "15.21"}
                       },
                       "liabilities": {
                           "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F": {"amount": "20", "usd_value": "20.35"}
                       }
                  }},
                   "eth2": { "0x9675faa8d15665e30d31dc10a332828fa15e2c7490f7d1894d9092901b139801ce476810f8e1e0c7658a9abdb9c4412e": {
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Invalid blockchain, or problems querying the given blockchain
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan or blockchain.info could not be reached or returned unexpected response.

Querying all balances
==========================

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also serves as a hacky way of notifying the backend that the user has logged in the dashboard and background task scheduling or other heavy tasks can commence.

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
   :statuscode 401: User is not logged in.
   :statuscode 500: Internal rotki error

Querying all supported assets
================================

.. http:post:: /api/(version)/assets/all

   Doing a POST on the all assets endpoint will return a list of all supported assets and their details.

   .. note::
      When filtering using ``evm_chain``, ``asset_type`` if provided must be ``evm_token``.


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
   :reqjson string evm_chain: The name for the evm chain to be used to filter the result data. Possible values are ``ethereum``, ``optimism``, ``gnosis``, ``celo``, etc. Optional.
   :reqjson string address: The address of the evm asset to be used to filter the result data. Optional.
   :reqjson bool show_user_owned_assets_only: A flag to specify if only user owned assets should be returned. Defaults to ``"false"``. Optional.
   :reqjson bool show_whitelisted_assets_only: If set to true then only whitelisted spam tokens are queried.
   :reqjson string ignored_assets_handling: A flag to specify how to handle ignored assets. Possible values are `'none'`, `'exclude'` and `'show_only'`. You can write 'none' in order to not handle them in any special way (meaning to show them too). This is the default. You can write 'exclude' if you want to exclude them from the result. And you can write 'show_only' if you want to only see the ignored assets in the result.
   :reqjson list[string] identifiers: A list of asset identifiers to filter by. Optional.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": [
              {
                  "identifier": "eip155:1/erc20:0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
                  "evm_address": "0xB6eD7644C69416d67B522e20bC294A9a9B405B31",
                  "evm_chain":"ethereum",
                  "token_kind":"erc20",
                  "decimals": 8,
                  "name": "0xBitcoin",
                  "started": 1517875200,
                  "symbol": "0xBTC",
                  "asset_type": "evm token"
                  "cryptocompare":"0xbtc",
                  "coingecko":"0xbtc",
                  "protocol":"None"
              },
              {
                  "identifier": "DCR",
                  "name": "Decred",
                  "started": 1450137600,
                  "symbol": "DCR",
                  "asset_type": "own chain"
              },
              {
                  "identifier": "eip155:1/erc20:0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38",
                  "evm_address": "0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38",
                  "evm_chain":"ethereum",
                  "token_kind":"erc20",
                  "decimals": 18,
                  "name": "DigitalDevelopersFund",
                  "started": 1498504259,
                  "symbol": "DDF",
                  "asset_type": "evm token"
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
                  "asset_type": "own chain"
              },
              {
                  "identifier": "KRW",
                  "name": "Korean won",
                  "symbol": "KRW",
                  "asset_type": "fiat"
              },
              {
                  "identifier": "eip155:1/erc20:0xD850942eF8811f2A866692A623011bDE52a462C1",
                  "evm_address": "0xD850942eF8811f2A866692A623011bDE52a462C1",
                  "evm_chain":"ethereum",
                  "token_kind":"erc20",
                  "decimals": 18,
                  "name": "Vechain Token",
                  "started": 1503360000,
                  "swapped_for": "VET",
                  "symbol": "VEN",
                  "asset_type": "evm token",
                  "coingecko": "vechain"
                  "cryptocompare":"VET",
                  "coingecko":"vet",
                  "protocol":"None"
              }
          ],
          "message": ""
      }

   :resjson list result: A list of assets that match the query with their respective asset details.
   :resjson string asset_type: The type of asset. Valid values are ethereum token, own chain, omni token and more. For all valid values check `here <https://github.com/rotki/rotki/blob/8387c96eb77f9904b44a1ddd0eb2acbf3f8d03f6/rotkehlchen/assets/types.py#L10>`_.
   :resjson integer started: An optional unix timestamp denoting when we know the asset started to have a price.
   :resjson string name: The long name of the asset. Does not need to be the same as the unique identifier.
   :resjson string forked: An optional attribute representing another asset out of which this asset forked from. For example ``ETC`` would have ``ETH`` here.
   :resjson string swapped_for: An optional attribute representing another asset for which this asset was swapped for. For example ``VEN`` tokens were at some point swapped for ``VET`` tokens.
   :resjson string symbol: The symbol used for this asset. This is not guaranteed to be unique.
   :resjson string evm_address: If the type is ``evm_token`` then this will be the hexadecimal address of the token's contract.
   :resjson string evm_chain: If the type is ``evm_token`` then this will be the name of the evm chain. "ethereum", "optimism" etc.
   :resjson string token_kind:  If the type is ``evm_token`` then this will be the token type, for example ``erc20``.
   :resjson integer decimals: If the type is ``evm_token`` then this will be the number of decimals the token has.
   :resjson string cryptocompare: The cryptocompare identifier for the asset. can be missing if not known. If missing a query by symbol is attempted.
   :resjson string coingecko: The coingecko identifier for the asset. can be missing if not known.
   :resjson string protocol: An optional string for evm tokens denoting the protocol they belong to. For example uniswap, for uniswap LP tokens.
   :resjson object underlying_tokens: Optional. If the token is an LP token or a token set or something similar which represents a pool of multiple other tokens, then this is a list of the underlying token addresses and a percentage(value in the range of 0 to 100) that each token contributes to the pool.
   :resjson string notes: If the type is ``custom_asset`` this is a string field with notes added by the user.
   :resjson string custom_asset_type: If the type is ``custom_asset`` this field contains the custom type set by the user for the asset.
   :statuscode 200: Assets successfully queried.
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
            "eip155:1/erc20:0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38",
            "_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041"
        ]
      }

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "assets": {
            "eip155:1/erc20:0xB6eD7644C69416d67B522e20bC294A9a9B405B31": {
              "name": "0xBitcoin",
              "symbol": "0xBTC",
              "asset_type": "evm token",
              "collection_id": "0"
            },
            "DCR": {
              "name": "Decred",
              "symbol": "DCR",
              "asset_type": "own chain"
            },
            "eip155:1/erc20:0xcC4eF9EEAF656aC1a2Ab886743E98e97E090ed38": {
              "name": "DigitalDevelopersFund",
              "symbol": "DDF",
              "chain_id": 1,
              "is_custom_asset": false,
              "asset_type": "evm token"
            },
            "_nft_0x57f1887a8bf19b14fc0df6fd9b2acc9af147ea85_26612040215479394739615825115912800930061094786769410446114278812336794170041": {
              "name": "Mooncat 151",
              "asset_type": "nft",
              "collection_name": "Mooncats",
              "image_url": "https://myimg.com"
            }
          },
          "asset_collections": {
            "0": {
              "name": "0xBitcoin",
              "symbol": "0xBTC"
            }
          }
        },
        "message": ""
      }

   :resjson object assets: A mapping of identifiers to (1) their name, symbol & chain(if available) if they are assets. And to (2) their name, collection name and image url if they are nfts.
   :resjson object asset_collections: A mapping of asset collections ids to their properties.
   :resjson string name: Name of the asset/nft.
   :resjson string symbol: Symbol of the asset. Will only exist for non-nft assets.
   :resjson int chain_id: This value might not be included in all the results. Chain id of the chain where the asset is located if the asset is an EVM token.
   :resjson string custom_asset_type: This value might not be included in all the results. It represents the custom asset type for a custom asset.
   :resjson string collection_name: Only included for NFTs. May be null if nft has no collection. If it does then this is its name.
   :resjson string image_url: Only included for NFTs. May be null if nft has no image. If it does this is a url to the image.
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
   :reqjson int[optional] chain_id: Chain id of the chain where the asset is located if the asset is an EVM token.


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
                  "chain_id": 1,
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
   :resjson int chain_id: This value might not be included in all the results. Chain id of the chain where the asset is located if the asset is an EVM token.
   :resjson string custom_asset_type: This value might not be included in all the results. It represents the custom asset type for a custom asset.
   :resjson string asset_type: This value represents the asset type. Can be `custom asset`, `nft`, etc.
   :resjson string collection_name: This value might not be included in all the results. It represents the nft collection name.
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
   :reqjson string value: A string to be used to search the assets. Required.
   :reqjson int[optional] chain_id: Chain id of a supported EVM chain used to filter the result
   :reqjson list[string][optional] owner_addresses: A list of evm addresses. If provided, only nfts owned by these addresses will be returned.
   :reqjson string[optional] name: Optional nfts name to filter by.
   :reqjson string[optional] collection_name: Optional nfts collection_name to filter by.
   :reqjson string[optional] ignored_assets_handling: A flag to specify how to handle ignored assets. Possible values are `'none'`, `'exclude'` and `'show_only'`. You can write 'none' in order to not handle them in any special way (meaning to show them too). This is the default. You can write 'exclude' if you want to exclude them from the result. And you can write 'show_only' if you want to only see the ignored assets in the result.

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
                  "chain_id": 1,
                  "is_custom_asset": false
              }
          ],
          "message": ""
      }

   :resjson object result: A list of objects that contain the asset details which match the search keyword ordered by distance to search keyword.
   :resjson string identifier: Identifier of the asset.
   :resjson string name: Name of the asset.
   :resjson string symbol: Symbol of the asset.
   :resjson int chain_id: This value might not be included in all the results. Chain id of the chain where the asset is located if the asset is an EVM token.
   :resjson string custom_asset_type: This value might not be included in all the results. It represents the custom asset type for a custom asset.
   :resjson string asset_type: This value represents the asset type. Can be `custom asset`, `nft`, etc.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 500: Internal rotki error

Detecting owned tokens
======================

.. http:post:: /api/(version)/blockchains/(blockchain)/tokens/detect

   Doing POST on the detect tokens endpoint will detect tokens owned by the provided addresses on the specified blockchain. If no addresses provided, tokens for all user's addresses will be detected.

    .. note::
          This endpoint can also be queried asynchronously by using ``"async_query": true``

  **Example Request**:

  .. http:example:: curl wget httpie python-requests

    GET /api/1/blockchains/eth/tokens/detect HTTP/1.1
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
  :statuscode 401: No user is currently logged in.
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
   :reqjson string symbol: The symbol of the asset. Required.
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

      PATCH /api/1/assets/all HTTP/1.1
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
                   "decimals": 18,
                   "name": "Aave Token",
                   "started": 1600970788,
                   "symbol": "AAVE",
                   "type": "ethereum token"
           },
           "remote": {
                   "coingecko": "aaveNGORZ",
                   "ethereum_address": "0x1Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
                   "decimals": 15,
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Conflicts were found during update. The conflicts should also be returned.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some conflict at replacing.
   :statuscode 500: Internal rotki error

Querying asset icons
======================

.. http:get:: /api/(version)/assets/icon

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
   :statuscode 202: Icon is not in the system and has been requested from coingecko but has not yet been queried.
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
   First, the cache of the icon of the given asset is deleted and then re-queried from CoinGecko and saved to the filesystem.


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

   :statuscode 200: Icon successfully deleted and re-queried.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 404: Unable to refresh icon at the moment.
   :statuscode 500: Internal rotki error


Get asset location mappings for a location
==========================================

.. http:post:: /api/(version)/assets/locationmappings

    Doing a POST on the asset location mappings endpoint will return all the paginated location assets mappings for the given filter.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        POST /api/1/assets/locationmappings/ HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "offset": 20,
          "limit": 2
        }

    :reqjson str location[optional]: If given, filter the returned mappings only for the location. Possible values can be any supported exchange, ``null`` to get the mappings that are common for all exchanges, or omitting it to get all the mappings.
    :reqjson str location_symbol[optional]: Filter the exchange symbols using the provided string.
    :reqjson int limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
    :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "result": {
              "entries": [
                { "asset": "eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96", "location_symbol": "GNO", "location": "binance"},
                { "asset": "eip155:1/erc20:0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE", "location_symbol": "SHIB", "location": "kraken"}
              ],
              "entries_found": 1500,
              "entries_total": 1500
            },
            "message": ""
        }

    :resjson object entries: An array of mapping objects. Each entry is composed of the asset identifier under the ``"asset"`` key, its ticker symbol used in the location under the ``"location_symbol"`` key, and its location under the ``"location"`` key. 
    :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
    :resjson int entries_total: The number of total entries ignoring all filters.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Mappings were returned successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 500: Internal rotki error.


Insert asset location mappings for a location
=============================================

.. http:put:: /api/(version)/assets/locationmappings

    Doing a PUT on the asset location mappings endpoint with a list of entries, and each entry containing an asset's identifier, its location, and its location symbol will save these mappings in the DB.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        PUT /api/1/assets/locationmappings HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "entries": [
            { "asset": "eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", "location_symbol": "UNI", "location": "kucoin"},
            { "asset": "eip155:1/erc20:0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF", "location_symbol": "IMX", "location": "kraken"}
          ]
        }

    :reqjson object entries: A list of mappings containing ``"asset"``, ``"location_symbol"``, and ``"location"`` to be saved in the database

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "result": true,
            "message": ""
        }

    :resjson bool result: A boolean which is true in the case the mappings were added successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Mappings were added successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: Some of the provided mappings already exist in the database or assets have incorrect format.
    :statuscode 500: Internal rotki error.


Update asset location mappings for a location
=============================================

.. http:patch:: /api/(version)/assets/locationmappings

    Doing a PATCH on the asset location mappings endpoint with a list of entries, and each entry containing an asset's identifier, its location, and its location symbol will updates these mappings in the DB.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        PATCH /api/1/assets/locationmappings HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "location": "kucoin",
          "entries": [
            { "asset": "eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984", "location_symbol": "UNI", "location": "kraken"},
            { "asset": "eip155:1/erc20:0xF57e7e7C23978C3cAEC3C3548E3D615c346e79fF", "location_symbol": "IMX", "location": "kucoin"}
          ]
        }

    :reqjson object entries: A list of mappings containing ``"asset"``, ``"location_symbol"``, and ``"location"`` to be updated in the database.

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "result": true,
            "message": ""
        }

    :resjson bool result: A boolean which is true in case the mappings were updated successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Mappings were updated successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: Some of the provided mappings don't exist in the database or assets have incorrect format.
    :statuscode 500: Internal rotki error.


Delete asset location mappings for a location
=============================================

.. http:delete:: /api/(version)/assets/locationmappings

    Doing a DELETE on the asset location mappings endpoint with a list of entries, and each entry containing an asset's location, and its location symbol will delete these mappings from the DB.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        DELETE /api/1/assets/locationmappings HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "entries": [
            {"location_symbol": "UNI", "location": "kraken"},
            {"location_symbol": "IMX", "location": "kucoin"}
          ]
        }

    :reqjson object entries: A list of objects containing ``"location_symbol"`` and ``"location"`` whose mappings should be deleted from the database.

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "result": true,
            "message": ""
        }

    :resjson bool result: A boolean which is true in case the mappings were deleted successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Mappings were deleted successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: Some of the provided asset identifiers don't exist in the database for the given location or their format is incorrect.
    :statuscode 500: Internal rotki error.


Statistics for netvalue over time
====================================

.. http:get:: /api/(version)/statistics/netvalue/

   Doing a GET on the statistics netvalue over time endpoint will return all the saved historical data points with user's history. For non-premium users this returns up to 2 weeks of data in the past.


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
   :Statuscode 401: No user is currently logged in.
   :statuscode 500: Internal rotki error.

Statistics for asset or collection balance over time
=====================================================

.. http:post:: /api/(version)/statistics/balance

   .. note::
      This endpoint is only available for premium users


   Doing a POST on the statistics asset/collection balance over time endpoint will return all saved balance entries for an asset. Optionally you can filter for a specific time range by providing appropriate arguments. Depending on the given argument this will either query a single asset or a collection of assets.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/statistics/balance HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1514764800, "to_timestamp": 1572080165, "asset": "BTC"}

   :reqjson int from_timestamp: The timestamp after which to return saved balances for the asset. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return saved balances for the asset. If not given all balances until now are returned.
   :reqjson string asset: Identifier of the asset. This is mutually exclusive with the collection id. If this is given then only a single asset's balances will be queried. If not given a collection_id MUST be given.
   :reqjson integer collection_id: Collection id to query. This is mutually exclusive with the asset. If this is given then combined balances of all assets of the collection are returned. If not given an asset MUST be given.

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
   :statuscode 401: No user is currently logged in
   :statuscode 403: Logged in user does not have premium.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 403: Logged in user does not have premium.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 403: Logged in user does not have premium.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 409: There is a problem reaching the rotki server.
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
   :reqjson bool include_ignored_trades: Determines whether ignored trades should be included in the result returned. Defaults to ``"true"``.
   :reqjson bool exclude_ignored_assets: Determines whether the trades with ignored assets should be included in the result returned. Defaults to ``"true"``.
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
   :reqjson bool exclude_ignored_assets: Optional. If this is true then the asset movements of ignored assets are not returned, defaults to ``"true"``.


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

Dealing with History Events
============================================

.. http:post:: /api/(version)/history/events

   Doing a POST on this endpoint with the given filter parameters will return all history events matching the filter. All arguments are optional. If nothing is given all events will be returned.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/history/events HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "from_timestamp": 1500,
          "to_timestamp": 999999
      }

   .. _history_base_entry_schema_section:

   :reqjson int limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson object otherargs: Check the documentation of the remaining arguments `here <filter-request-args-label_>`_.
   :reqjson bool customized_events_only: Optional. If enabled the search is performed only for manually customized events. Default false.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "events": [{
                  "entry": {
                      "identifier": 1,
		      "entry_type": "evm event",
                      "asset": "ETH",
                      "balance": {"amount": "0.00863351371344", "usd_value": "0"},
                      "counterparty": "gas",
                      "event_identifier": "10x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
                      "event_subtype": "fee",
                      "event_type": "spend",
                      "location": "ethereum",
                      "location_label": "0x6e15887E2CEC81434C16D587709f64603b39b545",
                      "notes": "Burned 0.00863351371344 ETH for gas",
                      "sequence_index": 0,
                      "timestamp": 1642802807,
                      "event_accounting_rule_status": "not processed",
		      "tx_hash": "0x8d822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
		      "address": null,
		      "product": null
                  },
                  "customized": false,
		  "hidden": true,
                  "ignored_in_accounting": false,
                  "has_details": false,
                  "grouped_events_num": 1
                }, {
                  "entry": {
                      "identifier": 2,
		      "entry_type": "evm event",
                      "asset": "ETH",
                      "balance": {"amount": "0.00163351371344", "usd_value": "0"},
                      "counterparty": "gas",
                      "event_identifier": "10x1c822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
                      "event_subtype": "fee",
                      "event_type": "spend",
                      "location": "ethereum",
                      "location_label": "0xce15887E2CEC81434C16D587709f64603b39b545",
                      "notes": "Burned 0.00863351371344 ETH for gas",
                      "sequence_index": 0,
                      "timestamp": 1642802807,
                      "event_accounting_rule_status": "not processed",
		      "tx_hash": "0x1c822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
		      "address": null,
		      "product": null
                  },
                  "customized": false,
                  "ignored_in_accounting": false,
                  "has_details": false,
                  "grouped_events_num": 3
              }, {
                  "entry": {
                      "identifier": 3,
		      "entry_type": "eth_withdrawal_event",
                      "asset": "ETH",
                      "balance": {"amount": "0.00163351371344", "usd_value": "0"},
                      "event_identifier": "EW_1454_20453",
                      "event_subtype": "remove_asset",
                      "event_type": "staking",
                      "location": "ethereum",
                      "location_label": "0xce15887E2CEC81434C16D587709f64603b39b545",
                      "notes": "Withdrew 0.00163351371344 ETH from validator 1454",
                      "sequence_index": 0,
                      "timestamp": 1652802807,
                      "event_accounting_rule_status": "not processed",
		      "validator_index": 1454,
		      "is_exit": false
                  },
                  "customized": false,
		  "hidden": true,
                  "ignored_in_accounting": false,
                  "has_details": false,
                  "grouped_events_num": 1
              }, {
	          "entry": {
                      "identifier": 4,
		      "entry_type": "eth_block_event",
                      "asset": "ETH",
                      "balance": {"amount": "0.00163351371344", "usd_value": "0"},
                      "event_identifier": "evm_1_block_15534342",
                      "event_subtype": "block_production",
                      "event_type": "staking",
                      "location": "ethereum",
                      "location_label": "0xce15887E2CEC81434C16D587709f64603b39b545",
                      "notes": "Validator 1454 produced block 15534342 with 0.00163351371344 going to 0xce15887E2CEC81434C16D587709f64603b39b545 as the block reward",
                      "sequence_index": 0,
                      "timestamp": 1652802807,
                      "event_accounting_rule_status": "not processed",
		      "validator_index": 1454,
		      "block_number": 15534342
                  },
                  "customized": false,
                  "ignored_in_accounting": false,
                  "has_details": false,
                  "grouped_events_num": 2
              },  {
                  "entry": {
                      "identifier": 5,
		      "entry_type": "eth deposit event",
                      "asset": "ETH",
                      "balance": {"amount": "32", "usd_value": "0"},
                      "counterparty": "eth2",
                      "event_identifier": "10x2c822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
                      "event_subtype": "deposit asset",
                      "event_type": "staking",
                      "location": "ethereum",
                      "location_label": "0xA215887E2CEC81434C16D587709f64603b39b545",
                      "notes": "Deposit 32 ETH to validator 4242",
                      "sequence_index": 15,
                      "timestamp": 1642802807,
                      "event_accounting_rule_status": "not processed",
		      "tx_hash": "0x2c822b87407698dd869e830699782291155d0276c5a7e5179cb173608554e41f",
		      "address": "0x00000000219ab540356cBB839Cbe05303d7705Fa",
		      "product": "staking",
		      "validator_index": 4242
                  },
                  "customized": false,
                  "ignored_in_accounting": false,
                  "has_details": false,
                  "grouped_events_num": 3
              }],
             "entries_found": 95,
             "entries_limit": 500,
             "entries_total": 1000
          },
          "message": ""
      }

   :resjson list decoded_events: A list of history events. Each event is an object comprised of the event entry and a boolean denoting if the event has been customized by the user or not. Each entry may also have a `has_details` flag if true. If `has_details` is true, then it is possible to call /history/events/details endpoint to retrieve some extra information about the event. Also each entry may have a `customized` flag set to true. If it does, it means the event has been customized/added by the user. Each entry may also have a `hidden` flag if set to true. If it does then that means it should be hidden in the UI due to consolidation of events. Finally if `group_by_event_ids` exist and is true, each entry contains `grouped_events_num` which is an integer with the amount of events under the common event identifier. The consumer has to query this endpoint again with `group_by_event_ids` set to false and with the `event_identifiers` filter set to the identifier of the events having more than 1 event. Finally `ignored_in_accounting` is set to `true` when the user has marked this event as ignored. Following are all possible entries depending on entry type.
   :resjson string identifier: Common key. This is the identifier of a single event.
   :resjson string entry_type: Common key. This identifies the category of the event and determines the schema. Possible values are: ``"history event"``, ``"evm event"``, ``"eth withdrawal event"``, ``"eth block event"``, ``"eth deposit event"``.
   :resjson string event_identifier: Common key. An event identifier grouping multiple events under a common group. This is how we group transaction events under a transaction, staking related events under block production etc.
   :resjson int sequence_index: Common key. This is an index that tries to provide the order of history entries for a single event_identifier.
   :resjson int timestamp: Common key. The timestamp of the entry
   :resjson string event_accounting_rule_status: Common key. It explains the status of accounting rules for the event. Possible values are: ``has rule``: Meaning the event has a rule. ``processed``: meaning the event will be processed because it is affected by another event. ``not processed`` meaning it doesn't have any rule and won't be processed by accounting.
   :resjson string location: Common key. The location of the entry. Such as "ethereum", "optimism", etc.
   :resjson string asset: Common key. The asset involved in the event.
   :resjson object balance: Common key. The balance of the asset involved in the event.
   :resjson string event_type: Common key. The type of the event. Valid values are retrieved from the backend.
   :resjson string event_subtype: Common key. The subtype of the event. Valid values are retrieved from the backend.
   :resjson string location_label: Common key. The location_label of the event. This means different things depending on event category. For evm events it's the initiating address. For withdrawal events the recipient address. For block production events the fee recipient.
   :resjson string notes: Common key. String description of the event.
   :resjson string tx_hash: Evm event & eth deposit key. The transaction hash of the event as a hex string.
   :resjson string counterparty: Evm event & eth deposit key. The counterparty of the event. This is most of the times a protocol such as uniswap, but can also be an exchange name such as kraken. Possible values are requested by the backend.
   :resjson string product: Evm event & eth deposit key. This is the product type with which the event interacts. Such as pool, staking contract etc. Possible values are requested by the backend.
   :resjson string address: Evm event & eth deposit key. This is the address of the contract the event interacts with if there is one.
   :resjson int validator_index: Eth staking (withdrawal + block production + eth deposit) key. The index of the validator related to the event.
   :resjson bool is_exit: Eth withdrawal event key. A boolean denoting if the withdrawal is a full exit or not.
   :resjson int block_number: Eth block event key. An integer representing the number of the block for which the event is made.

   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_limit: The limit of entries if free version. -1 for premium.
   :resjson int entries_total: The number of total entries ignoring all filters.
   :statuscode 200: Events successfully queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in or failure at event addition.
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/history/events

   .. _add_event_args_label:

   Doing a PUT on this endpoint can add a new event to rotki. For each entry type, the specified arguments are different. The unique identifier for the entry is returned as success.

   .. tab:: History Event

      **Example Request**:

      .. http:put:: /api/(version)/history/events

         .. http:example:: curl wget httpie python-requests

            PUT /api/1/history/events HTTP/1.1
            Host: localhost:5042
            Content-Type: application/json;charset=UTF-8

            {
               "entry_type": "history event",
               "event_identifier": "RE_xxxxxxxxxx",
               "location": "ethereum",
               "timestamp": 1569924574,
               "balance": {"amount": "1.542", "usd_value": "1.675"},
               "sequence_index": 162,
               "event_type": "informational",
               "event_subtype": "approve",
               "asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
               "location_label": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12",
               "notes": "Approve 1 SAI of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 for spending by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE"
            }

         :reqjson int sequence_index: This is an index that tries to provide the order of history entries for a single event_identifier.
         :reqjson string location: The location of the entry. Such as "ethereum", "optimism", etc.
         :reqjson string asset: The asset identifier for this entry
         :reqjson string event_identifier: The event identifier to be used for the event.
         :reqjson string event_type: The main event type of the entry. Possible event types can be seen in the `HistoryEventType enum <https://github.com/rotki/rotki/blob/59aa288dacd1776e62682e711a916f32a14c04c2/rotkehlchen/accounting/structures/types.py#L54>`_.
         :reqjson string event_subtype: The subtype for the entry. Possible event types can be seen in the `HistoryEventSubType enum <https://github.com/rotki/rotki/blob/59aa288dacd1776e62682e711a916f32a14c04c2/rotkehlchen/accounting/structures/types.py#L72>`_.
         :reqjson string[optional] location_label: location_label is a string field that allows to provide more information about the location. For example when we use this structure in blockchains can be used to specify the source address.
         :reqjson string[optional] notes: This is a description of the event entry in plain text explaining what is being done. This is supposed to be shown to the user.

   .. tab:: Evm Event

      **Example Request**:

      .. http:put:: /api/(version)/history/events

         .. http:example:: curl wget httpie python-requests

            PUT /api/1/history/events HTTP/1.1
            Host: localhost:5042
            Content-Type: application/json;charset=UTF-8

            {
               "entry_type": "evm event",
               "tx_hash": "0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e",
               "event_identifier": "10x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e",
               "sequence_index": 162,
               "timestamp": 1569924574,
               "location": "ethereum",
               "event_type": "informational",
               "asset": "eip155:1/erc20:0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359",
               "balance": {"amount": "1.542", "usd_value": "1.675"},
               "location_label": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12",
               "notes": "Approve 1 SAI of 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12 for spending by 0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE",
               "event_subtype": "approve",
               "counterparty": "0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE",
               "extra_data": {}
            }

         :reqjson string tx_hash: This is the transaction hash of the evm event
         :reqjson string[optional] event_identifier: The event identifier to be used for the event.
         :reqjson int sequence_index: This is an index that tries to provide the order of history entries for a single event_identifier.
         :reqjson string location: The location of the entry. Such as "ethereum", "optimism", etc.
         :reqjson string asset: The asset identifier for this entry
         :reqjson string event_type: The main event type of the entry. Possible event types can be seen in the `HistoryEventType enum <https://github.com/rotki/rotki/blob/59aa288dacd1776e62682e711a916f32a14c04c2/rotkehlchen/accounting/structures/types.py#L54>`_.
         :reqjson string event_subtype: The subtype for the entry. Possible event types can be seen in the `HistoryEventSubType enum <https://github.com/rotki/rotki/blob/59aa288dacd1776e62682e711a916f32a14c04c2/rotkehlchen/accounting/structures/types.py#L72>`_.
         :reqjson string[optional] location_label: location_label is a string field that allows to provide more information about the location. For example when we use this structure in blockchains can be used to specify the source address.
         :reqjson string[optional] notes: This is a description of the event entry in plain text explaining what is being done. This is supposed to be shown to the user.
         :reqjson string[optional] counterparty: An identifier for a potential counterparty of the event entry. For a send it's the target. For a receive it's the sender. For bridged transfer it's the bridge's network identifier. For a protocol interaction it's the protocol.
         :reqjson string[optional] address: Any relevant address that this event interacted with.
         :reqjson object[optional] extra_data: An object containing any other data to be stored.

   .. tab:: Eth Block Event

      **Example Request**:

      .. http:put:: /api/(version)/history/events

         .. http:example:: curl wget httpie python-requests

            PUT /api/1/history/events HTTP/1.1
            Host: localhost:5042
            Content-Type: application/json;charset=UTF-8

            {
               "entry_type": "eth block event",
               "event_identifier": "BLOCK_11",
               "timestamp": 1569924574,
               "balance": {"amount": "1.542", "usd_value": "1.675"},
               "block_number": 11,
               "validator_index": 1,
               "fee_recipient": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12",
               "is_mev_reward": true
            }

         :reqjson string[optional] event_identifier: The event identifier to be used for the event.
         :reqjson int block_number: This is the number of the block where the event took place.
         :reqjson int validator_index: This is the index of the validator.
         :reqjson string fee_recipient: an evm address field to specify the fee recipient in an "eth block event".
         :reqjson bool is_mev_reward: true if the "eth block event" is an mev reward event.

   .. tab:: Eth Deposit Event

      **Example Request**:

      .. http:put:: /api/(version)/history/events

         .. http:example:: curl wget httpie python-requests

            PUT /api/1/history/events HTTP/1.1
            Host: localhost:5042
            Content-Type: application/json;charset=UTF-8

            {
               "entry_type": "eth deposit event",
               "timestamp": 1569924574,
               "balance": {"amount": "1.542", "usd_value": "1.675"},
               "tx_hash": "0x64f1982504ab714037467fdd45d3ecf5a6356361403fc97dd325101d8c038c4e",
               "event_identifier": "RE_xxxxxxxxxx",
               "validator_index": 1,
               "sequence_index": 162,
               "depositor": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12",
               "extra_data": {}
            }

         :reqjson string tx_hash: This is the transaction hash of the evm event
         :reqjson int sequence_index: This is an index that tries to provide the order of history entries for a single event_identifier.
         :reqjson int validator_index: This is the index of the validator.
         :reqjson string[optional] event_identifier: The event identifier to be used for the event.
         :reqjson string depositor: an evm address field to specify the depositor in an "eth deposit event".
         :reqjson object[optional] extra_data: An object containing any other data to be stored.

   .. tab:: Eth Withdrawal Event

      **Example Request**:

      .. http:put:: /api/(version)/history/events

         .. http:example:: curl wget httpie python-requests

            PUT /api/1/history/events HTTP/1.1
            Host: localhost:5042
            Content-Type: application/json;charset=UTF-8

            {
               "entry_type": "eth withdrawal event",
               "timestamp": 1569924574,
               "balance": {"amount": "1.542", "usd_value": "1.675"},
               "is_exit": true,
               "validator_index": 1,
               "withdrawal_address": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12",
               "event_identifier": "EW_XX_XXXXX"
            }

         :reqjson string[optional] event_identifier: The event identifier to be used for the event.
         :reqjson int validator_index: This is the index of the validator.
         :reqjson string withdrawal_address: an evm address field to specify the withdrawer in an "eth withdrawal event".
         :reqjson bool is_exit: true if the "eth withdrawal event" is an exit event.

   :reqjson string entry_type: The type of the event that will be processed. Different validation is used based on the value for this field. Possible values are: ``"history event"``, ``"evm event"``, ``"eth withdrawal event"``, ``"eth block event"``, ``"eth deposit event"``.
   :reqjson int timestamp: The timestamp of the entry **in milliseconds**.
   :reqjson object balance: The amount/usd value of the event. If not known usd_value can also be "0".

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
          "entry_type": "evm event",
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

   The request object uses all the same arguments for each entry type as the `add event endpoint <add_event_args_label_>`_, with the addition of the identifier which signifies which entry will be edited.

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

   Doing a DELETE on this endpoint deletes a set of history entry events from the DB for the currently logged in user. If any of the identifiers is not found in the DB the entire call fails. If any of the identifiers are the last for their transaction hash the call fails, unless the ``force_delete`` argument is given.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/history/events HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"identifiers" : [55, 65, 124]}

   :reqjson list<integer> identifiers: A list of the identifiers of the history entries to delete.
   :reqjson bool force_delete: If true, then even if an event is the last event of a transaction it will be deleted. False by default.

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
   :statuscode 409: No user is logged in or one of the identifiers to delete did not correspond to an event in the DB or one of the identifiers was for the last event in the corresponding transaction hash and force_delete was false..
   :statuscode 500: Internal rotki error

Exporting History Events
============================================

.. http:post:: /api/(version)/history/events/export

   Doing a POST on this endpoint with the given filter parameters will export a csv with all history events matching the filter to a file in the provided directory. Only the 'directory_path' argument is required. If no filter is used all the events will be exported.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/history/events/export HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "directory_path": "/home",
          "from_timestamp": 1500,
          "to_timestamp": 999999
      }

   .. _history_export_schema_section:

   :reqjson string directory_path: The directory in which to write the exported CSV file
   :reqjson object otherargs: Check the documentation of the remaining arguments `here <filter-request-args-label_>`_.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message" "",
      }

   :statuscode 200: Events successfully exported
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in or failure at event export.
   :statuscode 500: Internal rotki error

.. http:put:: /api/(version)/history/events/export

   Doing a PUT on this endpoint with the given filter parameters will download a csv with all history events matching the filter. All arguments are optional. If no filter is used all the events will be downloaded.

   .. _filter-request-args-label:

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/history/events/export HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "from_timestamp": 1500,
          "to_timestamp": 999999
      }

   :reqjson list[string] order_by_attributes: This is the list of attributes of the transaction by which to order the results.
   :reqjson list[bool] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.
   :reqjson bool group_by_event_ids: A boolean determining if results should be grouped by common event identifiers. If true, the result will return only the first event of each group but also the number of events the group has. Default is false.
   :reqjson int from_timestamp: The timestamp from which to start querying. Default is 0.
   :reqjson int to_timestamp: The timestamp until which to query. Default is now.
   :reqjson list[string] event_identifiers: An optional list of event identifiers to filter for.
   :reqjson list[string] event_types: An optional list of event types by which to filter the decoded events.
   :reqjson list[string] event_subtypes: An optional list of event subtypes by which to filter the decoded events.
   :reqjson list location: An optional location name to filter events only for that location.
   :reqjson list[string] location_labels: A list of location labels to optionally filter by. Location label is a string field that allows you to provide more information about the location. When used in blockchains, it is used to specify the user's address. For exchange events, it's the exchange name assigned by the user.
   :reqjson object entry_types: An object with two keys named 'values' and 'behavior'. 'values' is a list of entry types to optionally filter by. 'behavior' is optional and is a string with the value 'include' or 'exclude' which defines the filtering behavior. It defaults to 'include'. Entry type is the event category and defines the schema. Possible values are: "history event," "evm event," "eth withdrawal event," "eth block event," "eth deposit event."
   :reqjson string asset: The asset to optionally filter by.
   :reqjson list[string] tx_hashes: An optional list of transaction hashes to filter for. This will make it an EVM event query.
   :reqjson list[string] counterparties: An optional list of counterparties to filter by. List of strings. This will make it an EVM event query. We currently have a special exception for "eth2" as a counterparty. It filters for all eth staking events if given. It can't be given along with other counterparties in a filter. Or with an entry types filter.
   :reqjson list[string] products: An optional list of product type to filter by. List of strings. This will make it an EVM event query.
   :reqjson list[string] addresses: An optional list of EVM addresses to filter by in the set of counterparty addresses. This will make it an EVM event query.
   :reqjson list[int] validator_indices: An optional list of validator indices to filter by. This makes it an EthStakingevent query.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: text/csv

   :statuscode 200: Events successfully downloaded
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in or failure at event download.
   :statuscode 500: Internal rotki error

Querying online events
============================================

.. http:post:: /api/(version)/history/events/query

   Doing a POST on this endpoint will query latest online events for the given event type and save them in the DB

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/history/events/query HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "async_query": true,
          "query_type": "eth_withdrawals"
      }


   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson string query_type: The name of the type of events to query for. Valid values are: ``"eth_withdrawals"``, ``"block_productions"``, ``"exchanges"``

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
         "result": true,
         "message": ""
      }

   :resjson bool result: A boolean for success or failure
   :resjson str message: Error message if any errors occurred.
   :statuscode 200: Events were queried successfully
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: Module for the given events is not active.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as beaconchain could not be reached or returned an unexpected response.

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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: Fatal accounting error while processing the report.
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
                ],
                "historical_price_oracles": ["manual", "cryptocompare", "coingecko"],
                "pnl_csv_with_formulas": true,
                "pnl_csv_have_summary": false,
                "ssf_graph_multiplier": 0,
                "last_data_migration": 3,
                "non_syncing_exchanges": []
                "evmchains_to_skip_detection": []
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
   :statuscode 409: No user is currently logged in. Error occurred when creating history events for pnl debug data.
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
   :resjosnarr bool rate_limited: True if we couldn't get the price and any of the oracles got rate limited.
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

   :reqjson int report_id: An optional id to limit the query to that specific report.

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

   :reqjson int report_id: Optional. The id of the report to query as a view arg.
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

   :reqjson int report_id: The id of the report to delete as a view arg.

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
              "connected_nodes": {
                  "eth": ["nodeX", "nodeY"],
                  "optimism": ["nodeW", "nodeZ"],
                  "polygon_pos": ["nodeA", "nodeB"],
              },
              "last_data_upload_ts": 0
          }
          "message": ""
      }

   :resjson int last_balance_save: The last time (unix timestamp) at which balances were saved in the database.
   :resjson int last_data_upload_ts: The last time (unix timestamp) at which a new DB was pushed to the remote as backup.
   :resjson object connected_nodes: A dictionary containing the evm chain name and a list of connected nodes.
   :statuscode 200: Data were queried successfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal rotki error.


Getting blockchain account data
===============================
.. http:get:: /api/(version)/blockchains/(name)/accounts

   .. note::
      Supported blockchains: ``"BTC", "BCH", "ETH", "KSM", "DOT", "AVAX", "OPTIMISM"``

   Doing a GET on the blockchains endpoint with a specific blockchain queries account data information for that blockchain.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/accounts HTTP/1.1
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
   :resjsonarr list tags: A list of tags associated with the account. Can also be null. Should never by an empty list.

   :statuscode 200: Account data successfully queried.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/BTC/accounts HTTP/1.1
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
   :resjsonarr list tags: [Optional] A list of tags associated with the account. Can also be null. Should never be an empty list.
   :resjsonarr list addresses: [Optional] A list of address objects  derived by the account. Can also be null. The attributes of each object are as seen in the previous response.

   :statuscode 200: Account data successfully queried.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

Getting all DeFi balances
=========================

.. http:get:: /api/(version)/blockchains/eth/defi

   Doing a GET on the DeFi balances endpoint will return a mapping of all accounts to their respective balances in DeFi protocols.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/defi HTTP/1.1
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

.. http:get:: /api/(version)/blockchains/eth/modules/makerdao/dsrbalance

   Doing a GET on the makerdao dsrbalance resource will return the current balance held in DSR by any of the user's accounts that ever had DAI deposited in the DSR and also the current DSR percentage.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/makerdao/dsrbalance HTTP/1.1
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

.. http:get:: /api/(version)/blockchains/eth/modules/makerdao/dsrhistory

   .. note::
      This endpoint is only available for premium users

   Doing a GET on the makerdao dsrhistory resource will return the history of deposits and withdrawals of each account to the DSR along with the amount of DAI gained at each step and other information

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/makerdao/dsrhistory HTTP/1.1
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
   :statuscode 401: No user is currently logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 409: Makerdao module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting MakerDAO vaults basic data
===================================

.. http:get:: /api/(version)/blockchains/eth/modules/makerdao/vaults

   Doing a GET on the makerdao vault resource will return the basic information for each vault the user has

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/makerdao/vaults HTTP/1.1
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

.. http:get:: /api/(version)/blockchains/eth/modules/makerdao/vaultdetails

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

      GET /api/1/blockchains/eth/modules/makerdao/vaultdetails HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 409: Makerdao module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting Aave balances
========================

.. http:get:: /api/(version)/blockchains/eth/modules/aave/balances

   Doing a GET on the aave balances resource will return the balances that the user has locked in Aave for lending and borrowing along with their current APYs.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/aave/balances HTTP/1.1
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

Getting Aave stats
========================

.. http:get:: /api/(version)/blockchains/eth/modules/aave/stats

   Doing a GET on the aave stats resource will return the interest payments of each account in Aave's lending.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/aave/stats HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson int from_timestamp: Timestamp from which to query aave historical data. If not given 0 is implied.
   :reqjson int to_timestamp: Timestamp until which to query aave historical data. If not given current timestamp is implied.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056": {
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
                  },
                  "total_earned_liquidations": {},
              },
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
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
   :resjson object total_earned_interest: A mapping of asset identifier to total earned (amount + usd_value mapping) for each asset's interest earnings. The total earned is essentially the sum of all interest payments plus the difference between ``balanceOf`` and ``principalBalanceOf`` for each asset.
   :resjson object total_lost: A mapping of asset identifier to total lost (amount + usd_value mapping) for each asset. The total losst for each asset is essentially the accrued interest from borrowing and the collateral lost from liquidations.
   :resjson object total_earned_liquidations: A mapping of asset identifier to total earned (amount + usd_value mapping) for each repaid asset during liquidations.

   :statuscode 200: Aave history successfully queried.
   :statuscode 400: Requested module is not allowed to query statistics.
   :statuscode 401: No user is currently logged in or currently logged in user does not have a premium subscription.
   :statuscode 409: Aave module is not activated.
   :statuscode 500: Internal rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting Balancer balances
==============================

.. http:get:: /api/(version)/blockchains/eth/modules/balancer/balances

   Doing a GET on the balancer balances resource will return the balances locked in Balancer Liquidity Pools (LPs or pools).

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/balancer/balances HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 409: Balancer module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as the graph node could not be reached or returned unexpected response.


Getting Compound balances
==============================

.. http:get:: /api/(version)/blockchains/eth/modules/compound/balances

   Doing a GET on the compound balances resource will return the balances that the user has locked in Compound for lending and borrowing along with their current APYs. The APYs are return in a string percentage with 2 decimals of precision. If for some reason APY can't be queried ``null`` is returned.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/compound/balances HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Compound module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting compound statistics
=============================

.. http:get:: /api/(version)/blockchains/ETH/modules/compound/stats

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the compound stats resource will return information related profit and loss of the events present in the database.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/ETH/modules/compound/stats HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson int from_timestamp: Timestamp from which to query compound historical data. If not given 0 is implied.
   :reqjson int to_timestamp: Timestamp until which to query compound historical data. If not given current timestamp is implied.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
          "interest_profit":{
            "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056":{
              "eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888":{
                "amount":"3.5",
                "usd_value":"892.5"
              },
              "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F":{
                "amount":"250",
                "usd_value":"261.1"
              }
            },
            "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237":{
              "eip155:1/erc20:0xE41d2489571d322189246DaFA5ebDe1F4699F498":{
                "amount":"0.55",
                "usd_value":"86.1"
              }
            }
          },
          "debt_loss":{
            "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237":{
              "ETH":{
                "amount":"0.1",
                "usd_value":"30.5"
              }
            }
          },
          "liquidation_profit":{
            "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237":{
              "ETH":{
                "amount":"0.00005",
                "usd_value":"0.023"
              }
            }
          },
          "rewards":{
            "0xA0B6B7fEa3a3ce3b9e6512c0c5A157a385e81056":{
              "eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888":{
                "amount":"3.5",
                "usd_value":"892.5"
              }
            }
          }
        },
        "message":""
      }

   :resjson object interest_profit: A mapping of addresses to mappings of totals assets earned from lending over a given period
   :resjson object debt_loss: A mapping of addresses to mappings of totals assets lost to repayment fees and liquidation over a given period.
   :resjson object liquidation_profit: A mapping of addresses to mappings of totals assets gained thanks to liquidation repayments over a given period.
   :resjson object rewards: A mapping of addresses to mappings of totals assets (only COMP atm) gained as a reward for using Compound over a given period.

   :statuscode 200: Compound statistics successfully queried.
   :statuscode 400: Requested module is not allowed to query statistics.
   :statuscode 401: User is not logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 409: Compound module is not activated.
   :statuscode 500: Internal rotki error.


Getting Liquity balances
========================

.. http:get:: /api/(version)/blockchains/eth/modules/liquity/balances

   Doing a GET on the liquity balances resource will return the balances that the user has in troves.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint will provide different information if called with a premium account or not. With premium accounts information about staking is provided.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/liquity/balances HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Liquity module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting Liquity staked amount
=============================

.. http:get:: /api/(version)/blockchains/eth/modules/liquity/staking

   Doing a GET on the liquity balances resource will return the balances that the user has staked.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   .. note::
      This endpoint requires a premium account.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/liquity/staking HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
            "0x063c26fF1592688B73d8e2A18BA4C23654e2792E": {
                "balances": {
                  "staked": {
                    "asset": "ETH",
                    "amount": "43.180853032438783295",
                    "usd_value": "43.180853032438783295",
                  },
                  "lusd_rewards": {
                    "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                    "amount": "94477.70111867384658505",
                    "usd_value": "94477.70111867384658505",
                  },
                  "eth_rewards": {
                    "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
                    "amount": "10211401.723115634393264567",
                    "usd_value": "10211401.723115634393264567",
                  }
                },
                "proxies": {
                    "0x063c26fF1592688B73d8e2A18BA4C23654e2792E": {
                      "staked": {
                        "asset": "ETH",
                        "amount": "43.180853032438783295",
                        "usd_value": "43.180853032438783295",
                      },
                      "lusd_rewards": {
                        "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                        "amount": "94477.70111867384658505",
                        "usd_value": "94477.70111867384658505",
                      },
                      "eth_rewards": {
                        "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
                        "amount": "10211401.723115634393264567",
                        "usd_value": "10211401.723115634393264567",
                      }
                }
            }
          },
          "message": ""
      }

   :resjson object optional[balances]: A mapping of the category to the amount & value of assets staked in the protocol.
   :resjson object optional[proxies]: A mapping of proxy addresses to the amount and value of assets staked in the protocol.

   :statuscode 200: Liquity staking information successfully queried.
   :statuscode 401: User is not logged in.
   :statuscode 409: Liquity module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting Liquity stability pool information
==========================================

.. http:get:: /api/(version)/blockchains/eth/modules/liquity/pool

   Doing a GET on the liquity stability pool resource will return the balances deposited in it and the rewards accrued.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint requires a premium account.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/liquity/pool HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
            "0x063c26fF1592688B73d8e2A18BA4C23654e2792E": {
                "balances": {
                  "gains": {
                    "asset": "ETH",
                    "amount": "43.180853032438783295",
                    "usd_value": "43.180853032438783295",
                  },
                  "rewards": {
                    "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                    "amount": "94477.70111867384658505",
                    "usd_value": "94477.70111867384658505",
                  },
                  "deposited": {
                    "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
                    "amount": "10211401.723115634393264567",
                    "usd_value": "10211401.723115634393264567",
                  }
                },
                "proxies": {
                    "0x063c26fF1592688B73d8e2A18BA4C23654e2792E": {
                      "gains": {
                        "asset": "ETH",
                        "amount": "43.180853032438783295",
                        "usd_value": "43.180853032438783295",
                      },
                      "rewards": {
                        "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                        "amount": "94477.70111867384658505",
                        "usd_value": "94477.70111867384658505",
                      },
                      "deposited": {
                        "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
                        "amount": "10211401.723115634393264567",
                        "usd_value": "10211401.723115634393264567",
                      }
                }
            }
          },
          "message": ""
      }

   :resjson object balances: A mapping of the category to the amount & value of assets staked in the protocol.
   :resjson object proxies: A mapping of proxy addresses to the amount and value of assets staked in the protocol.
   :resjson object deposited: Information about the amount and usd value of the LUSD deposited.
   :resjson object gains: Information about the amount and usd value of the ETH gained as reward for liquidations.
   :resjson object rewards: Information about the amount and usd value of the LQTY rewards gained.

   :statuscode 200: Liquity information successfully queried.
   :statuscode 401: User is not logged in.
   :statuscode 409: Liquity module is not activated.
   :statuscode 500: Internal rotki error.


Getting Liquity staking information
====================================

.. http:get:: /api/(version)/blockchains/eth/modules/liquity/stats

   Doing a GET on the liquity stats resource will return the statistics for staking in the stability pool and the LQTY staking service.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint requires a premium account.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/liquity/stats HTTP/1.1
      Host: localhost:5042

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "global_stats": {
            "total_usd_gains_stability_pool": "41902.74041824219",
            "total_usd_gains_staking": "190.09104568340678",
            "total_deposited_stability_pool": "1915600.7290263602",
            "total_withdrawn_stability_pool": "914454.5094041774",
            "total_deposited_stability_pool_usd_value": "0.0",
            "total_withdrawn_stability_pool_usd_value": "0.0",
            "staking_gains": [
              {
                "asset": "ETH",
                "amount": "0.19015022103888912",
                "usd_value": "23.001055387590114"
              },
              {
                "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
                "amount": "168.7710091203543",
                "usd_value": "167.08999029581668"
              },
              {
                "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                "amount": "1445.7823568041297",
                "usd_value": "0.0"
              }
            ],
            "stability_pool_gains": [
              {
                "asset": "ETH",
                "amount": "14.0767134582469",
                "usd_value": "31051.389153894255"
              },
              {
                "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                "amount": "11887.091269011284",
                "usd_value": "10851.35126434794"
              }
            ]
          },
          "by_address": {
            "0xF662f831361c8Ab48d807f7753eb3d641be25d24": {
              "total_usd_gains_stability_pool": "0.0",
              "total_usd_gains_staking": "0.0",
              "total_deposited_stability_pool": "1519146.7290263602",
              "total_withdrawn_stability_pool": "914454.5094041774",
              "total_deposited_stability_pool_usd_value": "0.0",
              "total_withdrawn_stability_pool_usd_value": "0.0",
              "staking_gains": [
                {
                  "asset": "ETH",
                  "amount": "0.18236022449762773",
                  "usd_value": "0.0"
                },
                {
                  "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
                  "amount": "2.23017071973649",
                  "usd_value": "0.0"
                },
                {
                  "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                  "amount": "1445.7823568041297",
                  "usd_value": "0.0"
                }
              ],
              "stability_pool_gains": [
                {
                  "asset": "ETH",
                  "amount": "1.7820064710306824",
                  "usd_value": "0.0"
                },
                {
                  "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                  "amount": "7646.741845927703",
                  "usd_value": "0.0"
                }
              ]
            },
            "0xbB8311c7bAD518f0D8f907Cad26c5CcC85a06dC4": {
              "total_usd_gains_stability_pool": "41902.74041824219",
              "total_usd_gains_staking": "190.09104568340678",
              "total_deposited_stability_pool": "396454.0",
              "total_withdrawn_stability_pool": "0",
              "total_deposited_stability_pool_usd_value": "0.0",
              "total_withdrawn_stability_pool_usd_value": "0",
              "staking_gains": [
                {
                  "asset": "ETH",
                  "amount": "0.007789996541261418",
                  "usd_value": "23.001055387590114"
                },
                {
                  "asset": "eip155:1/erc20:0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",
                  "amount": "166.54083840061782",
                  "usd_value": "167.08999029581668"
                }
              ],
              "stability_pool_gains": [
                {
                  "asset": "ETH",
                  "amount": "12.294706987216218",
                  "usd_value": "31051.389153894255"
                },
                {
                  "asset": "eip155:1/erc20:0x6DEA81C8171D0bA574754EF6F8b412F2Ed88c54D",
                  "amount": "4240.34942308358",
                  "usd_value": "10851.35126434794"
                }
              ]
            }
          }
        },
        "message": ""
      }

   :resjson object result: A mapping with the keys ``global_stats`` and ``by_address``.
   :resjson object global_stats: Stats aggregating the information for all the addresses tracked in the liquity module.
   :resjson object global_stats: Breakdown by tracked address of the stats.
   :resjson string total_usd_gains_stability_pool: Sum of all the gains valued at the moment of the event for the stability pool.
   :resjson string total_usd_gains_staking: Sum of all the gains valued at the moment of the event for liquity staking.
   :resjson string total_deposited_stability_pool: Total amount of LUSD deposited in the stability pool.
   :resjson string total_withdrawn_stability_pool: Total amount of LUSD withdrawn from the stability pool.
   :resjson string total_deposited_stability_pool_usd_value: Sum of the USD value deposited in the stability pool at the time of the events.
   :resjson string total_withdrawn_stability_pool_usd_value: Sum of the USD value withdrawn from the stability pool at the time of the events.
   :resjson list[object] staking_gains: Breakdown by asset of the gains claimed by staking.
   :resjson list[object] stability_pool_gains: Breakdown by asset of the gains claimed by depositing in the stability pool.

   :statuscode 200: Liquity staking stats successfully queried.
   :statuscode 400: Requested module is not allowed to query statistics.
   :statuscode 401: User is not logged in.
   :statuscode 409: Liquity module is not activated.
   :statuscode 500: Internal rotki error.


Getting Uniswap balances
==============================

.. http:get:: /api/(version)/blockchains/eth/modules/uniswap/v2/balances

   Doing a GET on the uniswap balances resource will return the balances locked in Uniswap Liquidity Pools (LPs or pools).

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/uniswap/v2/balances HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Uniswap module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.

Getting Uniswap V3 balances
==============================

.. http:get:: /api/(version)/blockchains/eth/modules/uniswap/v3/balances

   Doing a GET on the uniswap v3 balances resource will return the balances locked in Uniswap V3 Liquidity Pools (LPs or pools).

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/uniswap/v3/balances HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Uniswap module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

Getting Uniswap/Sushiswap events
================================

.. http:get:: /api/(version)/blockchains/eth/modules/{module}/stats

   Doing a GET on the uniswap/sushiswap stats endpoint will return information about the profit and loss on uniswap/sushiswap events for the selected range.

   .. note::
      This endpoint is only available for premium users

   .. note::
      module can only be one of ``uniswap`` or ``sushiswap`` for this endpoint.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/uniswap/history/events HTTP/1.1
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


   :resjson object result: A mapping between accounts and their Uniswap events stats per pool.
   :resjson string pool_address: The contract address of the pool.
   :resjson string profit_loss0: The token0 profit/loss.
   :resjson string profit_loss1: The token1 profit/loss.
   :resjson object token0: The pool's pair left token identifier
   :resjson object token1: The pool's pair right token identifier.
   :resjson string usd_profit_loss: The total profit/loss in USD.


   :statuscode 200: Uniswap events successfully queried.
   :statuscode 400: Requested module is not allowed to query statistics.
   :statuscode 401: User is not logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 409: Uniswap module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan or the graph node could not be reached or returned unexpected response.


Getting yearn finance vaults balances
==========================================

.. http:get:: /api/(version)/blockchains/eth/modules/yearn/vaults/balances

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the yearn finance vaults balances resource will return all yearn vault balances.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/yearn/vaults/balances HTTP/1.1
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
                      "roi": "25.55%"
                  },
                  "YYFI Vault": {
                      "underlying_token": "eip155:1/erc20:0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e",
                      "vault_token": "eip155:1/erc20:0xBA2E7Fed597fd0E3e70f5130BcDbbFE06bB94fe1",
                      "underlying_value": {
                          "amount": "25", "usd_value": "150"
                      },
                      "vault_value": {
                          "amount": "19", "usd_value": "150"
                      }
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
                      "roi": "35.15%"
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
   :resjsonarr optional[string] roi: An optional string. The Return of Investment for the vault since its creation.


   :statuscode 200: Yearn vault balances successfully queried.
   :statuscode 401: User is not logged in.
   :statuscode 409: Yearn module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting yearn finance V2 vaults balances
==========================================

.. http:get:: /api/(version)/blockchains/eth/modules/yearn/vaultsv2/balances

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the yearn finance vaults V2 balances resource will return all yearn vault balances.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/yearn/vaultsv2/balances HTTP/1.1
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
   :resjsonarr optional[string] roi: An optional string. The Return of Investment for the vault since its creation.


   :statuscode 200: Yearn vault V2 balances successfully queried.
   :statuscode 401: User is not logged in.
   :statuscode 409: Yearn module is not activated.
   :statuscode 500: Internal Rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Getting Loopring balances
==============================

.. http:get:: /api/(version)/blockchains/eth/modules/loopring/balances

   Doing a GET on the loopring balances resource will return the balances in loopring L2 that the user has deposited from any of the L1 addresses that are set to track loopring.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/loopring/balances HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Loopring module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as loopring returned an unexpected result.


Getting eth2 staking performance
=======================================


.. http:put:: /api/(version)/blockchains/eth2/stake/performance

   Doing a PUT on the ETH2 stake performance endpoint will return the performance for all validators (or the filtered ones) in a paginated manner.

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``	      

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/eth2/stake/performance HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "validator_indices": [0, 15, 23542], "only_cache": false, "status": "all", "limit": 10, "offset": 10}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool only_cache: If false then we skip any cached values
   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int[optional] from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int[optional] to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson list[optional] validator_indices: The indices of the validators to filter for
   :reqjson list[optional] addresses: The associated addresses for which to filter the results. These will associate with a validator if the address is a depositor, a withdrawal address or a fee recipient.
   :reqjson string[optional] status: The status by which to filter. By default and if missing it's ``"all"`` validators. Can also fiter by ``"active"`` or ``"exited"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "sums": {
                  "apr": "0.0597652039949379861158979362586657031468575710584143257025001370766265371913491",
                  "execution": "0.951964836013963505",
                  "exits": "0.0014143880000005993",
                  "outstanding_consensus_pnl": "0.000829238",
                  "sum": "3.2351487110139639043",
                  "withdrawals": "2.2809402489999998"
              },
              "validators": {
                  "432840": {
                      "apr": "0.0466762036714707128052091929912369373004480648295118244406922158753010413605874",
                      "execution": "0.93361811418473",
                      "exits": "0.0014143880000005993",
                      "sum": "2.5266283731847305993",
                      "withdrawals": "1.591595871"
                  },
                  "624729": {
                      "apr": "0.0130890003234672733106887432674287658464095062289025012618079212013254958307617",
                      "execution": "0.018346721829233505",
                      "outstanding_consensus_pnl": "0.000829238",
                      "sum": "0.708520337829233305",
                      "withdrawals": "0.6893443779999998"
                  }
              },
              "entries_found": 2,
              "entries_total": 402
          },
          "message": ""
      }

   :resjson object sums: Sums of all the pages of the results
   :resjson object validator: Mapping of validator index to performance for the current page
   :resjson string apr: The APR of returns for the given timerange for the validator.
   :resjson string execution: The sum of execution layer ETH PnL for the validator.
   :resjson string withdrawals: The sum of consensus layer withdrawals ETH pnl for the validator
   :resjson string exits: The sum of the exit ETH PnL for the validator
   :resjson string outstanding_consensus_pnl: If a recent timerange is queried we also take into account not yet withdrawn ETH gathering in the consensus layer.
   :resjson int entries_found: The validators found for the current filter
   :resjson int entries_total: The total number of validators found

   :statuscode 200: Eth2 validator performance successfully returned.
   :statuscode 401: User is not logged in.
   :statuscode 409: eth2 module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: Error connecting to a remote to query data.

Getting Eth2 Staking daily stats
=====================================

.. http:post:: /api/(version)/blockchains/eth2/stake/dailystats

   Doing a POST on the ETH2 stake daily stats endpoint will return daily stats for your ETH2 validators filtered and paginated by the given parameters

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/blockchains/eth2/stake/dailystats HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "validator_indices": [0, 15, 23542], "addresses": ["0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12"],  "status": "all", "only_cache": false}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool only_cache: If true then only the daily stats in the DB are queried.
   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: Optional. This is the list of attributes of the eth2_daily_staking_details table by which to order the results. If none is given 'timestamp' is assumed. Valid values are: ['timestamp', 'validator_index', 'pnl'].
   :reqjson list[bool] ascending: Optional. False by default. Defines the order by which results are returned depending on the chosen order by attribute.
   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson list(string)[optional] validator_indices: Optionally filter entries validator indices. If missing data for all validators are returned.
   :reqjson list(string)[optional] addresses: The associated addresses for which to filter the results. These will associate with a validator if the address is a depositor, a withdrawal address or a fee recipient.
   :reqjson string[optional] status: The status by which to filter. By default and if missing it's ``"all"`` validators. Can also fiter by ``"active"`` or ``"exited"``.

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
              }, {
                  "validator_index": 43567,
                  "timestamp": 1613865600,
                  "pnl": {"amount": "-0.0066", "usd_value": "-6.6"},
              }],
              "entries_found": 95,
              "entries_total": 1000,
              "sum_pnl": "0.0014",
         },
        "message": "",
      }

   :resjson entries : The list of daily stats filtered by the given filter.

   :resjson eth_depositor string: The eth1 address that made the deposit for the validator.
   :resjson timestamp int: The timestamp of the start of the day in GMT for which this entry is.
   :resjson pnl object: The amount of ETH gained or lost in that day along with its usd value. Average price of the day is taken.
   :resjson string sum_pnl: The sum of PnL in ETH for the current filter and current page.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_total: The number of total entries ignoring all filters.

   :statuscode 200: Eth2 staking details successfully queried
   :statuscode 401: User is not logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 409: eth2 module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Adding an Eth2 validator
==========================

.. http:put:: /api/(version)/blockchains/eth2/validators

   Doing a PUT on the eth2 validators endpoint will input information and track an ETH2 validator.


   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/eth2/validators HTTP/1.1
      Host: localhost:5042

   :reqjson validator_index int: An optional integer representing the validator index of the validator to track. If this is not given then the public key of the validator has to be given!
   :reqjson public_key str: An optional string representing the hexadecimal string of the public key of the validator to track. If this is not given the validator index has to be given!
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
   :statuscode 401: User is not logged in.
   :statuscode 409: eth2 module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as beaconcha.in could not be reached or returned unexpected response.


Deleting Eth2 validators
===========================

.. http:delete:: /api/(version)/blockchains/eth2/validators

   Doing a DELETE on the eth2 validators endpoint will delete information and stop tracking a number of ETH2 validator/s.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/eth2/validators HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json

      {
        "validators": [1, 23423, 3233]
      }

   :reqjson list[int] validators: A list of indices of eth2 validators to delete

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

   :statuscode 200: Eth2 validator/s successfully delete.
   :statuscode 401: User is not logged in.
   :statuscode 409: eth2 module is not activated.
   :statuscode 500: Internal rotki error.


Editing an Eth2 validator
==========================

.. http:patch:: /api/(version)/blockchains/eth2/validators

   Doing a PATCH on the eth2 validators endpoint will allow to edit the ownership percentage of a validator identified by its index.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/eth2/validators HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: eth2 module is not activated or validator doesn't exist.
   :statuscode 500: Internal rotki error.


Getting tracked Eth2 validators
===============================

.. http:get:: /api/(version)/blockchains/eth2/validators

   Doing a GET on the ETH2 validators endpoint will get information on the tracked ETH2 validators. If the user is not premium they will see up to a certain limit of validators. If ignore cache is false, only DB data is return. If it's true then all validator data will be refreshed and new validators will be detected.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth2/validators HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"ignore_cache": true, "async_query": true}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :reqjson bool ignore_cache: Boolean denoting whether to ignore the DB cache and refresh all validator data.
   :reqjson list(string)[optional] validator_indices: Optionally filter entries validator indices. If missing data for all validators are returned.
   :reqjson list(string)[optional] addresses: The associated addresses for which to filter the results. These will associate with a validator if the address is a depositor, a withdrawal address or a fee recipient.
   :reqjson string[optional] status: The status by which to filter. By default and if missing it's ``"all"`` validators. Can also fiter by ``"active"`` or ``"exited"``.


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
	      "withdrawal_address": "0x23a3283f9f538a54d49139cd35c2fe0443cad3db",
	      "status": "pending",
            },
            {
              "index":1532,
              "public_key":"0xa509dec619e5b3484bf4bc1c33baa4c2cdd5ac791876f4add6117f7eded966198ab77862ec2913bb226bdf855cc6d6ed",
              "ownership_percentage": "50",
	      "activation_timestamp": 1701971000,
	      "status": "active"
            },
            {
              "index":5421,
              "public_key":"0xa64722f93f37c7da8da67ee36fd2a763103897efc274e3accb4cd172382f7a170f064b81552ae77cdbe440208a1b897e",
              "ownership_percentage": "25.75",
	      "withdrawal_address": "0xfa13283f9e538a84d49139cd35c2fe0443caa34f",
	      "activation_timestamp": 1701972000,
	      "withdrawable_timestamp": 1702572000,
	      "status": "exited"
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
   :resjson string status: The status of the validator. Can be one of ``"pending"``, ``"active"``, ``"exiting"`` and ``"exited"``.
   :resjson string[optional] ownership_percentage: The ownership percentage of the validator. If missing assume 100%.
   :resjson string[optional] withdrawal_address: The withdrawal address for the validator if set.
   :resjson integer[optional] activation_timestamp: If existing this is the timestamp the validator will (or has been) activate/d. If not then this is a pending validator not yet fully deposited or not yet processed by the consensus layer.
   :resjson integer[optional] withdrawable_timestamp: If existing this is the timestamp the validator will (or has been) able to be completely withdrawn. In other words from which point on a full exit will happen next time it's skimmed by withdrawals. If this key exists this mean we are dealing with a validator that is exiting or has exited.

   :statuscode 200: Eth2 validator defaults successfully returned.
   :statuscode 401: User is not logged in.
   :statuscode 409: eth2 module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: Error contacting to a remote to query data.


Getting Pickle's DILL balances
==============================

.. http:get:: /api/(version)/blockchains/eth/modules/pickle/dill

   Doing a GET on the pickle's DILL balances resource will return the balances that the user has locked with the rewards that can be claimed.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   .. note::
      This endpoint also accepts parameters as query arguments.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/modules/pickle/dill HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Pickle module is not activated.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Querying ethereum airdrops
==============================

.. http:get:: /api/(version)/blockchains/eth/airdrops

   Doing a GET on the ethereum airdrops endpoint will return how much and of which token any of the tracked ethereum addresses are entitled to.

   **Example Request**

   .. http:example:: curl wget httpie python-requests

    GET /api/1/blockchains/eth/airdrops HTTP/1.1
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
                     "link": "https://app.uniswap.org/",
                     "claimed": false
                  }
            },
            "0x0B89f648eEcCc574a9B7449B5242103789CCD9D7": {
                  "1inch": {
                     "amount": "1823.23",
                     "asset": "eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302",
                     "link": "https://1inch.exchange/",
                     "claimed": false,
                     "missing_decoder": true
                  },
                  "uniswap": {
                     "amount": "400",
                     "asset": "eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
                     "link": "https://app.uniswap.org/",
                     "claimed": true,
                     "icon_url": "https://raw.githubusercontent.com/rotki/data/main/airdrops/icons/uniswap.svg"
                  }
            },
            "message": ""
         }
      }


   :reqjson object result: A mapping of addresses to protocols for which claimable airdrops exist

   :statuscode 200: Tags successfully queried.
   :statuscode 401: User is not logged in.
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
   :statuscode 401: No user is logged in.
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
   :statuscode 401: No user is logged in.
   :statuscode 409: The address already exists in the addresses to query for that protocol.
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
   :statuscode 401: No user is logged in.
   :statuscode 409: The address is not in the addresses to query for that protocol.
   :statuscode 500: Internal rotki error


Adding EVM accounts to all EVM chains
=======================================

.. http:put:: /api/(version)/blockchains/evm/accounts

   Doing a PUT on the EVM accounts endpoint functions just like the add blockchain accounts endpoint but adds the addresses for all evm chains. It will follow the following logic. Take ethereum mainnet as the parent chain. If it's a contract there, it will only add it to the mainnet. If it's an EoA it will try all chains one by one and see if they have any transactions/activity and add it to the ones that do.

   .. note::
     This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/evm/accounts HTTP/1.1
      Host: localhost:5042

      {
          "accounts": [{
                  "address": "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
                  "label": "my new metamask",
                  "tags": ["public", "metamask"]
              }, {
                  "address": "0x9531C059098e3d194fF87FebB587aB07B30B1306"
              }, {
                  "address": "0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa"
              }, {
                  "address": "0xc37b40ABdB939635068d3c5f13E7faF686F03B65"
              }, {
                  "address": "0x7277F7849966426d345D8F6B9AFD1d3d89183083"
              }]
      }

      For request details check `here <blockchain_account_addition_section_>`__

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "added":{
               "0x9531C059098e3d194fF87FebB587aB07B30B1306": ["all"],
               "0x9008D19f58AAbD9eD0D60971565AA8510560ab41": ["eth"]
            },
            "failed":{
               "0xc37b40ABdB939635068d3c5f13E7faF686F03B65": [
                  "polygon_pos",
                  "arbitrum_one",
                  "base",
                  "gnosis"
               ]
            },
            "existed":{
               "0x7277F7849966426d345D8F6B9AFD1d3d89183083": ["gnosis"]
            },
            "no_activity":{
               "0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa": ["all"],
               "0x7277F7849966426d345D8F6B9AFD1d3d89183083": [
                  "eth",
                  "optimism",
                  "avax",
                  "polygon_pos",
                  "arbitrum_one",
                  "base"
               ]
            },
            "eth_contracts": ["0x9008D19f58AAbD9eD0D60971565AA8510560ab41"]
        },
        "message": ""
      }

   .. note::
     When a result includes all the chains instead of listing them all we use the special symbol ``all``

   :resjson object added: A mapping containing addresses and what chains they were added to.
   :resjson object existed: A mapping containing addresses and in what chains they were already tracked before the api call so no action was taken on them.
   :resjson object failed: A mapping containing which chains failed to get added for each address due to some error contacting remote APIs.
   :resjson object no_activity: A mapping containing addresses and in which chains they had no activity so no action was taken for them.
   :resjson list no_activity: A list of the addresses that were detected as ethereum contracts.
   :statuscode 200: Accounts successfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 401: User is not logged in.
   :statuscode 409: Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Remote error occurred when attempted to connect to an Avalanche or Polkadot node and only if it's the first account added. Check message for details.


.. http:post:: /api/(version)/blockchains/evm/accounts

   Doing a POST on the EVM accounts endpoint will re-detect evm accounts on all supported chains. Rotki will go through already added addresses and for each address, if it is an EOA (not a smart contract) and has activity on some chain, will add it to that chain.

   .. note::
     This endpoint can also be queried asynchronously by using ``"async_query": true``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/blockchains/evm/accounts HTTP/1.1
      Host: localhost:5042

      {}

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

   :resjson bool result: true in case of success, null otherwise.
   :statuscode 200: Accounts successfully added
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 401: User is not logged in.
   :statuscode 409: Node that was queried is not synchronized.
   :statuscode 500: Internal rotki error
   :statuscode 502: Remote error occurred.


Adding blockchain accounts
===========================

.. http:put:: /api/(version)/blockchains/(name)/accounts

   .. note::
      Supported blockchains: ``"BTC", "BCH", "ETH", "KSM", "DOT", "AVAX", "OPTIMISM"``

      Supported blockchains with ENS domains: ``"BTC", "BCH", "ETH", "KSM", "DOT"``

      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the blockchains endpoint with a specific blockchain URL and a list of account data in the json data will add these accounts to the tracked accounts for the given blockchain and the current user. A list of accounts' addresses that were added during a request is returned. This data is returned so that if you add an ens name, you get its name's resolved address for the further usage.
   If one of the given accounts to add is invalid the entire request will fail.

.. _blockchain_account_addition_section:

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/eth/accounts HTTP/1.1
      Host: localhost:5042

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
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the new account. Can be null. Should never be an empty list.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Remote error occurred when attempted to connect to an Avalanche or Polkadot node and only if it's the first account added. Check message for details.

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
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the xpub. Can be null. Should never be an empty list.
   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :statuscode 200: Xpub successfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 401: User is not logged in.
   :statuscode 409: Some error occurred when re-querying the balances after addition. Provided tags do not exist. Check message for details.
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
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the xpub. Can be null. Should never be an empty list.

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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some error occurred when re-querying the balances after addition. Provided tags do not exist. Check message for details.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some error occurred when re-querying the balances after addition. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as blockstream/haskoin. Check message for details.


Editing blockchain account data
=================================

.. http:patch:: /api/(version)/blockchains/(name)/accounts

   .. note::
      Supported blockchains: ``"BTC", "BCH", "ETH", "KSM", "DOT", "AVAX", "OPTIMISM"``

      Supported blockchains with ENS domains: ``"BTC", "BCH", "ETH", "KSM", "DOT"``

   Doing a PATCH on the blockchains endpoint with a specific blockchain URL and a list of accounts to edit will edit the label and tags for those accounts.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/blockchains/eth/accounts HTTP/1.1
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
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the account. Can be null. Should never be an empty list.

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
   :statuscode 401: User is not logged in.
   :statuscode 409: An account given to edit does not exist or a given tag does not exist.
   :statuscode 500: Internal rotki error

Removing blockchain accounts
==============================

.. http:delete:: /api/(version)/blockchains/(name)/accounts

   .. note::
      Supported blockchains: ``"BTC", "BCH", "ETH", "KSM", "DOT", "AVAX", "OPTIMISM"``

      Supported blockchains with ENS domains: ``"BTC", "BCH", "ETH", "KSM", "DOT"``

      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a DELETE on the blockchains endpoint with a specific blockchain URL and a list of accounts in the json data will remove these accounts from the tracked accounts for the given blockchain and the current user. The updated balances after the account deletions are returned.
    If one of the given accounts to add is invalid the entire request will fail.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/eth/accounts HTTP/1.1
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Some error occurred when re-querying the balances after addition. Check message for details.
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
                  "identifier": 1,
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "50.315",
                  "usd_value": "2370.13839",
                  "tags": ["public"],
                  "location": "blockchain"
              }, {
                  "identifier": 2,
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain"
              }, {
                  "identifier": 3,
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
   :statuscode 401: User is not logged in.
   :statuscode 500: Internal rotki error

Adding manually tracked balances
====================================

.. http:put:: /api/(version)/balances/manual/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the manually tracked balances endpoint you can add a balance for an asset that rotki can't automatically detect, along with a label identifying it for you and any number of tags.

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
                  "location": "blockchain",
                  "balance_type": "asset"
              }, {
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "location": "blockchain",
                  "balance_type": "liability"
              }]
      }

   :reqjson list[object] balances: A list of manually tracked balances to add to rotki
   :reqjsonarr string asset: The asset that is being tracked
   :reqjsonarr string label: A label to describe where is this balance stored. Must be unique between all manually tracked balance labels.
   :reqjsonarr string amount: The amount of asset that is stored.
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the this manually tracked balance. Can be null. Should never be an empty list.
   :reqjsonarr string location: The location where the balance is saved. Can be one of: ["external", "kraken", "poloniex", "bittrex", "binance", "bitmex", "coinbase", "banks", "blockchain", "coinbasepro", "gemini", "ftx", "ftxus", "independentreserve"]
   :reqjsonarr string[optional] balance_type: The type of the balance. Either "asset" or "liability". By default it's an asset.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
          "balances": [{
                  "identifier": 1,
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "50.315",
                  "usd_value": "2370.13839",
                  "tags": ["public"],
                  "location": "blockchain",
                   "balance_type": "asset"
              }, {
                  "identifier" :2,
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain",
                  "balance_type": "asset"
              }, {
                  "identifier": 3
                  "asset": "ZEC",
                  "label" "My favorite wallet",
                  "amount": "76.2"
                  "usd_value": "6067.77",
                  "tags": ["private", "inheritance"]
                  "location": "blockchain",
                  "balance_type": "asset"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances successfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The balances to add contained invalid assets or were an empty list. One of the balance labels already exist.
   :statuscode 401: User is not logged in.
   :statuscode 409: Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as Cryptocompare. Check message for details.

Editing manually tracked balances
====================================

.. http:patch:: /api/(version)/balances/manual

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PATCH on the manual balances endpoint allows you to edit a number of manually tracked balances by identifier.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/balances/manual/ HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "balances": [{
                  "identifier": 1,
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "4.5",
                  "location": "blockchain",
                  "balance_type": "asset"
                  },{
                  "identifier": 3,
                  "asset": "ETH"    ,
                  "label": "My favorite wallet",
                  "amount": "10",
                  "tags": [],
                  "location": "kraken",
                  "balance_type": "liability"
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
                  "identifier" 1,
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "4.5",
                  "usd_value": "210.548",
                  "tags": ["public"],
                  "location": "blockchain",
                  "balance_type": "asset"
              }, {
                  "identifier": 2,
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain",
                  "balance_type": "asset"
              }, {
                  "identifier": 3,
                  "asset": "ZEC",
                  "label" "My favorite wallet",
                  "amount": "10"
                  "usd_value": "1330.85"
                  "location": "kraken",
                  "balance_type": "asset"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances successfully edited
   :statuscode 400: Provided JSON or data is in some way malformed. The balances to add contained invalid assets or were an empty list.
   :statuscode 401: User is not logged in.
   :statuscode 409: Provided tags do not exist. Check message for details.
   :statuscode 500: Internal rotki error
   :statuscode 502: Error occurred with some external service query such as Cryptocompare. Check message for details.

Deleting manually tracked balances
======================================

.. http:delete:: /api/(version)/balances/manual/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a DELETE on the manual balances endpoint with a list of identifiers of manually tracked balances will remove these balances from the database for the current user.
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
                  "identifier": 2,
                  "asset": "BTC",
                  "label": "My XPUB BTC wallet",
                  "amount": "1.425",
                  "usd_value": "9087.22",
                  "location": "blockchain",
                  "balance_type": "asset"
              }]
          "message": ""
      }

   :resjson object result: An object containing all the manually tracked balances as defined `here <manually_tracked_balances_section_>`__ with additionally a current usd equivalent value per account.
   :statuscode 200: Balances successfully delete
   :statuscode 400: Provided JSON or data is in some way malformed. One of the labels to remove did not exist.
   :statuscode 401: User is not logged in.
   :statuscode 409: Check message for details.
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
   :reqjson string identifier: The identifier with which to identify this vault. It's unique per user and vault args + watcher combination. The client needs to keep this identifier. If the entry is edited, the identifier changes.
   :reqjson string type: The type of the watcher. Valid types are: "makervault_collateralization_ratio".
   :reqjson object args: An object containing the args for the vault. Depending on the vault type different args are possible. Check `here <watcher_types_section_>`__ to see the different options.
   :statuscode 200: Watchers successfully queried
   :statuscode 401: No user is currently logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not connect to or got unexpected response format from rotki server


   .. _watcher_types_section:

   For makervault ratio the possible arguments are:
    - vault_id: The id of the vault to watcher
    - ratio: The target ratio to watch for
    - op: The comparison operator:
        * lt: less than the given ratio
        * le: less than or equal to the given ratio
        * gt: greater than the given ratio
        * ge: greater than or equal to the given ratio

Adding new watcher
====================

.. http:put:: /api/(version)/watchers/

   .. note::
      This endpoint is only available for premium users

   Doing a PUT on the watchers endpoint you can install new watchers for watching to the server.


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
   :statuscode 401: No user is currently logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not connect to or got unexpected response format from rotki server

Editing watchers
==================

.. http:patch:: /api/(version)/watchers

   .. note::
      This endpoint is only available for premium users

   Doing a PATCH on the watchers endpoint allows you to edit a number of watchers by identifier. If one of the identifier is not found, the whole method fails.

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
   :statuscode 401: No user is currently logged in.
   :statuscode 403: Logged in user does not have premium.
   :statuscode 500: Internal rotki error
   :statuscode 502: Could not connect to or got unexpected response format from rotki server

Deleting watchers
==================

.. http:delete:: /api/(version)/watchers/

   .. note::
      This endpoint is only available for premium users

   Doing a DELETE on the watchers endpoint with a list of identifiers will delete either all or none of them.


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
   :statuscode 401: No user is currently logged in.
   :statuscode 403: Logged in user does not have premium.
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
   :statuscode 401: User is not logged in.
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
          "result": {"successful":[],"no_action":["eip155:1/erc20:0x255Aa6DF07540Cb5d3d297f0D0D4D84cb52bc8e6"]},
          "message": ""
      }

   :resjson list successful: A list of asset identifiers that were added to the list of ignored assets.
   :resjson list no_action: A list of assets that were already ignored and no action was taken on them.
   :statuscode 200: Assets successfully added
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 401: User is not logged in.
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
          "result": {"successful":[],"no_action":["ETH"]},
          "message": ""
      }

   :resjson list successful: A list of asset identifiers that were removed from the list of ignored assets.
   :resjson list no_action: A list of assets that weren't ignored and no action was taken on them.
   :statuscode 200: Assets successfully removed
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 401: User is not logged in.
   :statuscode 500: Internal rotki error


False positive in spam assets
==============================

.. http:post:: /api/(version)/assets/ignored/whitelist

   Doing a POST on this endpoint will mark the provided token as a false positive spam asset. This will remove it from the list of ignored assets, remove the spam value from the protocol field and add it to the list of false positives.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      PATH /api/1/assets/ignored/whitelist HTTP/1.1
      Host: localhost:5042

      {"token": "eip155:1/erc20:0x6B3595068778DD592e39A122f4f5a5cF09C90fE2"}


  :reqjsonarr string token: The identifier of the evm token that will be marked as false positive

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Asset added to spam whitelist successfully.
  :statuscode 401: No user is currently logged in.
  :statuscode 500: Internal rotki error.

.. http:get:: /api/(version)/assets/ignored/whitelist

   Doing a GET on this endpoint will return a list of the assets that are whitelisted.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/ignored/whitelist HTTP/1.1
      Host: localhost:5042


  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F"],
          "message": ""
      }

  :resjson bool result: list of the assets whitelisted.
  :statuscode 200: Assets listed succesfully.
  :statuscode 409: No user is currently logged in.
  :statuscode 500: Internal rotki error.

.. http:delete:: /api/(version)/assets/ignored/whitelist

   Doing a DELETE on this endpoint will remove the provided token from the list of false positives.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/ignored/whitelist HTTP/1.1
      Host: localhost:5042

      {"token": "eip155:1/erc20:0x6B3595068778DD592e39A122f4f5a5cF09C90fE2"}


  :reqjsonarr string token: The identifier of the evm token that will be removed from the false positive whitelist

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Asset removed from spam whitelist successfully.
  :statuscode 409: No user is currently logged in.
  :statuscode 500: Internal rotki error.


Toggle spam status in evm tokens
==================================

.. http:post:: /api/(version)/assets/evm/spam/

   Doing a POST on this endpoint will mark the provided token as a spam token. It will move the token to the list of ignored assets and remove it from the list of whitelisted tokens. Any protocol value that the token might have will be overwritten.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      PATH /api/1/assets/evm/spam HTTP/1.1
      Host: localhost:5042

      {"token": "eip155:1/erc20:0x6B3595068778DD592e39A122f4f5a5cF09C90fE2"}


  :reqjsonarr string token: The identifier of the evm token that will be marked as spam

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Asset marked as spam successfully.
  :statuscode 401: No user is currently logged in.
  :statuscode 500: Internal rotki error.

.. http:delete:: /api/(version)/assets/evm/spam/

   Doing a DELETE on this endpoint will remove the spam protocol from the token setting it to null. It will also remove the token from the list of ignored assets.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/evm/spam HTTP/1.1
      Host: localhost:5042

      {"token": "eip155:1/erc20:0x6B3595068778DD592e39A122f4f5a5cF09C90fE2"}


  :reqjsonarr string token: The identifier of the evm token that will be updated removing the protocol value of spam.

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Asset updated correctly.
  :statuscode 401: No user is currently logged in.
  :statuscode 500: Internal rotki error.


Dealing with ignored actions
==============================

.. http:put:: /api/(version)/actions/ignored

   Doing a PUT on the ignored actions endpoint will add action identifiers for ignoring of a given action type during accounting. Returns the list of all ignored action identifiers of the given type after the addition.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/actions/ignored HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"action_type": "history event", "data": ["Z231-XH23K"]}

   :reqjson str action_type: A type of actions whose ignored ids to add. Defined above. Depending on the type, the data field is different.
   :reqjson list data: The data to ignore. For type "evm_transaction" it's an object with the following keys: ``"evm_chain"`` with the name of the evm chain the transaction happened in and ``"tx_hash"`` the string of the transaction hash to ignore. For all other types it's a list of strings representing the identifier of the action to ignore.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: Action ids successfully added
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 401: User is not logged in.
   :statuscode 409: One of the action ids provided is already on the list.
   :statuscode 500: Internal rotki error

.. http:delete:: /api/(version)/actions/ignored/

   Doing a DELETE on the ignored actions endpoint removes action ids from the list of actions of the given type to be ignored during accounting.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/actions/ignored HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
          "action_type": "evm transaction",
          "data": [{
              "evm_chain": "ethereum",
              "tx_hash": "0x34d9887286d8c427e5bf18004c464d150190780e83e89a47906cc63a07267780"
          }, {
              "evm_chain": "optimism",
              "tx_hash": "0x14d9887286d3c427e5bf18004c464d150190780e83e89a47906cc63a07267780"
          }]
      }

   :reqjson str action_type: As defined in ``PUT`` above.
   :reqjson list data: As defined in ``PUT`` above.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: Action ids successfully removed
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 401: User is not logged in.
   :statuscode 409: One of the action ids provided is not on the list.
   :statuscode 500: Internal rotki error


Querying general information
==============================

.. http:get:: /api/(version)/info

   Doing a GET on the info endpoint will return general information about rotki. Under the version key we get info on the current version of rotki. When ``check_for_updates`` is ``true`` if there is a newer version then ``"download_url"`` will be populated. If not then only ``"our_version"`` and ``"latest_version"`` will be. There is a possibility that latest version may not be populated due to github not being reachable. Also we return the data directory and other information.

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
                "data_directory": "/home/username/.local/share/rotki/data",
                "log_level": "DEBUG",
                "accept_docker_risk": false,
                "backend_default_arguments": {
                        "max_logfiles_num": 3,
                        "max_size_in_mb_all_logs": 300,
                        "sqlite_instructions": 5000
                }
        },
        "message": ""
      }

   :resjson str our_version: The version of rotki present in the system
   :resjson str latest_version: The latest version of rotki available
   :resjson str download_url: URL link to download the latest version
   :resjson str data_directory: The rotki data directory
   :resjson str log_level: The log level used in the backend. Can be ``DEBUG``, ``INFO``, ``WARN``, ``ERROR`` or ``CRITICAL``.
   :resjson bool accept_docker_risk: A boolean indicating if the user has passed an environment variable to the backend process acknowledging the security issues with the docker setup: https://github.com/rotki/rotki/issues/5176
   :resjson object backend_default_arguments: A mapping of backend arguments to their default values so that the frontend can know about them.

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

   .. note::
      If you want to provide a stream of data instead of a path, you can call POST on this endpoint and provide the stream in `filepath` variable.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/import HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"source": "cointracking", "filepath": "/path/to/data/file", "timestamp_format": "%d/%m/%Y %H:%M:%S"}

   :reqjson str source: The source of the data to import. Valid values are ``"cointracking"``, ``"cryptocom"``, ``"blockfi_transactions"``, ``"blockfi_trades"``, ``"nexo"``,  ``"shapeshift_trades"``, ``"uphold_transactions"``, ``"bitmex_wallet_history"``, ``"bisq_trades"``, ``"binance"``, ``"rotki_events"``, ``"rotki_trades"``, ``"bitcoin_tax"``, ``"bitstamp"``, ``"bittrex"``, ``"kucoin"``.
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
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal rotki error

ERC20 token info
====================

.. http:get:: /api/(version)/blockchains/evm/erc20details

   Doing a GET to this endpoint will return basic information about a token by calling the ``decimals/name/symbol`` methods.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/blockchains/eth/erc20details HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"address": "0x6B175474E89094C44Da98b954EedeAC495271d0F", "evm_chain": "optimism"}

   :reqjson str address: The checksumed address of a contract
   :reqjson str evm_chain: The name of the evm chain to check for token info e.g. ``"ethereum"``, ``"optimism"`` etc.
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
==============

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
                "price_in_asset": "0.025",
                "price_asset": "ETH",
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
   :resjson string price_in_asset: The last known price of the NFT in `price_asset`. Can be zero.
   :resjson string price_asset: The identifier of the asset used for `price_in_asset`.
   :resjson string price_usd: The last known price of the NFT in USD. Can be zero.
   :statuscode 200: NFTs successfully queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: User is not logged in.
   :statuscode 409: nft module is not activated.
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

      {"async_query": false, "ignore_cache": false, "offset": 3, "limit": 1}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not
   :param bool ignore_cache: Boolean denoting whether to ignore the cache for this query or not.
   :reqjson list[string][optional] owner_addresses: A list of evm addresses. If provided, only nfts owned by these addresses will be returned.
   :reqjson string[optional] name: Optional nfts name to filter by.
   :reqjson string[optional] collection_name: Optional nfts collection_name to filter by.
   :reqjson string[optional] ignored_assets_handling: A flag to specify how to handle ignored assets. Possible values are `'none'`, `'exclude'` and `'show_only'`. You can write 'none' in order to not handle them in any special way (meaning to show them too). This is the default. You can write 'exclude' if you want to exclude them from the result. And you can write 'show_only' if you want to only see the ignored assets in the result.
   :reqjson int limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string][optional] order_by_attributes: This is the list of attributes of the nft by which to order the results. By default we sort using ``name``.
   :reqjson list[bool][optional] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.
   :reqjson string[optional] lps_handling: A flag to specify how to handle LP NFTs. Possible values are `'all_nfts'` (default), `'only_lps'` and `'exclude_lps'`. You can use 'only_lps' if you want to only include LPs NFTs in the result or you can use 'exclude_lps' if you want NFTs not marked as LP positions.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

        {
            "result": {
                "entries": [
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
                  },
                ],
                "entries_found": 2,
                "entries_total": 10,
                "total_usd_value": "2651.70"
            },
            "message": ""
        }


   :resjson object entries: A list of nfts balances. ``name`` can also be null. ``collection_name`` can be null if nft does not have a collection.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_total: The number of total entries ignoring all filters.
   :resjson int total_usd_value: Total usd value of the nfts in the filter.
   :statuscode 200: NFT balances successfully queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: User is not logged in.
   :statuscode 409: nft module is not activated.
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
   :statuscode 401: No user is currently logged in.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: Failure to create the DB backup.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: Failure to delete the backup or the requested file to delete is not in the user's data directory.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: Failure to download the backup or the requested file to download is not in the user's data directory.
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
   :statuscode 401: User is not logged in.
   :statuscode 409: Other error. Check error message for details.
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
              "entries": [
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
   :statuscode 401: No user is logged in.
   :statuscode 409: Kraken is not active or some parameter for filters is not valid.
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
   :statuscode 401: No user is logged in.
   :statuscode 507: Failed to create the file.


Import assets added by the user
===============================

.. http:put:: /api/(version)/assets/user
.. http:post:: /api/(version)/assets/user

   Doing a put or a post to this endpoint will import the assets in the json file provided. The file has to follow the rotki expected format and will be verified.

   .. note::
      If doing a POST the `action` field is not required.

   .. note::
      This endpoint can be called asynchronously.

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
   :statuscode 401: No user is logged in.
   :statuscode 409: Imported file is for an older version of the schema or file can't be loaded or format is not valid.
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
   :statuscode 401: No user is currently logged in.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: No snapshot data found for the given timestamp. No permissions to write in the given directory. Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: No snapshot data found for the given timestamp. No permissions to write in the given directory. Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: No snapshot found for the specified timestamp.Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: JSON has different timestamps. Snapshot contains an unknown asset. JSON has invalid headers. Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: CSV file has different timestamps. Snapshot contains an unknown asset. Csv file has invalid headers. Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: Failed to query names or addresses have incorrect format.
   :statuscode 500: Internal rotki error.


Get mappings from addressbook
==============================

.. http:post:: /api/(version)/names/addressbook

    Doing a POST on the addressbook endpoint with either /global or /private postfix with a list of addresses will return found address mappings with the specified filter arguments. If no filter argument is specified, all known mappings are returned.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

        POST /api/1/names/addressbook/global HTTP/1.1
        Host: localhost:5042
        Content-Type: application/json;charset=UTF-8

        {
          "offset": 0,
          "limit": 1,
          "blockchain": "eth",
          "name_substring": "neighbour",
          "addresses": [
            {"address": "0x9531c059098e3d194ff87febb587ab07b30b1306", "blockchain": "eth"},
            {"address": "bc1qamhqfr5z2ypehv0sqq784hzgd6ws2rjf6v46w8", "blockchain": "btc"},
            {"address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD"}
           ]
        }

    :reqjson int[optional] limit: This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
    :reqjson int[optional] offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
    :reqjson list[string] order_by_attributes: This is the list of attributes of the addressbook entries by which to order the results.
    :reqjson list[bool] ascending: Should the order be ascending? This is the default. If set to false, it will be on descending order.
    :reqjson str[optional] name_substring: The substring to use as filter for the name to be found in the addressbook.
    :reqjson str[optional] blockchain: The blockchain in which to use the provided name.
    :reqjson object[optional] addresses: List of addresses that the backend should find names for.

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": {
              "entries": [
                { "address": "bc1qamhqfr5z2ypehv0sqq784hzgd6ws2rjf6v46w8", "name": "mtgox", "blockchain": "btc" },
                { "address": "0x9531c059098e3d194ff87febb587ab07b30b1306", "name": "My dear friend Tom", "blockchain": "eth" },
                { "address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD", "name": "Neighbour Frank", "blockchain": "eth" }
               ],
              "entries_found": 1,
              "entries_total": 3
            },
            "message": ""
        }

    :resjson object entries: An array of address objects. Each entry is composed of the address under the ``"address"`` key and other metadata like ``"name"`` and ``"blockchain"`` for each address.
    :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
    :resjson int entries_total: The number of total entries ignoring all filters.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Mappings were returned successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 401: No user is currently logged in.
    :statuscode 409: Addresses have incorrect format.
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
            {"address": "0x9531c059098e3d194ff87febb587ab07b30b1306", "blockchain": "eth", "name": "Dude ABC"},
            {"address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD", "name": "Dude XYZ"}
          ]
        }

    :reqjson object entries: A list of entries to be added to the addressbook

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": true,
            "message": ""
        }

    :resjson bool result: A boolean which is true in the case that entries were added successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Entries were added successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 401: No user is currently logged in.
    :statuscode 409: Some of the provided entries already exist in the addressbook or addresses have incorrect format.
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
            {"address": "13EcxFSXEFmJfxGXSQYLfgEXXGZBSF1P753MyHauw5NV4tAV", "name": "Polkacomma"},
            {"address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD", "name": "Dude XYZ"}
          ]
        }

    :reqjson object entries: A list of entries to be updated in the addressbook.
    :reqjson str address: The address that will be tracked in the addressbook.
    :reqjson str[optional] blockchain: The blockchain in which to use the provided name.
    :reqjson str name: Name to be used.

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": true,
            "message": ""
        }

    :resjson bool result: A boolean which is true in case if entries were updated successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Entries were updated successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 401: No user is currently logged in.
    :statuscode 409: Some of the provided entries don't exist in the addressbook or addresses have incorrect format.
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
          "addresses": [
            {"address": "0x9531c059098e3d194ff87febb587ab07b30b1306", "blockchain": "eth"},
            {"address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD"}
          ]
        }

    :reqjson object entries: A list of addresses to be deleted from the addressbook
    :reqjson str address: The address that will be deleted in the addressbook.
    :reqjson str[optional] blockchain: The blockchain for which to delete the name mapping. If is not provided the names for all the chains will be deleted.

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/zip

        {
            "result": true,
            "message": ""
        }

    :resjson bool result: A boolean which is true in case if entries were deleted successfully.
    :resjson str message: Error message if any errors occurred.
    :statuscode 200: Entries were deleted successfully.
    :statuscode 400: Provided JSON is in some way malformed.
    :statuscode 409: No user is currently logged in.
    :statuscode 409: Some of the provided entries don't exist in the addressbook or addresses have incorrect format.
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
          "addresses": [
            {"address": "0x9531c059098e3d194ff87febb587ab07b30b1306", "blockchain": "eth"},
            {"address": "0x8A4973ABBCEd48596D6D79ac6B53Ceda65e342CD"}
          ]
        }

    :reqjson object addresses: List of addresses that the backend should find names for
    :reqjson str address: The address that will be queried in the addressbook.
    :reqjson str[optional] blockchain: The chain for which to find names. If is not provided the names are searched for all chains.

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
    :statuscode 401: No user is currently logged in.
    :statuscode 409: Addresses have incorrect format.
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
   :statuscode 401: No user is currently logged in.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: No user note found. Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: User note does not exist.
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
            "location": "history events"
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: User note with the given title already exists. User has reached the limit of available notes. Check error message.
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
   :statuscode 401: No user is currently logged in.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: No custom asset found. Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: Custom asset name and type is already being used. Custom asset does not exist.  Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: Custom asset with the given name and type already exists. Check error message.
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
   :statuscode 401: No user is currently logged in.
   :statuscode 409: Other error. Check error message.
   :statuscode 500: Internal rotki error.


Events Details
================

.. http:get:: /api/(version)/history/events/details

   Doing a GET on this endpoint will return the details of a history event.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/history/events/details HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"identifier": 137}

   :reqjson int identifier: The identifier of the event to be queried.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "sub_swaps": [
                  {"from_amount": "100.0", "to_amount": "0.084", "from_asset": "eip155:1/erc20:0x6B3595068778DD592e39A122f4f5a5cF09C90fE2", "to_asset": "ETH"},
                  {"from_amount": "0.084", "to_amount": "98.2", "from_asset": "ETH", "to_asset": "eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7"}
              ]
          },
          "message": ""
      }

   :resjson object result: A dictionary with the details. It may contain one of the following amount of details.
   :resjson list sub_swaps: A list with the details of each sub-swap. Each entry contains the following keys: from_amount, to_amount, from_asset, to_asset.
   :resjson dict liquity_staking: Information about assets that were staked in liquity in this event.

   :statuscode 200: The details were returned successfully.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 404: There is no event with the provided identifier or the event has no details to be returned.
   :statuscode 401: No user is currently logged in.
   :statuscode 500: Internal rotki error.

Add EVM Transaction By Hash
================================

.. http:put:: /api/(version)/blockchains/evm/transactions/add-hash

   Doing a PUT on this endpoint will add an EVM transaction to the database and associate it with the provided address.
   .. note::
   This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/evm/transactions/add-hash HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
        "evm_chain": "ethereum",
        "tx_hash": "0x65d53653c584cde22e559cec4667a7278f75966360590b725d87055fb17552ba",
        "associated_address": "0xb8553D9ee35dd23BB96fbd679E651B929821969B",
        "async_query": true
      }

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not.
   :reqjson str evm_chain: The name of the evm chain for the transaction to the added e.g. ``"ethereum"``, ``"optimism"`` etc.
   :reqjson str tx_hash: The hash of the transaction to be added.
   :reqjson str associated_address: The address to be associated with the transaction. The address must be one that is already tracked by rotki.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true
          "message": ""
      }

   :resjson bool result: It contains a boolean representing the status of the request.

   :statuscode 200: The transaction was saved successfully.
   :statuscode 400: Provided JSON is in some way malformed. Transaction is already present in DB. Address provided is not tracked by rotki.
   :statuscode 404: Transaction hash not found for the specified chain.
   :statuscode 401: No user is currently logged in.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.


Get Binance Savings Interests History
=======================================

.. http:post:: /api/(version)/exchange/(location)/savings

   Doing a POST on this endpoint will return all history events relating to interest payments for the specified location.
   .. note::

      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      POST /api/1/exchange/binance/savings HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "only_cache": false}

   :reqjson bool async_query: Boolean denoting whether this is an asynchronous query or not.
   :reqjson int limit: Optional. This signifies the limit of records to return as per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson int offset: This signifies the offset from which to start the return of records per the `sql spec <https://www.sqlite.org/lang_select.html#limitoffset>`__.
   :reqjson list[string] order_by_attributes: Optional. This is the list of attributes of the history by which to order the results. If none is given 'timestamp' is assumed. Valid values are: ['timestamp', 'location', 'amount'].
   :reqjson list[bool] ascending: Optional. False by default. Defines the order by which results are returned depending on the chosen order by attribute.
   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson bool only_cache: Optional.If this is true then the equivalent exchange/location is not queried, but only what is already in the DB is returned.
   :reqjson string location: This represents the exchange's name. Can only be one of `"binance"` or `"binanceus"`.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
          "entries": [
            {
              "timestamp": 1587233562,
              "location": "binance",
              "asset": "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F",
              "amount": "0.00987654",
              "usd_value": "0.05432097"
            },
            {
              "timestamp": 1577233578,
              "location": "binance",
              "asset": "eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53",
              "amount": "0.00006408",
              "usd_value": "0.00070488"
            }
          ],
          "entries_found": 2,
          "entries_limit": 100,
          "entries_total": 2,
          "total_usd_value": "0.05502585",
          "assets": [
            "eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53",
            "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F"
          ],
          "received": [
            {
              "asset": "eip155:1/erc20:0x4Fabb145d64652a948d72533023f6E7A623C7C53",
              "amount": "0.00006408",
              "usd_value": "0.00070488"
            },
            {
              "asset": "eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F",
              "amount": "0.00987654",
              "usd_value": "0.05432097"
            }
          ]
        },
        "message": ""
      }

   :resjsonarr int timestamp: The timestamp at which the event occurred.
   :resjsonarr string location: A valid location at which the event happened.
   :resjsonarr string amount: The amount related to the event.
   :resjsonarr string asset: Asset involved in the event.
   :resjsonarr string message: It won't be empty if the query to external services fails for some reason.
   :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
   :resjson int entries_limit: The limit of entries if free version. -1 for premium.
   :resjson int entries_total: The number of total entries ignoring all filters.
   :resjson string total_usd_value: Sum of the USD value for the assets received computed at the time of acquisition of each event.
   :resjson list[string] assets: Assets involved in events ignoring all filters.
   :resjson list[object] received: Assets received with the total amount received for each asset and the aggregated USD value at time of acquisition.

   :statuscode 200: The balances were returned successfully.
   :statuscode 400: Invalid location provided.
   :statuscode 401: No user is currently logged in.
   :statuscode 500: Internal rotki error.
   :statuscode 502: An external service used in the query such as binance could not be reached or returned unexpected response.

Get all EVM Chains
===================

.. http:get:: /api/(version)/blockchains/evm/all

    Doing a GET request on this endpoint will return a list of all EVM chain IDs and their names and labels.

    **Example Request**

    .. http:example:: curl wget httpie python-requests

    GET /api/(version)/blockchains/evm/all HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

    {}

    **Example Response**

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
            "result": [
                {"id": 1, "name": "ethereum", "label": "Ethereum"},
                {"id": 10, "name": "optimism", "label": "Optimism"},
                {"id": 56, "name": "binance", "label": "Binance Smart Chain"},
                {"id": 100, "name": "gnosis", "label": "Gnosis"},
                {"id": 137, "name": "polygon_pos", "label": "Polygon POS"},
                {"id": 250, "name": "fantom", "label": "Fantom"},
                {"id": 42161, "name": "arbitrum_one", "label": "Arbitrum One"},
                {"id": 8453, "name": "base", "label": "Base"},
                {"id": 43114, "name": "avalanche", "label": "Avalanche"},
                {"id": 42220, "name": "celo", "label": "Celo"}
            ],
            "message": ""
        }

    :resjsonarr result: Returns a list of all EVM chains IDs, their names and labels. ``name`` is what is used to describe the chain when dealing from/to the API. ``label`` is the label to use in the frontend to display the chain.
    :statuscode 200: Success
    :statuscode 500: Internal rotki error

Get avatar for an ens name
============================

.. http:get:: /api/(version)/avatars/ens/<ens_name>

   Doing a GET on this endpoint will return the avatar that is currently set for the provided ens name. If successful, responses include an `ETag` header for caching.

   **Example Request**

    .. http:example:: curl wget httpie python-requests

      GET /api/1/avatars/ens/rotki.eth HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {}

   :reqjson string ens_name: The ens name to check avatar for. It should have `.eth` postfix.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: image/png

   :statuscode 200: The avatar was successfully found and returned.
   :statuscode 304: Avatar image has not changed. Should be cached on the client. This is returned if the given `If-Match` or `If-None-Match` header match the `ETag` of the previous response.
   :statuscode 400: Invalid ens name provided (it doesn't end with `.eth`).
   :statuscode 404: There is no avatar set for the given ens name.
   :statuscode 409: Avatar was requested for an ens name that is not currently in the database or we couldn't query the blockchain.


Clear Icons/Avatars Cache
=================================

.. http:post:: /api/(version)/cache/<cache_type>/clear

   Doing a POST on this endpoint will clear the cache of avatars/icons depending on the ``cache_type``. Valid options of ``cache_type`` are ``icons`` & ``avatars``.

   **Example Request**

    .. http:example:: curl wget httpie python-requests

      POST /api/1/cache/icons/clear HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
         "entries": ["ETH", "BTC"]
      }

    .. http:example:: curl wget httpie python-requests

      POST /api/1/cache/avatars/clear HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
         "entries": ["rotki.eth", "nebolax.eth"]
      }

   :reqjsonarr optional[string] entries: An array of the icons/avatars to be cleared from the cache. All icons/avatars are deleted in the cache if ``null``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

   :statuscode 200: The cache items were cleared successfully.
   :statuscode 400: Entries provided do not match the ``cache_type`` specified. Invalid ``cache_type`` provided.
   :statuscode 500: Internal rotki error


Event Mappings
================

.. http:get:: /api/(version)/history/events/type_mappings

  Doing a GET on this endpoint will return a mapping of history events types and subtypes to a ``EventCategory`` representation. We also return properties such ``icon``, ``label`` and ``color`` for event types.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

    GET /history/events/type_mappings HTTP/1.1
    Host: localhost:5042


  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
          "global_mappings":{
            "spend":{
              "fee":"gas",
              "return wrapped":"send",
              "donate":"donate",
              "none":"send"
            }
          },
          "entry_type_mappings":{
            "eth withdrawal event":{
              "staking":{
                "remove asset":{
                    "is_exit":"stake exit",
                    "not_exit":"withdraw"
                }
              }
            }
          },
          "per_protocol_mappings":{
            "ethereum":{
              "aave":{
                "spend":{
                  "payback debt":"repay",
                  "liquidate":"liquidate"
                }
              }
            },
            "optimism":{
              "aave":{
                "spend":{
                  "payback debt":"repay",
                  "liquidate":"liquidate"
                }
              }
            },
            "polygon pos":{
              "aave":{
                "spend":{
                  "payback debt":"repay",
                  "liquidate":"liquidate"
                }
              }
            },
          },
          "event_category_details":{
            "send":{
	      "direction": "out",
	      "counterparty_mappings": {
                "default": {
		  "label":"send",
                  "icon":"mdi-arrow-up",
            }}},
            "receive":{
	      "direction": "in",
	      "counterparty_mappings": {
                "default": {
		  "label":"receive",
                  "icon":"mdi-arrow-down",
                  "color":"green"
            }}},
            "fee":{
	      "direction": "out",
	      "counterparty_mappings": {
                "default": {
		  "label":"fee",
                  "icon":"mdi-account-cash",
            }, "gas": {
		  "label":"gas fee",
                  "icon":"mdi-fire",
	    }}},
            "gas":{
              "label":"gas_fee",
              "icon":"mdi-fire",
            },
            "receive":{
              "label":"receive",
              "icon":"mdi-arrow-down",
              "color":"green"
            }
          }
        }
      }

  :resjson object global_mappings: keys of this object are the history event types names and values are mappings of subtypes' names to the ``EventCategory`` name. Contains mappings that should be applied if there is no a specific protocol rule.
  :resjson object type_mappings: the keys of this mapping are entry types and it contains the combinations of event type and subtype that would overwritte the information in ``global_mappings`` only for that entry type.
  :resjson object per_protocol_mappings: same as global_mappings but contains specific mappings per chain and protocol.
  :resjson object event_category_details: This is a mapping of ``EventCategory`` to its direction and mapping of counterparty to details. For all the ``EventCategoryDetails`` mapping there is a ``"default"`` key mapping to the default details. For some exceptions there is also other keys which are counterparties. Such as for spend/fee and counterparty gas.
  :resjon object accounting_events_icons: Mapping of accounting event type to its corresponding icon name.
  :resjson string label: Label to show in the frontend for the event type.
  :resjson string icon: Icon to be used by the frontend for this event type.
  :resjson string color[optional]: Optional color to apply to the icon

  :statuscode 200: Information was correctly generated
  :statuscode 500: Internal rotki error

Getting all available counterparties
=====================================

.. http:get:: /api/(version)/history/events/counterparties

   Doing a GET on this endpoint will return information for all the counterparties used for decoding events in the backend.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

    GET /history/events/counterparties HTTP/1.1
    Host: localhost:5042


  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":[
            {
              "identifier":"1inch-v1",
              "label":"1inch",
              "image":"/assets/images/defi/1inch.svg"
            },
            {
              "identifier":"1inch-v2",
              "label":"1inch",
              "image":"/assets/images/defi/1inch.svg"
            }
        ]
      }

  :resjson string identifier: value used by the backend to represent the counterparty.
  :resjson string label: Name displayed in the frontend.
  :resjson string image: Relative path to the counterparty image.

  :statuscode 200: Information was correctly generated
  :statuscode 500: Internal rotki error

Getting EVM products
=====================================

.. http:get:: /api/(version)/history/events/products

   Doing a GET on this endpoint will return information for all the counterparties and the products that they use. Also it will return a list of all the available product values.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

    GET /history/events/products HTTP/1.1
    Host: localhost:5042


  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
          "mappings":{
            "convex":[
              "gauge",
              "staking"
            ],
            "curve":[
              "gauge"
            ]
          },
          "products":[
            "pool",
            "staking",
            "gauge"
          ]
        },
        "message":""
      }

  :resjson object mappings: A mapping of each counterparty to a list with the products that they use
  :resjson object products: A list of all the available products

  :statuscode 200: Information was correctly generated
  :statuscode 500: Internal rotki error

Get all valid locations
========================

.. http:get:: /api/(version)/locations/all

   Doing a GET on this endpoint will return all the possible location values.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

    GET /locations/all HTTP/1.1
    Host: localhost:5042


  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
          "locations": {
            "ethereum": {"image": "ethereum.svg"},
            "optimism": {"image": "optimism.svg"},
            "ftx": {"image": "ftx.svg", "is_exchange": true},
            "kraken": {
              "image": "kraken.svg",
              "exchange_detail": {
                "is_exchange_with_key": true
              }
            },
            "kucoin": {
              "image": "kucoin.svg",
              "exchange_detail": {
                "is_exchange_with_key": true,
                "is_exchange_with_passphrase": true
              }
            },
            "bitpanda": {
              "image": "bitpanda.svg",
              "exchange_detail": {
                "is_exchange_with_key": true,
                "is_exchange_without_api_secret": true
              }
            },
            "external": {"icon": "mdi-book"}
        }
      }

  :resjson list[string] locations: A mapping of locations to their details. Can contain `image` or `icon` depending on whether a known image should be used or an icon from the icon set. Additionally, it can contain a `display_name` if a special name needs to be used. If the location is an exchange, it may also include an `is_exchange` key, or an `exchange_details` object if the location has more details for the exchange data. The `exchange_details` object can contain `is_exchange_with_key` for exchanges requiring an API key, `is_exchange_with_passphrase` for exchanges needing an API key and passphrase, and `is_exchange_without_api_secret` for exchanges that do not require an API secret key, all within the exchange_detail object.

  :statuscode 200: Information was correctly returned
  :statuscode 500: Internal rotki error

Refresh general cache
========================

.. http:post:: /api/(version)/cache/general/refresh

   Doing a POST on this endpoint will refresh the entire cache (curve, makerdao, yearn, velodrome).

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

    POST /cache/general/refresh HTTP/1.1
    Host: localhost:5042


  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Is true if all the caches were refreshed successfully.

  :statuscode 200: Caches were correctly updated
  :statuscode 409: An issue during refreshing caches occurred
  :statuscode 500: Internal rotki error

Getting Metadata For Airdrops
===================================

.. http:get:: /api/(version)/airdrops/metadata

   Doing a GET on this endpoint will return metadata for all the airdrops that are supported by rotki.

   **Example Request**

   .. http:example:: curl wget httpie python-requests

    GET /airdrops/metadata HTTP/1.1
    Host: localhost:5042

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
         "result":[
            {
               "identifier": "uniswap",
               "name": "Uniswap",
               "icon": "uniswap.svg",
               "icon_url": "https://raw.githubusercontent.com/rotki/data/main/airdrops/icons/uniswap.svg"
            },
            {
               "identifier": "1inch",
               "name": "1inch",
               "icon": "1inch.svg"
            }
         ],
         "message": "",
      }

   :resjson string identifier: The identifier of the airdrop.
   :resjson string name: The name of the airdrop.
   :resjson string icon: The icon of the airdrop.

   :statuscode 200: Information was correctly returned
   :statuscode 500: Internal rotki error
   :statuscode 502: Failed to fetch airdrop metadata from rotki's data repository.

Getting Metadata For Defi Protocols
==========================================

.. http:get:: /api/(version)/defi/metadata

   Doing a GET on this endpoint will return metadata for all the defi protocols that are supported by rotki.

   **Example Request**

   .. http:example:: curl wget httpie python-requests

    GET /defi/metadata HTTP/1.1
    Host: localhost:5042

   **Example Response**

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
         "result":[
            {
               "identifier": "uniswapv1",
               "name": "Uniswap V1",
               "icon": "uniswap.svg"
            },
            {
               "identifier": "oneinch_liquidity",
               "name": "1inch Liquidity Protocol",
               "icon": "1inch.svg"
            }
         ],
         "message": ""
      }

   :resjson string identifier: The identifier of the defi protocol.
   :resjson string name: The name of the defi protocol.
   :resjson string icon: The icon of the defi protocol.

   :statuscode 200: Information was correctly returned
   :statuscode 500: Internal rotki error

Dealing with skipped external events
========================================

.. http:get:: /api/(version)/history/skipped_external_events

   Doing a GET on this endpoint will return a summary of skipped external events in the DB.


  **Example Request**

  .. http:example:: curl wget httpie python-requests

    GET /api/1/history/skipped_external_events HTTP/1.1
    Host: localhost:5042


  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
	    "locations": {
	        "kraken": 5,
	        "binance": 3
            },
	    "total": 8
        },
        "message": ""
      }

  :resjson bool result: The mapping of skipped event locations to the number of skipped events per location.

  :statuscode 200: All okay
  :statuscode 500: Internal rotki error


.. http:put:: /api/(version)/history/skipped_external_events
.. http:patch:: /api/(version)/history/skipped_external_events

   Doing a PUT on this endpoint with a filepath path as argument will export all skipped external events in a csv to that directory.
   Doing a PATCH on this endpoint will download all skipped external events in a csv file.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/history/skipped_external_events HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {"directory_path": "/home/username/path/to/csvdir"}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
          "message": ""
      }

   :resjson bool result: Boolean denoting success or failure.
   :statuscode 200: File were exported successfully
   :statuscode 400: Provided JSON is in some way malformed or given string is not a directory.
   :statuscode 404: No file was found when trying to export the events in CSV.
   :statuscode 401: No user is currently logged in.
   :statuscode 409: No permissions to write in the given directory. Check error message.
   :statuscode 500: Internal rotki error.


.. http:post:: /api/(version)/history/skipped_external_events

   Doing a POST on this endpoint will try to reprocess all skipped external events saved in the DB.


  **Example Request**

  .. http:example:: curl wget httpie python-requests

    POST /api/1/history/skipped_external_events HTTP/1.1
    Host: localhost:5042


  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {"total": 10, "successful": 5},
        "message": ""
      }

  :resjson int total: The total number of skipped events that we tried to reprocess
  :resjson int succesfull: The number of skipped events that we reprocessed successfully and were thus deleted from the skipped events table.

  :statuscode 200: Reprocessing went fine.
  :statuscode 409: An issue occurred during reprocessing
  :statuscode 500: Internal rotki error


Managing custom accounting rules
========================================

.. http:post:: /api/(version)/accounting/rules

   Doing a POST on this endpoint will allow querying the accounting rules by a list of possible values. This endpoint allows pagination.


  **Example Request**

  .. http:example:: curl wget httpie python-requests

      POST /api/1/accounting/rules HTTP/1.1
      Host: localhost:5042

      {
         "event_types":["deposit", "withdrawal"],
         "counterparties":["uniswap", "compound"]
      }

  :reqjsonarr optional[array[string]] event_types: List of possible event types to use while filtering.
  :reqjsonarr optional[array[string]] event_subtypes: List of possible event subtypes to use while filtering.
  :reqjsonarr optional[array[string]] counterparties: List of possible counterparties to use while filtering. Instead of a string a null value can also be given to mean counterparty being None.


  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
      "result":{
         "entries":[{
            "taxable":false,
            "count_cost_basis_pnl": {"value": true},
            "count_entire_amount_spend":{"value": false},
            "accounting_treatment":null,
            "identifier":2,
            "event_type":"staking",
            "event_subtype":"spend",
            "counterparty":"compound"
         }],
         "entries_found":1,
         "entries_total":1,
         "entries_limit":-1
      },
      "message":""
      }

  :resjson array entries: List of all the rules with their identifier. For the meaning of each field refer to :ref:`accounting_rules_fields`
  :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
  :resjson int entries_limit: The limit of entries if free version. Always -1 for this endpoint.
  :resjson int entries_total: The number of total entries ignoring all filters.

  :statuscode 200: All okay
  :statuscode 409: Bad set of filters provided
  :statuscode 500: Internal rotki error


.. http:put:: /api/(version)/accounting/rules

  Doing a PUT request on this endpoint will allow to create a new accounting rule.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      PUT /api/1/accounting/rules HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
         "taxable": {"value": true},
         "count_entire_amount_spend":{"value": false, "linked_setting": "include_crypto2crypto"},
         "count_cost_basis_pnl":{"value": true},
         "event_type":"staking",
         "event_subtype":"spend",
         "counterparty": "compound",
         "accounting_treatment":"swap"
      }

  .. _accounting_rules_fields:

  :reqjsonarr object taxable: If ``value`` is set to ``true`` if the event should be considered as taxable. Allows to link the property to an accounting setting.
  :reqjsonarr object count_entire_amount_spend: If ``value`` is set to ``true`` then the entire amount is counted as a spend. Which means an expense (negative pnl). Allows to link the property to an accounting setting.
  :reqjsonarr object count_cost_basis_pnl: If ``value`` is set to ``true`` then we also count any profit/loss the asset may have had compared to when it was acquired. Allows to link the property to an accounting setting.
  :reqjsonarr string linked_setting: If it takes any value this property will take the value of the provided setting. Can be either `include_gas_costs` or `include_crypto2crypto`.
  :reqjsonarr string event_type: The event type that the rule targets.
  :reqjsonarr string event_subtype: The event subtype that the rule targets.
  :reqjsonarr optional[string] counterparty: The counterparty that the rule targets.
  :reqjsonarr accounting_treatment: Special rule to handle pairs of events. Can be ``swap`` or ``swap with fee``

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
         "result": true,
         "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Entry correctly stored.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data. Combination of type, subtype and counterparty already exists.
  :statuscode 500: Internal rotki error.


.. http:patch:: /api/(version)/accounting/rules

  Doing a PATCH on this endpoint allows to edit an accounting rule. Takes the same parameters as the PUT verb plus the identifier of the entry being updated.

  **Example Request**:

  .. http:example:: curl wget httpie python-requests

    PATCH /api/1/accounting/rules HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

      {
         "identifier": 1,
         "taxable": true,
         "count_entire_amount_spend": {"value": false},
         "count_cost_basis_pnl":{"value": true},
         "event_type": "staking",
         "event_subtype": "spend",
         "counterparty": "uniswap",
         "accounting_treatment": "swap"
      }

  :ref:`accounting_rules_fields`

  :reqjsonarr integer identifier: The id of the rule being updated.

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Entry correctly updated.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data. Entry doesn't exist. Combination of type, subtype and counterparty already exists.
  :statuscode 500: Internal rotki error.

.. http:delete:: /api/(version)/accounting/rules

  Doing a DELETE on this endpoint allows deleting a rule by their identifier.

  **Example Request**:

  .. http:example:: curl wget httpie python-requests

    PATCH /api/1/accounting/rules HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

    {
      "identifier": 2
    }

  :reqjsonarr integer identifier: The identifier of the rule that will be deleted

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Entry correctly deleted.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data. Or entry doesn't exist.
  :statuscode 500: Internal rotki error.


Accounting rules linkable properties
========================================
.. http:get:: /api/(version)/accounting/rules/info

   Doing a GET on this endpoint will return a mapping of the properties that can be linked for accounting rules.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      GET /api/1/accounting/rules/info HTTP/1.1
      Host: localhost:5042

  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": {
            "count_entire_amount_spend":["include_gas_costs", "include_crypto2crypto"],
            "count_cost_basis_pnl":["include_gas_costs", "include_crypto2crypto"]
         },
        "message": ""
      }


  :resjson object result: A mapping of the properties that can be linked to the list of settings configurations that can be used for that field.

  :statuscode 200: All okay
  :statuscode 500: Internal rotki error


Solving conflicts in accounting rules
========================================
.. http:post:: /api/(version)/accounting/rules/conflicts

   Doing a POST on this endpoint will return the list of conflicts for accounting rules providing the local version and remote version to compare them. It allows pagination by ``limit`` and ``offset``.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      POST /api/1/accounting/rules/conflicts HTTP/1.1
      Host: localhost:5042

  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
      "result":{
         "entries":[
            {
               "local_id": 1,
               "local_data":{
                  "taxable":{
                     "value":true,
                     "linked_setting":"include_crypto2crypto"
                  },
                  "count_cost_basis_pnl":{
                     "value":true
                  },
                  "count_entire_amount_spend":{
                     "value":false,
                     "linked_setting":"include_crypto2crypto"
                  },
                  "accounting_treatment":"None",
                  "event_type":"spend",
                  "event_subtype":"return wrapped",
                  "counterparty":"compound"
               },
               "remote_data":{
                  "taxable":{
                     "value":false
                  },
                  "count_cost_basis_pnl":{
                     "value":false
                  },
                  "count_entire_amount_spend":{
                     "value":false
                  },
                  "accounting_treatment":"swap",
                  "event_type":"spend",
                  "event_subtype":"return wrapped",
                  "counterparty":"compound"
               }
            }
         ],
         "entries_found":1,
         "entries_total":1,
         "entries_limit":-1
      },
      "message":""
      }


  :resjson object result: An object, mapping identifiers to the local and remote version of the conflict.

  :statuscode 200: All okay
  :statuscode 401: No user is currently logged in
  :statuscode 500: Internal rotki error


.. http:patch:: /api/(version)/accounting/rules/conflicts

   Doing a PATCH on this endpoint will apply a conflict resolution method for the selected accounting rules.

  **Example Request**

  .. note::
     Either ``conflicts`` or ``solve_all_using`` need to be provided but not both together.

  .. http:example:: curl wget httpie python-requests

      PATH /api/1/accounting/rules/conflicts HTTP/1.1
      Host: localhost:5042

      {"conflicts": [{"local_id": "1", "solve_using": "remote"}]}


  :reqjsonarr string local_id: The identifier of the rule that will be updated.
  :reqjsonarr string solve_using: Either ``remote`` or ``local``.
  :reqjsonarr string solve_all_using: Either ``remote`` or ``local``. If this is given it should be the only key in the request.

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Conflicts resolved succesfully.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Couldn't find the rule locally.
  :statuscode 500: Internal rotki error.


Managing calendar entries
==========================

.. http:post:: /api/(version)/calendar

   Doing a POST on this endpoint will allow querying the calendar entries by some of their attributes.


  **Example Request**

  .. http:example:: curl wget httpie python-requests

      POST /api/(version)/calendar HTTP/1.1
      Host: localhost:5042

      {
         "from_timestamp": 1977652400,
         "to_timestamp": 1977652511,
         "accounts": [{"address": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12"}, {"address": "0xc37b40ABdB939635068d3c5f13E7faF686F03B65", "blockchain": "gnosis"}]
         "counterparty": 'ens'
      }

  :reqjsonarr optional[list[object]] accounts: List of addresses + their chain linked to the calendar events. The blockchain part can be omitted and it will return information for the address in all the chains.
  :reqjsonarr optional[integer] identifiers: List of identifiers linked to the calendar events.
  :reqjsonarr string counterparty: Counterparty used to filter the events.
  :reqjsonarr string name: Substring used to filter for in the ``name`` attribute when querying calendar events.
  :reqjsonarr string description: Substring used to filter for in the ``description`` attribute when querying calendar events.
  :resjson int from_timestamp: The earliest timestamp of the events queried.
  :resjson int to_timestamp: The latest timestamp of the events queried.

  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
          "entries":[
            {
              "identifier":1,
              "name":"ENS renewal",
              "description":"Renew yabir.eth extended",
              "counterparty":"ENS",
              "timestamp":1977652411,
              "address":"0xc37b40ABdB939635068d3c5f13E7faF686F03B65"
            },
            {
              "identifier":2,
              "name":"CRV unlock",
              "description":"Unlock date for CRV",
              "counterparty":"CURVE",
              "timestamp":1851422011,
              "address":"0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12"
            }
          ],
          "entries_found":2,
          "entries_total":2,
          "entries_limit":-1
        }
      }

  :resjson array entries: List of all the calendar events with their identifier.
  :resjson int entries_found: The number of entries found for the current filter. Ignores pagination.
  :resjson int entries_limit: The limit of entries if free version. Always -1 for this endpoint.
  :resjson int entries_total: The number of total entries ignoring all filters.

  :statuscode 200: All okay
  :statuscode 401: No user is currently logged in.
  :statuscode 500: Internal rotki error


.. http:put:: /api/(version)/calendar

  Doing a PUT request on this endpoint will allow to create a new calendar entry.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      PUT /api/(version)/calendar HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
        "timestamp":1869737344,
        "name":"ENS renewal",
        "description":"Renew yabir.eth",
        "counterparty":"ENS",
        "address":"0xc37b40ABdB939635068d3c5f13E7faF686F03B65",
        "color": "ffffff"
      }

  .. _calendar_fields:

  :resjson integer timestamp: Timestamp of the event in the calendar.
  :resjson string name: Name of the event.
  :resjson optional[string] description: Longer description given to the event.
  :resjson string counterparty: A protocol counterparty given to the calendar event. Missing if it doesn't have a value.
  :resjson string address: Address linked to the calendar event. Missing if it doesn't have a value.
  :resjson string color: The color to render the event in the frontend with. Missing if it doesn't have a value.

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
         "result": {"entry_id": 1},
         "message": ""
      }

  :resjson object result: object with the identifier of the calendar entry created. 
  :statuscode 200: Entry correctly stored.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data.
  :statuscode 500: Internal rotki error.


.. http:patch:: /api/(version)/calendar

  Doing a PATCH on this endpoint allows to edit a calendar entry. Takes the same parameters as the PUT verb plus the identifier of the entry being updated.

  **Example Request**:

  .. http:example:: curl wget httpie python-requests

    PATCH /api/(version)/calendar HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

      {
        "identifier": 1,
        "timestamp":1869737344,
        "name":"ENS renewal",
        "description":"Renew yabir.eth",
        "counterparty":"ENS",
        "address":"0xc37b40ABdB939635068d3c5f13E7faF686F03B65"
      }

  :ref:`calendar_fields`

  :reqjsonarr integer identifier: The id of the event being updated.

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
         "result": {"entry_id": 1},
         "message": ""
      }

  :resjson object result: object with the identifier of the calendar entry updated. 
  :statuscode 200: Entry correctly updated.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data. Event not found.
  :statuscode 500: Internal rotki error.


.. http:delete:: /api/(version)/calendar

  Doing a DELETE on this endpoint allows deleting a calendar event by their identifier.

  **Example Request**:

  .. http:example:: curl wget httpie python-requests

    PATCH /api/(version)/calendar HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

    {
      "identifier": 2
    }

  :reqjsonarr integer identifier: The identifier of the event that will be deleted

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Entry correctly deleted.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data. Entry doesn't exist.
  :statuscode 500: Internal rotki error.


Managing calendar reminders
============================

.. http:post:: /api/(version)/calendar/reminders

   Doing a POST on this endpoint will allow querying the calendar reminders using the identifier of the associated calendar entry.


  **Example Request**

  .. http:example:: curl wget httpie python-requests

      POST /api/(version)/calendar/reminders HTTP/1.1
      Host: localhost:5042

      {"identifier": 1}

  :resjson int identifier: Identifier of the calendar entry linked to the reminder.

  **Example Response**

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result":{
          "entries":[
            {
              "identifier":1,
              "event_id": 1,
              "secs_before": 213234124
            }, {
              "identifier":2,
              "event_id": 1,
              "secs_before": 2132341253
            },
          ]
        }
      }

  :resjson array entries: List of all the calendar reminders linked to the provided calendar event.

  :statuscode 200: All okay
  :statuscode 401: No user is currently logged in.
  :statuscode 500: Internal rotki error


.. http:put:: /api/(version)/calendar/reminders

  Doing a PUT request on this endpoint will allow to create new calendar reminder entries. If any of the entries fails to get added the key ``failed`` will be populated in the response.

  **Example Request**

  .. http:example:: curl wget httpie python-requests

      PUT /api/(version)/calendar/reminders HTTP/1.1
      Host: localhost:5042
      Content-Type: application/json;charset=UTF-8

      {
        "reminders": [
         {"secs_before": 1869737344, "event_id": 1},
         {"secs_before": 1869737344, "event_id": 100}
        ]
      }

  .. _calendar_reminder_fields:

  :resjson integer secs_before: Seconds before the event timestamp to trigger a notification.
  :resjson integer event_id: Identifier of a valid calendar entry.

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
         "result": {"success": [1], "failed": [100]},
         "message": ""
      }

  :resjson object result: object with the ids of the events for which the reminders were created succesfully and for which it failed. If none failed the failed key is not returned.
  :statuscode 200: Entry correctly stored.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data.
  :statuscode 500: Internal rotki error.


.. http:patch:: /api/(version)/calendar/reminders

  Doing a PATCH on this endpoint allows to edit a calendar reminder. Takes the same parameters as the PUT verb plus the identifier of the entry being updated.

  **Example Request**:

  .. http:example:: curl wget httpie python-requests

    PATCH /api/(version)/calendar HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

      {
        "identifier": 1,
        "secs_before": 1869737344,
        "event_id": 1
      }

  :ref:`calendar_reminder_fields`

  :reqjsonarr integer identifier: The id of the event being updated.

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
         "result": {"entry_id": 1},
         "message": ""
      }

  :resjson object result: object with the identifier of the calendar reminder updated. 
  :statuscode 200: Entry correctly updated.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data. Event not found.
  :statuscode 500: Internal rotki error.


.. http:delete:: /api/(version)/calendar/reminders

  Doing a DELETE on this endpoint allows deleting a calendar reminder by their identifier.

  **Example Request**:

  .. http:example:: curl wget httpie python-requests

    PATCH /api/(version)/calendar/reminders HTTP/1.1
    Host: localhost:5042
    Content-Type: application/json;charset=UTF-8

    {
      "identifier": 2
    }

  :reqjsonarr integer identifier: The identifier of the reminder that will be deleted

  **Example Response**:

  .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "result": true,
        "message": ""
      }

  :resjson bool result: Boolean denoting success or failure.
  :statuscode 200: Entry correctly deleted.
  :statuscode 401: No user is currently logged in.
  :statuscode 409: Failed to validate the data. Entry doesn't exist.
  :statuscode 500: Internal rotki error.
