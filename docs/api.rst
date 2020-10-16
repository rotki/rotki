Rotki API
##################################################
.. toctree::
  :maxdepth: 2


Introduction
*************

When the Rotki backend runs it exposes an HTTP Rest API that is accessed by either the electron front-end or a web browser. The endpoints accept and return JSON encoded objects. All queries have the following prefix: ``/api/<version>/`` where ``version`` is the current version. The current version at the moment is ``1``.


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
   :statuscode 500: Internal Rotki error

.. http:put:: /api/(version)/users

   By doing a ``PUT`` at this endpoint you can create a new user

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/users HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript

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
   :reqjson string[optional] premium_api_key: An optional api key if the user has a Rotki premium account.
   :reqjson string[optional] premium_api_secret: An optional api secret if the user has a Rotki premium account.
   :reqjson object[optional] initial_settings: Optionally provide DB settings to set when creating the new user. If not provided, default settings are used.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "exchanges": ["kraken", "poloniex", "binance"],
              "settings": {
                  "have_premium": true,
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
                  "last_balance_save": 1571552172,
                  "submit_usage_analytics": true,
                  "kraken_account_type": "intermediate",
                  "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"]
              }
          },
          "message": ""
      }

   :resjson object result: For succesful requests, result contains the currently connected exchanges, and the user's settings. For details on the user settings refer to the `Getting or modifying settings`_ section.
   :statuscode 200: Adding the new user was succesful
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User already exists. Another user is already logged in. Given Premium API credentials are invalid. Permission error while trying to access the directory where Rotki saves data.
   :statuscode 500: Internal Rotki error

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
   :reqjson bool sync_approval: A string denoting if the user approved an initial syncing of data from premium. Valid values are ``"unknown"``, ``"yes"`` and ``"no"``. Should always be ``"unknown"`` at first and only if the user approves should a login with approval as ``"yes`` be sent. If he does not approve a login with approval as ``"no"`` should be sent. If there is the possibility of data sync from the premium server and this is ``"unknown"`` the login will fail with an appropriate error asking the consumer of the api to set it to ``"yes"`` or ``"no"``.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "exchanges": ["kraken", "poloniex", "binance"],
              "settings": {
                  "have_premium": true,
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
                  "last_balance_save": 1571552172,
                  "submit_usage_analytics": true,
                  "kraken_account_type": "intermediate"
                  "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"]
              }
          },
          "message": ""
      }

   :resjson object result: For succesful requests, result contains the currently connected exchanges,and the user's settings. For details on the user settings refer to the `Getting or modifying settings`_ section.
   :statuscode 200: Logged in succesfully
   :statuscode 300: Possibility of syncing exists and the login was sent with sync_approval set to ``"unknown"``. Consumer of api must resend with ``"yes"`` or ``"no"``. In this case the result will contain an object with a payload for the message under the ``result`` key and the message under the ``message`` key. The payload has the following keys: ``local_size``, ``remote_size``, ``local_last_modified``, ``remote_last_modified``.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 401: Provided password is wrong for the user or some other authentication error.
   :statuscode 409: Another user is already logged in. User does not exist. There was a fatal error during the upgrade of the DB. Permission error while trying to access the directory where Rotki saves data.
   :statuscode 500: Internal Rotki error

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

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: Logged out succesfully
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in, or current logged in user is different to the one requested for logout.
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

   :resjson bool result: The result field in this response is a simple boolean value indicating success or failure.
   :statuscode 200: API key/secret set successfully
   :statuscode 400: Provided JSON is in some way malformed. For example invalid API key format
   :statuscode 401: Provided API key/secret does not authenticate.
   :statuscode 409: User is not logged in, or user does not exist
   :statuscode 500: Internal Rotki error

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
   :statuscode 500: Internal Rotki error

.. http:put:: /api/(version)/premium/sync

   By doing a ``PUT`` at this endpoint you can backup or restore the database for the logged-in user using premium sync.

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/premium/sync HTTP/1.1
      Host: localhost:5042

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
   :statuscode 500: Internal Rotki error
   :statuscode 502: The external premium service could not be reached or returned unexpected response.

Modify user password
========================

.. http:patch:: /api/(version)/users/(username)/password

   By doing a ``PATCH`` at this endpoint you can change the specific user's password as long as that user is logged in.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/users/john/password HTTP/1.1
      Host: localhost:5042

      {
          "current_password": "supersecret"
          "new_password": "evenmoresecret",
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
   :statuscode 500: Internal Rotki error

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
   :statuscode 500: Internal Rotki error

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
   :statuscode 500: Internal Rotki error

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
              "last_balance_save": 1571552172,
              "submit_usage_analytics": true,
              "kraken_account_type": "intermediate",
              "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"]
          },
          "message": ""
      }

   .. _balance_save_frequency:

   :resjson int version: The database version
   :resjson int last_write_ts: The unix timestamp at which an entry was last written in the database
   :resjson bool premium_should_sync: A boolean denoting whether premium users database should be synced from/to the server
   :resjson bool include_crypto2crypto: A boolean denoting whether crypto to crypto trades should be counted.
   :resjson bool anonymized_logs: A boolean denoting whether sensitive logs should be anonymized.
   :resjson int last_data_upload_ts: The unix timestamp at which the last data upload to the server happened.
   :resjson int ui_floating_precision: The number of decimals points to be shown for floating point numbers in the UI. Can be between 0 and 8.
   :resjson int taxfree_after_period: The number of seconds after which holding a crypto in FIFO order is considered no longer taxable. Must be either a positive number, or -1. 0 is not a valid value. The default is 1 year, as per current german tax rules. Can also be set to ``-1`` which will then set the taxfree_after_period to ``null`` which means there is no taxfree period.
   :resjson int balance_save_frequency: The number of hours after which user balances should be saved in the DB again. This is useful for the statistics kept in the DB for each user. Default is 24 hours. Can't be less than 1 hour.
   :resjson bool include_gas_costs: A boolean denoting whether gas costs should be counted as loss in profit/loss calculation.
   :resjson string historical_data_start: A date in the DAY/MONTH/YEAR format at which we consider historical data to have started.
   :resjson string eth_rpc_endpoint: A URL denoting the rpc endpoint for the ethereum node to use when contacting the ethereum blockchain. If it can not be reached or if it is invalid etherscan is used instead.
   :resjson string main_currency: The FIAT currency to use for all profit/loss calculation. USD by default.
   :resjson string date_display_format: The format in which to display dates in the UI. Default is ``"%d/%m/%Y %H:%M:%S %Z"``.
   :resjson int last_balance_save: The timestamp at which the balances were last saved in the database.
   :resjson bool submit_usage_analytics: A boolean denoting wether or not to submit anonymous usage analytics to the Rotki server.
   :resjson string kraken_account_type: The type of the user's kraken account if he has one. Valid values are "starter", "intermediate" and "pro".
   :resjson list active_module: A list of strings denoting the active modules with which Rotki is running.

   :statuscode 200: Querying of settings was succesful
   :statuscode 409: There is no logged in user
   :statuscode 500: Internal Rotki error

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
   :reqjson bool[optional] anonymized_logs: A boolean denoting whether sensitive logs should be anonymized.
   :reqjson int[optional] ui_floating_precision: The number of decimals points to be shown for floating point numbers in the UI. Can be between 0 and 8.
   :resjson int[optional] taxfree_after_period: The number of seconds after which holding a crypto in FIFO order is considered no longer taxable. Must be either a positive number, or -1. 0 is not a valid value. The default is 1 year, as per current german tax rules. Can also be set to ``-1`` which will then set the taxfree_after_period to ``null`` which means there is no taxfree period.
   :reqjson int[optional] balance_save_frequency: The number of hours after which user balances should be saved in the DB again. This is useful for the statistics kept in the DB for each user. Default is 24 hours. Can't be less than 1 hour.
   :reqjson bool[optional] include_gas_costs: A boolean denoting whether gas costs should be counted as loss in profit/loss calculation.
   :reqjson string[optional] historical_data_start: A date in the DAY/MONTH/YEAR format at which we consider historical data to have started.
   :reqjson string[optional] eth_rpc_endpoint: A URL denoting the rpc endpoint for the ethereum node to use when contacting the ethereum blockchain. If it can not be reached or if it is invalid etherscan is used instead.
   :reqjson string[optional] main_currency: The FIAT currency to use for all profit/loss calculation. USD by default.
   :reqjson string[optional] date_display_format: The format in which to display dates in the UI. Default is ``"%d/%m/%Y %H:%M:%S %Z"``.
   :reqjson bool[optional] submit_usage_analytics: A boolean denoting wether or not to submit anonymous usage analytics to the Rotki server.
   :reqjson list active_module: A list of strings denoting the active modules with which Rotki should run.

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
              "last_balance_save": 1571552172,
              "submit_usage_analytics": true,
              "kraken_account_type": "intermediate",
              "active_modules": ["makerdao_dsr", "makerdao_vaults", "aave"]
          },
          "message": ""
      }

   :resjson object result: Same as when doing GET on the settings

   :statuscode 200: Modifying settings was succesful
   :statuscode 400: Provided JSON is in some way malformed, of invalid value for a setting.
   :statuscode 409: No user is logged in or tried to set eth rpc endpoint that could not be reached.
   :statuscode 500: Internal Rotki error

Query the result of an ongoing backend task
===========================================

.. http:get:: /api/(version)/tasks

   By querying this endpoint without any given task id a list of all pending/completed tasks is returned.

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
          "result": [4, 23],
          "message": ""
      }

   :resjson list result: A list of integers representing the pending/completed task IDs.

   :statuscode 200: Querying was succesful
   :statuscode 500: Internal Rotki error

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
   :resjson any outcome: IF the result of the task id is not yet ready this should be ``null``. If the task has finished then this would contain the original task response.

   :statuscode 200: The task's outcome is succesfully returned or pending
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 404: There is no task with the given task id
   :statuscode 409: No user is currently logged in
   :statuscode 500: Internal Rotki error

Query the current fiat currencies exchange rate
===============================================

.. http:get:: /api/(version)/fiat_exchange_rates

   Querying this endpoint with a list of strings representing FIAT currencies will return a dictionary of their current exchange rates compared to USD. If no list is given then the exchange rates of all currencies is returned. Providing an empty list is an error.

   .. note::
      This endpoint also accepts parameters as query arguments. List as a query argument here would be given as: ``?currencies=EUR,CNY,GBP``

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/fiat_exchange_rates HTTP/1.1
      Host: localhost:5042

      {"currencies": ["EUR", "CNY", "GBP"]}

   :query strings-list currencies: A comma separated list of fiat currencies to query. e.g.: /api/1/fiat_exchange_rates?currencies=EUR,CNY,GBP
   :reqjson list currencies: A list of fiat currencies to query

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {"EUR": "0.8973438622", "CNY": "7.0837221823", "GBP": "0.7756191673"},
          "message": ""
      }

   :resjson object result: A JSON object with each element being a FIAT currency symbol and each value its USD exchange rate.
   :statuscode 200: The exchange rates have been sucesfully returned
   :statuscode 400: Provided JSON is in some way malformed. Empty currencies list given
   :statuscode 500: Internal Rotki error


Get a list of setup exchanges
==============================

.. http:get:: /api/(version)/exchanges

   Doing a GET on this endpoint will return a list of which exchanges are currently setup for the logged in user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/exchanges HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["kraken", "binance"]
          "message": ""
      }

   :resjson list result: A list of exchange names that have been setup for the logged in user.
   :statuscode 200: The exchanges list has been sucesfully setup
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal Rotki error

Setup or remove an exchange
============================

.. http:put:: /api/(version)/exchanges

   Doing a PUT on this endpoint with an exchange's name, api key and secret will setup the exchange for the current user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/exchanges HTTP/1.1
      Host: localhost:5042

      {"name": "kraken", "api_key": "ddddd", "api_secret": "ffffff", "passphrase": "secret"}

   :reqjson string name: The name of the exchange to setup
   :reqjson string api_key: The api key with which to setup the exchange
   :reqjson string api_secret: The api secret with which to setup the exchange
   :reqjson string passphrase: An optional passphrase, only for exchanges, like coinbase pro, which need a passphrase.

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
   :statuscode 500: Internal Rotki error

.. http:delete:: /api/(version)/exchanges

   Doing a DELETE on this endpoint for a particular exchange name will delete the exchange from the database for the current user.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/exchanges HTTP/1.1
      Host: localhost:5042

      {"name": "kraken"}

   :reqjson string name: The name of the exchange to delete

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
   :statuscode 500: Internal Rotki error

Querying the balances of exchanges
====================================

.. http:get:: /api/(version)/exchanges/balances/(name)

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
   :statuscode 500: Internal Rotki error

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
   :statuscode 500: Internal Rotki error


Purging locally saved data for exchanges
=========================================

.. http:delete:: /api/(version)/exchanges/data/(name)

   Doing a DELETE on the appropriate exchanges trades endpoint will delete the cached trades, deposits and withdrawals for that exchange. If no exchange is given then all exchanges will be affected. Next time exchange history is queried, everything will be queried again, and may take some time.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/exchanges/delete/binance HTTP/1.1
      Host: localhost:5042

      {}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Data succesfully purged.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in. Exchange is not registered or some other error. Check error message for details.
   :statuscode 500: Internal Rotki error

Purging locally saved ethereum transactions
===========================================

.. http:delete:: /api/(version)/blockchains/ETH/transactions

   Doing a DELETE on the transactions endpoint for ETH will purge all locally saved transaction data. Next time transactions are queried all of them will be queried again for all addresses and may take some time.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/ETH/transactions HTTP/1.1
      Host: localhost:5042

      {}


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result": true, "message": "" }

   :statuscode 200: Data succesfully purged.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal Rotki error


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

      {"from_timestamp": 1514764800, "to_timestamp": 1572080165}

   :reqjson int from_timestamp: The timestamp after which to return transactions. If not given zero is considered as the start.
   :reqjson int to_timestamp: The timestamp until which to return transactions. If not given all transactions from ``from_timestamp`` until now are returned.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      { "result":
            "entries": [{
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
            }, {
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
            }],
            "entries_found": 95,
            "entries_limit": 500,
        "message": ""
      }

   :statuscode 200: Transactions succesfull queried
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in or some other error. Check error message for details.
   :statuscode 500: Internal Rotki error
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
   :statuscode 500: Internal Rotki error

Adding new tags
===================

.. http:put:: /api/(version)/tags

   Doing a PUT on the tags endpoint will add a new tag to the application


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/tags/ HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript

      {
            "name": "not public",
            "description": "Accounts that are not publically associated with me",
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

   :reqjson object result: A mapping of the tags Rotki knows about including our newly added tag. Explanation of the response format is seen `here <tags_response_>`_

   :statuscode 200: Tag successfully created.
   :statuscode 400: Provided request JSON is in some way malformed.
   :statuscode 409: User is not logged in. Tag with the same name already exists.
   :statuscode 500: Internal Rotki error

Editing a tag
==============

.. http:patch:: /api/(version)/tags

   Doing a PATCH on the tags endpoint will edit an already existing tag


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/tags/ HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript

      {
            "name": "not public",
            "description": "Accounts that are private",
            "background_color": "f9f9f9",
            "foreground_color": "f2f2f2",
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

   :reqjson object result: A mapping of the tags Rotki knows about including our newley edited tag. Explanation of the response format is seen `here <tags_response_>`_

   :statuscode 200: Tag successfully created.
   :statuscode 400: Provided request JSON is in some way malformed. Or no field to edit was given.
   :statuscode 409: User is not logged in. Tag with the given name does not exist.
   :statuscode 500: Internal Rotki error

Deleting a tag
==============

.. http:delete:: /api/(version)/tags

   Doing a DELETE on the tags endpoint will remove an existing tag


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/tags/ HTTP/1.1
      Host: localhost:5042
      Accept: application/json, text/javascript

      {
            "name": "not public",
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

   :reqjson list result: A mapping of the tags Rotki knows about, now without the tag we just deleted. Explanation of the response format is seen `here <tags_response_>`_

   :statuscode 200: Tag successfully removed.
   :statuscode 400: Provided request JSON is in some way malformed.
   :statuscode 409: User is not logged in. Tag with the given name does not exist.
   :statuscode 500: Internal Rotki error

Querying onchain balances
==========================

.. http:get:: /api/(version)/balances/blockchains/(blockchain)/

   Doing a GET on the blockchains balances endpoint will query on-chain balances for the accounts of the user. Doing a GET on a specific blockchain will query balances only for that chain. Available blockchain names are: ``BTC`` and ``ETH``.

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
                           "DAI": {"amount": "15", "usd_value": "15.21"}
                       },
                       "total_usd_value": "1665.74"
                  }}
              },
              "totals": {
                  "BTC": {"amount": "1", "usd_value": "7540.15"},
                  "ETH": {"amount": "10", "usd_value": "1650.53"},
                  "DAI": {"amount": "15", "usd_value": "15.21"}
              }
          },
          "message": ""
      }

   :resjson object per_account: The blockchain balances per account per asset. Each element of this object has an asset as its key. Then each asset has an address for that blockchain as its key and each address an object with the following keys: ``"amount"`` for the amount stored in the asset in the address and ``"usd_value"`` for the equivalent $ value as of the request. Ethereum accounts have a mapping of tokens owned by each account. BTC accounts are separated in standalone accounts and in accounts that have been derived from an xpub. The xpub ones are listed in a list under the ``"xpubs"`` key. Each entry has the xpub, the derivation path and the list of addresses and their balances.
   :resjson object total: The blockchain balances in total per asset. The format is the same as defined `here <balances_result_>`_.

   :statuscode 200: Balances succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in. Invalid blockchain, or problems querying the given blockchain
   :statuscode 500: Internal Rotki error
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

   Doing a GET on the balances endpoint will query all balances across all locations for the user. That is exchanges, blockchains and all manually tracked balances. And it will return an overview of all queried balances.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/balances/ HTTP/1.1
      Host: localhost:5042

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

   :resjson object result: Each key of the result object is an asset. Each asset's value is another object with the following keys. ``"amount"`` is the amount owned in total for that asset. ``"percentage_of_net_value"`` is the percentage the user's net worth that this asset represents. And finally ``"usd_value"`` is the total $ value this asset is worth as of this query. There is also a ``"location"`` key in the result. In there are the same results as the rest but divided by location as can be seen by the example response above.
   :statuscode 200: Balances succesfully queried.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal Rotki error

Querying all supported assets
================================

.. http:get:: /api/(version)/assets/all

   Doing a GET on the all assets endpoint will return a mapping of all supported assets and their details. The keys are the unique symbol identifier and the values are the details for each asset.

The details of each asset can contain the following keys:

- **type**: The type of asset. Valid values are ethereum token, own chain, omni token and more. For all valid values check here: https://github.com/rotki/rotki/blob/develop/rotkehlchen/assets/resolver.py#L7
- **started**: An optional unix timestamp denoting where we know price data for the asset started
- **ended**: If an asset is no longer in circulation this value should denote the unix timestamp after which price data is no longer available
- **name**: The long name of the asset. Does not need to be the same as the unique symbol identifier
- **forked**: An optional attribute representing another asset out of which this asset forked from. For example ``ETC`` would have ``ETH`` here.
- **swapped_for**: An optional attribute representing another asset for which this asset was swapped for. For example ``VEN`` tokens were at some point swapped for ``VET`` tokens.
- **symbol**: The symbol used for this asset. This is not guaranteed to be unique. Unfortunately some assets use the same symbol as others.
- **ethereum_address**: If the type is ``ethereum_token`` then this will be the hexadecimal address of the token's contract.
- **ethereum_token_decimals**: If the type is ``ethereum_token`` then this will be the number of decimals the token has

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
              "0xBTC": {
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
              "DDF": {
                  "active": false,
                  "ended": 1542153600,
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
              "VEN": {
                  "active": false,
                  "ended": 1533254400,
                  "ethereum_address": "0xD850942eF8811f2A866692A623011bDE52a462C1",
                  "ethereum_token_decimals": 18,
                  "name": "Vechain Token",
                  "started": 1503360000,
                  "swapped_for": "VET",
                  "symbol": "VEN",
                  "type": "ethereum token"
              },
          },
          "message": ""
      }


   :resjson object result: A mapping of asset symbol identifiers to asset details
   :statuscode 200: Assets succesfully queried.
   :statuscode 500: Internal Rotki error

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
   :statuscode 500: Internal Rotki error

Querying asset icons
======================

.. http:get:: /api/(version)/assets/(identifier)/icon/(size)

   Doing a GET on the asset icon endpoint will return the icon of the specified
   size identified with the asset. If size is not provided then the thumb size icon is returned. Possible values for size are ``thumb``, ``small`` and ``large``.

   If we have no icon for an asset a 404 is returned.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/assets/YFI/icon/large HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: image/png

   :resuslt: The data of the image
   :statuscode 200: Icon succesfully queried
   :statuscode 304: Icon data has not changed. Should be cached on the client. This is returned if the given If-Match or If-None-Match header match the etag of the previous response.
   :statuscode 400: Provided JSON is in some way malformed. Either unknown asset or invalid size.
   :statuscode 404: We have no icon for that asset
   :statuscode 500: Internal Rotki error


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
   :statuscode 500: Internal Rotki error.

Statistics for asset balance over time
======================================

.. http:get:: /api/(version)/statistics/balance/(asset name)

   .. note::
      This endpoint is only available for premium users

   .. note::
      This endpoint also accepts parameters as query arguments.

   Doing a GET on the statistics asset balance over time endpoint will return all saved balance entries for an asset. Optionally you can filter for a specific time range by providing appropriate arguments.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/statistics/balance/BTC HTTP/1.1
      Host: localhost:5042

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
   :statuscode 500: Internal Rotki error

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
   :statuscode 500: Internal Rotki error.

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
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. There is a problem reaching the Rotki server.
   :statuscode 500: Internal Rotki error.

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

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "location": "external"}

   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string location: Optionally filter trades by location. A valid location name has to be provided. If missing location filtering does not happen.
   :param int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :param int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :param string location: Optionally filter trades by location. A valid location name has to be provided. If missing location filtering does not happen.

   .. _trades_schema_section:

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "entries": [{
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
              }],
              "entries_found": 95,
              "entries_limit": 250,
          "message": ""
      }

   :resjson object entries: An array of trade objects.
   :resjsonarr string trade_id: The uniquely identifying identifier for this trade.
   :resjsonarr int timestamp: The timestamp at which the trade occured
   :resjsonarr string location: A valid location at which the trade happened
   :resjsonarr string pair: The pair for the trade. e.g. ``"BTC_EUR"``
   :resjsonarr string trade_type: The type of the trade. e.g. ``"buy"`` or ``"sell"``
   :resjsonarr string amount: The amount that was bought or sold
   :resjsonarr string rate: The rate at which 1 unit of ``base_asset`` was exchanges for 1 unit of ``quote_asset``
   :resjsonarr string fee: The fee that was paid, if anything, for this trade
   :resjsonarr string fee_currency: The currency in which ``fee`` is denominated in
   :resjsonarr string link: Optional unique trade identifier or link to the trade. Can be an empty string
   :resjsonarr string notes: Optional notes about the trade. Can be an empty string
   :resjson int entries_found: The amount of trades found for the user. That disregards the filter and shows all trades found.
   :resjson int entries_limit: The trades limit for the account tier of the user. If unlimited then -1 is returned.
   :statuscode 200: Trades are succesfully returned
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is logged in.
   :statuscode 500: Internal Rotki error
   :statuscode 502: Error reaching the remote from which the trades got requested

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

   :resjson object result: Array of trades with the same schema as seen in `this <trades_schema_section_>`_ section.
   :statuscode 200: Trades was succesfully added.
   :statuscode 400: Provided JSON is in some way malformed
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal Rotki error

.. http:patch:: /api/(version)/trades

   Doing a PATCH on this endpoint edits an existing trade in Rotki's currently logged in user using the ``trade_id``.

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

   :resjson object result: A trade with the same schema as seen in `this <trades_schema_section_>`_ section.
   :statuscode 200: Trades was succesfully edited.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The given trade identifier to edit does not exist.
   :statuscode 500: Internal Rotki error.

.. http:delete:: /api/(version)/trades

   Doing a DELETE on this endpoint deletes an existing trade in Rotki's currently logged in user using the ``trade_id``.

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

   :resjson bool result: Boolean indicating succes or failure of the request.
   :statuscode 200: Trades was succesfully deleted.
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is logged in. The given trade identifier to delete does not exist.
   :statuscode 500: Internal Rotki error.

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

      {"from_timestamp": 1451606400, "to_timestamp": 1571663098, "location": "kraken"}

   :reqjson int from_timestamp: The timestamp from which to query. Can be missing in which case we query from 0.
   :reqjson int to_timestamp: The timestamp until which to query. Can be missing in which case we query until now.
   :reqjson string location: Optionally filter trades by location. A valid location name has to be provided. Valid locations are for now only exchanges for deposits/widthrawals.


   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": {
              "entries": [{
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
                  "link": "optional exchange unique id",
              }],
              "entries_found": 80,
              "entries_limit": 100,
          "message": ""
      }

   :resjson object entries: An array of deposit/withdrawal objects
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
   :statuscode 500: Internal Rotki error
   :statuscode 502: Error querying the remote for the asset movements

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
   :statuscode 500: Internal Rotki error.

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
                  "margin_positions_profit_loss": "500",
                  "settlement_losses": "200",
                  "ethereum_transaction_gas_costs": "2.5",
                  "asset_movement_fees": "3.45",
                  "general_trade_profit_loss": "5002",
                  "taxable_trade_profit_loss": "5002",
                  "total_taxable_profit_loss": "6936.05",
                  "total_profit_loss": "6936.05"
              },
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
                  "is_virtual": false
              }],
          },
          "message": ""
      }

   The overview part of the result is a dictionary with the following keys:

   :resjson str loan_profit: The profit from loans inside the given time period denominated in the user's profit currency.
   :resjson str defi_profit_loss: The profit/loss from Decentralized finance events inside the given time period denominated in the user's profit currency.
   :resjson str margin_positions_profit_loss: The profit/loss from margin positions inside the given time period denominated in the user's profit currency.
   :resjson str settlement_losses: The losses from margin settlements inside the given time period denominated in the user's profit currency.
   :resjson str ethereum_transactions_gas_costs: The losses from ethereum gas fees inside the given time period denominated in the user's profit currency.
   :resjson str asset_movement_fees: The losses from exchange deposit/withdral fees inside the given time period denominated in the user's profit currency.
   :resjson str general_trade_profit_loss: The profit/loss from all trades inside the given time period denominated in the user's profit currency.
   :resjson str taxable_trade_profit_loss: The portion of the profit/loss from all trades that is taxable and is inside the given time period denominated in the user's profit currency.
   :resjson str total_taxable_profit_loss: The portion of all profit/loss that is taxable and is inside the given time period denominated in the user's profit currency.
   :resjson str total_profit_loss: The total profit loss inside the given time period denominated in the user's profit currency.

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

   :statuscode 200: History processed and returned succesfully
   :statuscode 400: Provided JSON is in some way malformed.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal Rotki error.

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
   :statuscode 500: Internal Rotki error.

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
              "history_process_start_ts": 1572325881,
              "history_process_current_ts": 1572345881,
              "last_data_upload_ts": 0
          }
          "message": ""
      }

   :resjson int last_balance_save: The last time (unix timestamp) at which balances were saved in the database.
   :resjson bool eth_node_connection: A boolean denoting if the application is connected to an ethereum node. If ``false`` that means we fall back to etherscan.
   :resjson int history_process_start_ts: A unix timestamp indicating the time that the last history processing started. Meant to be queried frequently so that a progress bar can be provided to the user.
   :resjson int history_process_current_ts: A unix timestamp indicating the current time as far as the last history processing is concerned. Meant to be queried frequently so that a progress bar can be provided to the user.
   :statuscode 200: Data were queried succesfully.
   :statuscode 409: No user is currently logged in.
   :statuscode 500: Internal Rotki error.


Getting blockchain account data
===============================
.. http:get:: /api/(version)/blockchains/(name)/

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
           }],
           "message": "",
      }

   :resjson list result: A list with the account data details
   :resjsonarr string address: The address, which is the unique identifier of each account
   :resjsonarr string label: The label to describe the account. Can also be null.
   :resjsonarr list tags: A list of tags associated with the account. Can also be null.

   :statuscode 200: Account data succesfully queried.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal Rotki error

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
                  "protocol": {"name": "Curve", "icon": "http://link"},
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
                  "protocol": {"name": "Compound", "icon": "http://link"},
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
                  "protocol": {"name": "Compound", "icon": "http://link"},
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
                  "protocol": {"name": "Aave", "icon": "http://link"},
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
   :resjsonarr object protocol: The name and icon link of the protocol. Since these names come from Zerion check `here <https://github.com/zeriontech/defi-sdk#supported-protocols>`__ for supported names.
   :resjsonarr string balance_type: One of ``"Asset"`` or ``"Debt"`` denoting that one if deposited asset in DeFi and the other a debt or liability.
   :resjsonarr string base_balance: A single DefiBalance entry. It's comprised of a token address, name, symbol and a balance. This is the actually deposited asset in the protocol. Can also be a synthetic in case of synthetic protocols or lending pools.
   :resjsonarr string underlying_balances: A list of underlying DefiBalances supporting the base balance. Can also be an empty list. The format of each balance is thesame as that of base_balance. For lending this is going to be the normal token. For example for aDAI this is DAI. For cBAT this is BAT etc. For pools this list contains all tokens that are contained in the pool.

   :statuscode 200: Balances succesfully queried.
   :statuscode 409: User is not logged in or if using own chain the chain is not synced.
   :statuscode 500: Internal Rotki error.
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

   :resjson object result: A mapping of accounts to the number of DAI they have locked in DSR and the corresponding USD value. If an account is not in the mapping Rotki does not see anything locked in DSR for it.

   :statuscode 200: DSR succesfully queried.
   :statuscode 409: User is not logged in. Or makerdao module is not activated.
   :statuscode 500: Internal Rotki error.
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

   :resjson object result: A mapping of accounts to the DSR history report of each account. If an account is not in the mapping Rotki does not see anything locked in DSR for it.
   :resjson object movements: A list of deposits/withdrawals to/from the DSR for each account.
   :resjson string gain_so_far: The total gain so far in DAI from the DSR for this account. The amount is the DAI amount and the USD value is the added usd value of all the usd values of each movement again plus the usd value of the remaining taking into account current usd price
   :resjsonarr string movement_type: The type of movement involving the DSR. Can be either "deposit" or "withdrawal".
   :resjsonarr string gain_so_far: The amount of DAI gained for this account in the DSR up until the moment of the given deposit/withdrawal along with the usd value equivalent of the DAI gained for this account in the DSR up until the moment of the given deposit/withdrawal. The rate is the DAI/USD rate at the movement's timestamp.
   :resjsonarr string value: The amount of DAI deposited or withdrawn from the DSR along with the USD equivalent value of the amount of DAI deposited or withdrawn from the DSR. The rate is the DAI/USD rate at the movement's timestamp.
   :resjsonarr int block_number: The block number at which the deposit or withdrawal occured.
   :resjsonarr int tx_hash: The transaction hash of the DSR movement

   :statuscode 200: DSR history succesfully queried.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. Or makerdao module is not activated.
   :statuscode 500: Internal Rotki error
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
              "collateral_asset": "USDC",
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
   :resjsonarr string collateral_asset: The asset deposited in the vault as collateral. As of this writing supported assets are ``["ETH", "BAT", "USDC", "WBTC"]``
   :resjsonarr string collateral: The amount of collateral currently deposited in the vault along with the current value in USD of all the collateral in the vault according to the MakerDAO price feed.
   :resjsonarr string debt: The amount of DAI owed to the vault. So generated DAI plus the stability fee interest. Along with its current usd value.
   :resjsonarr string collateralization_ratio: A string denoting the percentage of collateralization of the vault.
   :resjsonarr string liquidation_ratio: This is the current minimum collateralization ratio. Less than this and the vault is going to get liquidated.
   :resjsonarr string liquidation_price: The USD price that the asset deposited in the vault as collateral at which the vault is going to get liquidated.
   :resjsonarr string stability_fee: The current annual interest rate you have to pay for borrowing collateral from this vault type.
   :statuscode 200: Vaults succesfuly queried
   :statuscode 409: User is not logged in. Or makerdao module is not activated.
   :statuscode 500: Internal Rotki error.
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
   :resjsonarr int creation_ts: The timestamp of the vault's creation.
   :resjsonarr string total_interest_owed: Total amount of DAI lost to the vault as interest rate. This can be negative, if the vault has been liquidated. In that case the negative number is the DAI that is out in the wild and does not need to be returned after liquidation.
   :resjsonarr string total_liquidated: The total amount/usd_value of the collateral asset that has been lost to liquidation. Will be ``0`` if no liquidations happened.
   :resjson object events: A list of all events that occured for this vault
   :resjsonarr string event_type: The type of the event. Valid types are: ``["deposit", "withdraw", "generate", "payback", "liquidation"]``
   :resjsonarr string value: The amount/usd_value associated with the event. So collateral deposited/withdrawn, debt generated/paid back, amount of collateral lost in liquidation.
   :resjsonarr int timestamp: The unix timestamp of the event
   :resjsonarr string tx_hash: The transaction hash associated with the event.

   :statuscode 200: Vault details succesfuly queried
   :statuscode 409: User is not logged in. Or makerdao module is not activated.
   :statuscode 500: Internal Rotki error.
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
                      "DAI": {
                          "balance": {
                              "amount": "350.0",
                              "usd_value": "351.21"
                          },
                          "apy": "3.51%"
                      },
                      "KNC": {
                          "balance": {
                              "amount": "220.21",
                              "usd_value": "363.3465"
                          },
                          "apy": "0.53%"
                      },
                  },
                  "borrowing": {
                      "LEND": {
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
                      "BAT": {
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
   :statuscode 500: Internal Rotki error.
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
		      "asset": "DAI",
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
		      "asset": "DAI",
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
		      "asset": "DAI",
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
		      "asset": "ZRX",
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
		      "DAI": {
		          "amount": "0.9482",
			  "usd_value": "1.001"
		      },
		      "ZRX": {
		          "amount": "0.523",
			  "usd_value": "0.0253"
		      }
		  },
		  "total_lost": {
		      "WBTC": {
		          "amount": "0.3212",
			  "usd_value": "3560.32"
		      }
		  }
              },
              "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
                  "events": [{
                      "event_type": "deposit",
		      "asset": "BAT",
                      "value": {
		          "amount": "500",
			  "usd_value": "124.1"
		      },
                      "block_number": 9149160,
                      "timestamp": 1592706553,
                      "tx_hash": "0x618fc9542890a2f58ab20a3c12d173b3638af11fda813e61788e242b4fc9a755",
		      "log_index": 1
                  }],
                  "total_earned": {
		      "BAT": {
		          "amount": "0.9482",
			  "usd_value": "0.2312"
		      }
		  },
		  "total_lost": {}
              }
          },
          "message": ""
      }

   :resjson object result: A mapping of accounts to the Aave history report of each account. If an account is not in the mapping Rotki does not see anything ever deposited in Aave for it.
   :resjson object events: A list of AaveEvents. Check the fields below for the potential values.
   :resjsonarr string event_type: The type of Aave event. Can be ``"deposit"``, ``"withdrawal"``, ``"interest"``, ``"borrow"``, ``"repay"`` and ``"liquidation"``.
   :resjsonarr int timestamp: The unix timestamp at which the event occured.
   :resjsonarr int block_number: The block number at which the event occured. If the graph is queried this is unfortunately always 0, so UI should not show it.
   :resjsonarr string tx_hash: The transaction hash of the event.
   :resjsonarr int log_index: The log_index of the event. For the graph this is indeed a unique number in combination with the transaction hash, but it's unfortunately not the log index.
   :resjsonarr string asset: This attribute appears in all event types except for ``"liquidation"``. It shows the asset that this event is about. This can only be an underlying asset of an aToken.
   :resjsonarr object value: This attribute appears in all event types except for ``"liquidation"``. The value (amount and usd_value mapping) of the asset for the event. The rate is the asset/USD rate at the events's timestamp.
   :resjsonarr string borrow_rate_mode: This attribute appears only in ``"borrow"`` events. Signifies the type of borrow. Can be either ``"stable"`` or ``"variable"``.
   :resjsonarr string borrow_rate: This attribute appears only in ``"borrow"`` events. Shows the rate at which the asset was borrowed. It's a floating point number. For example ``"0.155434"`` would means 15.5434% interest rate for this borrowing.
   :resjsonarr string accrued_borrow_interest: This attribute appears only in ``"borrow"`` events. Its a floating point number showing the acrrued interest for borrowing the asset so far
   :resjsonarr  object fee: This attribute appears only in ``"repay"`` events. The value (amount and usd_value mapping) of the fee for the repayment. The rate is the asset/USD rate at the events's timestamp.
   :resjsonarr string collateral_asset: This attribute appears only in ``"liquidation"`` events. It shows the collateral asset that the user loses due to liquidation.
   :resjsonarr string collateral_balance: This attribute appears only in ``"liquidation"`` events. It shows the value (amount and usd_value mapping) of the collateral asset that the user loses due to liquidation. The rate is the asset/USD rate at the events's timestamp.
   :resjsonarr string principal_asset: This attribute appears only in ``"liquidation"`` events. It shows the principal debt asset that is repaid due to the liquidation due to liquidation.
   :resjsonarr string principal_balance: This attribute appears only in ``"liquidation"`` events. It shows the value (amount and usd_value mapping) of the principal asset whose debt is repaid due to liquidation. The rate is the asset/USD rate at the events's timestamp.
   :resjson object total_earned: A mapping of asset identifier to total earned (amount + usd_value mapping) for each asset. The total earned is essentially the sum of all interest payments plus the difference between ``balanceOf`` and ``principalBalanceOf`` for each asset.
   :resjson object total_lost: A mapping of asset identifier to total lost (amount + usd_value mapping) for each asset. The total losst for each asset is essentially the accrued interest from borrowing and the collateral lost from liquidations.

   :statuscode 200: Aave history succesfully queried.
   :statuscode 409: No user is currently logged in or currently logged in user does not have a premium subscription. Or aave module is not activated.
   :statuscode 500: Internal Rotki error
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

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
		      "COMP": {
		          "balance" :{
			      "amount": "3.5",
			      "usd_value": "892.5",
			  }
		      }
		  },
                  "lending": {
                      "DAI": {
                          "balance": {
                              "amount": "350.0",
                              "usd_value": "351.21"
                          },
                          "apy": "3.51%"
                      },
                      "WBTC": {
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
                      "BAT": {
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

   :resjson object result: A mapping of all accounts that currently have compound balance to the balances and APY data for each account for lending and borrowing. Each key is an asset and its values are the current balance and the APY in %

   :statuscode 200: Compound balances succesfully queried.
   :statuscode 409: User is not logged in. Or compound module is not activated.
   :statuscode 500: Internal Rotki error.
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
		  "asset": "DAI",
		  "value": {
		      "amount": "10.5",
		      "usd_value": "10.86"
		  },
		  "to_asset": "cDAI",
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
		  "asset": "cDAI",
		  "value": {
		      "amount": "165.21",
		      "usd_value": "12.25"
		  },
		  "to_asset": "DAI",
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
		  "asset": "ZRX",
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
		  "asset": "ZRX",
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
		  "to_asset": "ZRX",
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
		  "asset": "COMP",
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
		      "COMP": {
			      "amount": "3.5",
			      "usd_value": "892.5",
			  },
		       "DAI": {
			      "amount": "250",
			      "usd_value": "261.1",
		      }
		  },
                  "0x1D7D7Eb7035B42F39f200AA3af8a65BC3475A237": {
		      "ZRX": {
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
		      "COMP": {
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
   :statuscode 500: Internal Rotki error.
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
		      "underlying_token": "yDAI+yUSDC+yUSDT+yTUSD",
		      "vault_token": "yyDAI+yUSDC+yUSDT+yTUSD",
		      "underlying_value": {
		          "amount": "25", "usd_value": "150"
		      },
		      "vault_value": {
		          "amount": "19", "usd_value": "150"
		      },
		      "roi": "25.55%",
		  },
		  "YYFI Vault": {
		      "underlying_token": "YFI",
		      "vault_token": "yYFI",
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
		      "underlying_token": "aLINK",
		      "vault_token": "yaLINK",
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
   :statuscode 500: Internal Rotki error.
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
			  "from_asset": "yDAI+yUSDC+yUSDT+yTUSD",
			  "from_value": {
			      "amount": "115000", "usd_value": "119523.23"
			  },
			  "to_asset": "yyDAI+yUSDC+yUSDT+yTUSD",
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
			  "from_asset": "yyDAI+yUSDC+yUSDT+yTUSD",
			  "from_value": {
			      "amount": "108230.234", "usd_value": "125321.24"
			  },
			  "to_asset": "yyDAI+yUSDC+yUSDT+yTUSD",
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
			  "from_asset": "YFI",
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
			  "from_asset": "crvRenWSBTC",
			  "from_value": {
			      "amount": "20", "usd_value": "205213.12"
			  },
			  "to_asset": "ycrvRenWSBTC",
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
   :statuscode 500: Internal Rotki error.
   :statuscode 502: An external service used in the query such as etherscan could not be reached or returned unexpected response.

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
   :statuscode 500: Internal Rotki error


Add address to query per protocol
==================================

.. http:put:: /api/(version)/queried_addresses/

   Doing a PUT on this endpoint will add a new address for querying by a protocol/module. Returns all the queried addresses per module after the addition.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/queried_addresses HTTP/1.1
      Host: localhost:5042

      {
          "module": "aave",
          "address": "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b
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
   :statuscode 500: Internal Rotki error

Remove an address to query per protocol
=========================================

.. http:delete:: /api/(version)/queried_addresses/

   Doing a DELETE on this endpoint will remove an address for querying by a protocol/module. Returns all the queried addresses per module after the deletion.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/queried_addresses HTTP/1.1
      Host: localhost:5042

      {
          "module": "aave",
          "address": "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b
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
   :statuscode 500: Internal Rotki error

Adding blockchain accounts
===========================

.. http:put:: /api/(version)/blockchains/(name)/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the the blockchains endpoint with a specific blockchain URL and a list of account data in the json data will add these accounts to the tracked accounts for the given blockchain and the current user. The updated balances after the account additions are returned.
   If one of the given accounts to add is invalid the entire request will fail.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/blockchains/ETH/ HTTP/1.1
      Host: localhost:5042

      {
          "accounts": [{
                  "address": "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B",
                  "label": "my new metamask",
                  "tags": ["public", "metamask"]
              }, {
                  "address": "0x19b0AD50E768D2376C6BA7de32F426ecE4e03e0b
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
   :statuscode 200: Accounts succesfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal Rotki error
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

      {
          "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
          "derivation_path": "m/0/0",
          "label": "my electrum xpub",
          "tags": ["public", "old"]
      }

   :reqjson string xpub: The extended public key to add
   :reqjsonarr string derivation_path: The derivation path from which to start deriving addresses relative to the xpub.
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
   :statuscode 200: Xpub succesfully added
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Provided tags do not exist. Check message for details.
   :statuscode 500: Internal Rotki error
   :statuscode 502: Error occured with some external service query such as blockcypher. Check message for details.

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

      {
          "xpub": "xpub68V4ZQQ62mea7ZUKn2urQu47Bdn2Wr7SxrBxBDDwE3kjytj361YBGSKDT4WoBrE5htrSB8eAMe59NPnKrcAbiv2veN5GQUmfdjRddD1Hxrk",
          "derivation_path": "m/0/0",
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
   :statuscode 200: Xpub succesfully removed
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to add contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Check message for details.
   :statuscode 500: Internal Rotki error
   :statuscode 502: Error occured with some external service query such as blockcypher. Check message for details.

Editing blockchain account data
=================================

.. http:patch:: /api/(version)/blockchains/(name)/


   Doing a PATCH on the the blockchains endpoint with a specific blockchain URL and a list of accounts to edit will edit the label and tags for those accounts.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PATCH /api/1/blockchains/ETH/ HTTP/1.1
      Host: localhost:5042

      {
          "accounts": [{
              "address": "0x78b0AD50E768D2376C6BA7de33F426ecE4e03e0B",
              "label": "my new metamask",
              "tags": ["public", metamask"]
              }, {
              "address": "johndoe.eth",
              "label": "my hardware wallet"
              }]
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

   :resjson list result: A list containing the blockchain account data as also defined `here <blockchain_accounts_result_>`_.

   :statuscode 200: Accounts succesfully edited
   :statuscode 400: Provided JSON or data is in some way malformed. Given list to edit is empty.
   :statuscode 409: User is not logged in. An account given to edit does not exist or a given tag does not exist.
   :statuscode 500: Internal Rotki error

Removing blockchain accounts
==============================

.. http:delete:: /api/(version)/blockchains/(name)/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a DELETE on the the blockchains endpoint with a specific blockchain URL and a list of accounts in the json data will remove these accounts from the tracked accounts for the given blockchain and the current user. The updated balances after the account deletions are returned.
    If one of the given accounts to add is invalid the entire request will fail.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/blockchains/ETH/tokens HTTP/1.1
      Host: localhost:5042

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
                  "BTC": {"amount": "1", "usd_value": "7540.15"},
              }
          },
          "message": ""
      }

   :resjson object result: An object containing the ``"per_account"`` and ``"totals"`` keys as also defined `here <blockchain_balances_result_>`_.
   :statuscode 200: Accounts succesfully deleted
   :statuscode 400: Provided JSON or data is in some way malformed. The accounts to remove contained invalid addresses or were an empty list.
   :statuscode 409: User is not logged in. Some error occured when re-querying the balances after addition. Check message for details.
   :statuscode 500: Internal Rotki error
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
   :statuscode 500: Internal Rotki error

Adding manually tracked balances
====================================

.. http:put:: /api/(version)/balances/manual/

   .. note::
      This endpoint can also be queried asynchronously by using ``"async_query": true``

   Doing a PUT on the the manually tracked balances endpoint you can add a balance for an asset that Rotki can't automatically detect, along with a label identifying it for you and any number of tags.

   .. _manually_tracked_balances_section:


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/balances/manual/ HTTP/1.1
      Host: localhost:5042

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

   :reqjson list[object] balances: A list of manually tracked balances to add to Rotki
   :reqjsonarr string asset: The asset that is being tracked
   :reqjsonarr string label: A label to describe where is this balance stored. Must be unique between all manually tracked balance labels.
   :reqjsonarr string amount: The amount of asset that is stored.
   :reqjsonarr list[optional] tags: An optional list of tags to attach to the this manually tracked balance.
   :reqjsonarr string location: The location where the balance is saved. Can be one of: ["external", "kraken", "poloniex", "bittrex", "binance", "bitmex", "coinbase", "banks", "blockchain", "coinbasepro", "gemini"]

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
   :statuscode 500: Internal Rotki error
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

      {
          "balances": [{
                  "asset": "XMR",
                  "label": "My monero wallet",
                  "amount": "4.5",
                  "location": "blockchain"
                  },{
                  "asset": "ETH",
                  "label" "My favorite wallet",
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
   :statuscode 500: Internal Rotki error
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
   :statuscode 500: Internal Rotki error
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
   :statuscode 500: Internal Rotki error
   :statuscode 502: Could not connect to or got unexpected response format from Rotki server


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

      {
          "watchers": [{
            "type": "makervault_collateralization_ratio",
            "args": {"ratio": "200.5", "op": "gt", "vault_id": "24"}
            }, {
             "type": "makervault_collateralization_ratio",
             "args": {"ratio": "185.55", "op": "lt","vault_id": "456"}
            }],
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
   :statuscode 500: Internal Rotki error
   :statuscode 502: Could not connect to or got unexpected response format from Rotki server

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

      {
          "watchers": [{
            "identifier": "6h3m7vRrLLOipwNmzhAVdo6FaGlr0XKGYLyjHqWa2KQ=",
            "type": "makervault_collateralization_ratio",
            "args": {"ratio": "200.5", "op": "gt", "vault_id": "24"}
            }, {
             "identifier: "7a4m7vRrLLOipwNmzhAVdo6FaGgr0XKGYLyjHqWa2KQ=",
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
   :statuscode 500: Internal Rotki error
   :statuscode 502: Could not connect to or got unexpected response format from Rotki server

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
   :statuscode 500: Internal Rotki error
   :statuscode 502: Could not connect to or got unexpected response format from Rotki server

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
          "result": ["1ST", "DAO"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets succesfully queried
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal Rotki error

.. http:put:: /api/(version)/assets/ignored/

   Doing a PUT on the ignored assets endpoint will add new assets to the ignored assets list. Returns the new list with the added assets in the response.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/assets/ignored HTTP/1.1
      Host: localhost:5042

      {"assets": ["GNO"]}

   :reqjson list assets: A list of asset symbols to add to the ignored assets.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["1ST", "DAO", "GNO"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets succesfully added
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. One of the assets provided is already on the list.
   :statuscode 500: Internal Rotki error

.. http:delete:: /api/(version)/assets/ignored/

   Doing a DELETE on the ignored assets endpoint will remove the given assets from the ignored assets list. Returns the new list without the removed assets in the response.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      DELETE /api/1/assets/ignored HTTP/1.1
      Host: localhost:5042

      {"assets": ["DAO"]}

   :reqjson list assets: A list of asset symbols to remove from the ignored assets.

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": ["1ST"]
          "message": ""
      }

   :resjson list result: A list of asset names that are currently ignored.
   :statuscode 200: Assets succesfully removed
   :statuscode 400: Provided JSON or data is in some way malformed.
   :statuscode 409: User is not logged in. One of the assets provided is not on the list.
   :statuscode 500: Internal Rotki error

Querying the version
====================

.. http:get:: /api/(version)/version

   Doing a GET on the version endpoint will return information about the version of Rotki. If there is a newer version then ``"download_url"`` will be populated. If not then only ``"our_version"`` and ``"latest_version"`` will be. There is a possibility that latest version may not be populated due to github not being reachable.


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
              "our_version": "1.0.3",
              "latest_version": "1.0.4",
              "download_url": "https://github.com/rotki/rotki/releases/tag/v1.0.4"
          },
          "message": ""
      }

   :resjson str our_version: The version of Rotki present in the system
   :resjson str latest_version: The latest version of Rotki available
   :resjson str url: URL link to download the latest version

   :statuscode 200: Version information queried
   :statuscode 500: Internal Rotki error

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
   :statuscode 500: Internal Rotki error

Data imports
=============

.. http:get:: /api/(version)/import

   Doing a PUT on the data import endpoint will facilitate importing data from external sources. The arguments are the source of data import and the filepath to the data for importing.


   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      PUT /api/1/import HTTP/1.1
      Host: localhost:5042

      {"source": "cointracking.info", "filepath": "/path/to/data/file"}

   :reqjson str source: The source of the data to import. Valid values are ``"cointracking.info"``
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
   :statuscode 409: User is not logged in.
   :statuscode 500: Internal Rotki error
