Rotki Contribution Guide
##############################

Rotki is an opensource project so help is really appreciated.

Bug Reporting
*****************

Use the `proper template <https://github.com/rotki/rotki/issues/new?template=bug_report.md>`_ to create bug report issues.

Make sure to check the issue tracker for similar issues before reporting. If this is a new issue then provide a detailed description of the problem, what happened and what you were expecting to happen instead.

Also provide a detailed description of your system and of the rotki version used as the issue template explains.

Feature Requests
********************

Use the `feature request <https://github.com/rotki/rotki/issues/new?template=feature_request.md>`_ template.

Describe exactly what it is that you would like to see added to rotki and why that would provide additional value.

Please note that feature requests are just that. Requests. There is no guarantee that they will be worked on in the near future.

Contributing as a Developer
********************************

Being an opensource project, we welcome contributions in the form of source code. To do that you will have to work on an issue and open a Pull Request for it.

In order for your Pull Request to be considered it will need to pass the automated CI tests and you will also need to sign the CLA (Contributor's license agreement).

Committing Rules
=====================

For an exhaustive guide read `this <http://chris.beams.io/posts/git-commit/>`_ guide. It's all really good advice. Some rules that you should always follow though are:

1. Commits should be just to the point, not too long and not too short.
2. Commit title not exceed 50 characters.
3. Give a description of what the commit does in a short title. If more information is needed then add a blank line and afterward elaborate with as much information as needed.
4. Commits should do one thing, if two commits both do the same thing, that's a good sign they should be combined.
5. **Never** merge master on the branch, always rebase on master. To delete/amend/edit/combine commits follow `this tutorial <https://robots.thoughtbot.com/git-interactive-rebase-squash-amend-rewriting-history>`_.

Manual Testing
***********************

In order to make sure that the final executable works as a complete package (including the UI) a bit of manual testing with the final binaries is required.

This should eventually be reduced when we manage to have a more complete E2E test suite. Everything below that can be E2E tested should be.

If time allows test the below on the binaries for all OSes. If not just on one.

Startup
=========

New User
----------

- Create a new user and see that it works. Both with and without a premium key. With a premium key make sure that you can verify that pulling data from the server works.

- Provide mismatching passwords and see it's handled properly.

- Provide wrong premium keys and see it's handled properly

Sign in existing user
----------------------

- Sign in an existing user with a wrong password and see it's handled.

- Sign in a non-existing user and see it's handled

- Sing in an existing user and see it works

External Trades
================

- Add an external trade and see it's added in the table
- Edit an external trade from the table and see it's altered
- Delete an external trade from the table and see it's removed
- Expand the details on a trade and see they are shown properly

Data Importing
===============

- Import some data from cointracking.info and see that works properly

Exchanges
===========

- Add an invalid exchange API key and see it's handled properly
- Add a valid exchange API key and see it works. See that dashboard balances are also updated.
- Remove an exchange and see that it works and that the dasboard balances are updated.

External Services
==================

- Add an API key for all external services
- Remove an API key for all external services

Application and Accounting Settings
====================================

- Change all application settings one by one and see the changes are reflected.
- Same as above but for invalid values (if possible) and see they are handled.
- Change the profit currency and see it works
- Change all accounting settings one by one and see the changes are reflected.
- Same as above but for invalid values (if possible) and see they are handled.

Accounts and Balances
========================

Fiat
-----

- Add a fiat balance and see it works
- Remove a fiat balance and see it works
- See that adding non number or negative is handled

Ethereum Accounts
-------------------

- Add an ethereum account and see it works
- Add an invalid ethereum account and see it is handled properly
- Remove an ethereum account and see it works

Ethereum Tokens
-------------------

- Track an ethereum token and see it works
- Remove an ethereum token and see it works

Bitcoin accounts
----------------
  
- Add a bitcoin account and see it works
- Add an invalid bitcoin account and see it is handled properly
- Remove a bitcoin account and see it works

Tax Report
===========

- Check that invalid input in the date range are handled properly
- Create a big tax report over many exchanges for a long period of time and see that it's correct and no unexpected problems occur.
- Create a CSV export of the report and see it works

Premium Analytics
===================

- Check they work for a premium account
- Modify the range of the netvalue graph and see it works properly
- Change the asset and modify the range of the graph of amount and value of an asset and see it works properly
- Check the netvalue distribution by location works properly
- Check the netvalue distribution by asset works properly and that you can modify the number of assets shown in the graph


