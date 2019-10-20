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

Endpoints
***********

In this section we will see the information about the individual endpoints of the API and detailed explanation of how each one can be used to interact with Rotki.

Logging out of the current user account
=======================================

.. http:get:: /api/(version)/logout

   With this endpoint you can logout from your currently logged in account. All user related data will be saved in the database, memory cleared and encrypted database connection closed.

   **Example Request**:

   .. http:example:: curl wget httpie python-requests

      GET /api/1/logout HTTP/1.1
      Host: localhost:5042

   **Example Response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
          "result": true,
	  "message": ""
      }


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
   :statuscode 409: Invalid input, e.g. not the correct type for a setting
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

   The following is an example response of an async query to exchange balances.

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
