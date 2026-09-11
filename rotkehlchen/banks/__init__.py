"""Bank connectors: local-first bank account balances and transaction history.

How this relates to the exchange integrations
---------------------------------------------
Banks are close cousins of exchanges. Reused unchanged, as implementation:

- ``ExchangeInterface`` as the connector base class: credential validation, balance
  query, history event query with range bookkeeping, credential editing, the recovering
  HTTP session. A bank is never registered as an exchange, it only shares the interface.
- ``user_credentials`` for secret storage (the location column tells banks apart).
- History events as the normalized output, with ``UNIQUE(group_identifier,
  sequence_index)`` in the DB giving idempotent re-ingestion.
- ``used_query_ranges`` bookkeeping and ``key_value_cache`` for per-connection state.
- The balance snapshot and the history refresh pipelines, which iterate banks next to
  exchanges.

Banks are their own integration at the product level: ``BankManager`` (``manager.py``)
owns the connections, the ``/banks`` endpoints add, edit, remove, list, sync and query
balances, and ``/locations/all`` marks a bank with ``is_bank`` and its ``bank_details``
manifest instead of ``exchange_details``. The exchange setup form does not list banks.

Deliberate divergences, and why:

- A **manifest** (``manifest.py``) declares tier, capabilities, auth primitives and the
  secrets schema. Exchanges are all "paste an API key"; banks are not (app approvals,
  TANs), and the UI must be able to render setup generically for banks it has never
  seen. The manifest is served under ``bank_details`` of ``/locations/all``.
- A **normalized transaction model** (``normalization.py``) between the bank payload and
  history events. Exchanges emit events directly because every exchange has its own
  event zoo. Bank transactions all look alike (an amount, a side, a counterparty, a
  reference), so one mapping serves every bank and the contract tests can check it.
- An **``updated_at`` cursor per account** instead of time-range bookkeeping. Bank
  transactions are edited and flip status after they first appear; a last-modified
  cursor with a safety window catches that, a settled-time range does not.
- An **error taxonomy** (``errors.py``): ``AuthExpired``, ``MFARequired``,
  ``RateLimited``, ``SchemaDrift``. Subclasses of ``RemoteError`` so nothing upstream
  has to change, but distinguishable so the UI can prompt for re-auth vs. wait vs. report.
- **Session persistence hooks** in the connector base, for connectors whose auth yields
  a session token. Exchanges never need this.
- **Framework-level contract tests** (``tests/banks/test_contract.py``) that run every
  connector against its committed, redacted fixtures. Exchange tests are per exchange.

Not diverged, on purpose: no separate credential table. Nothing in the data model
required one, and the location column already separates the two kinds of credentials.
"""
