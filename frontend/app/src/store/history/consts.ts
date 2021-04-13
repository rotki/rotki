import i18n from '@/i18n';

export const ACTION_FETCH_LEDGER_ACTIONS = 'fetchLedgerActions' as const;
export const ACTION_ADD_LEDGER_ACTION = 'addLedgerAction' as const;
export const ACTION_EDIT_LEDGER_ACTION = 'editLedgerAction' as const;
export const ACTION_DELETE_LEDGER_ACTION = 'deleteLedgerAction' as const;
export const ACTION_PURGE_TRANSACTIONS = 'purgeTransactions' as const;
export const ACTION_PURGE_EXCHANGE = 'purgeExchange' as const;
export const ACTION_REMOVE_EXCHANGE_TRADES = 'removeExchangeTrades' as const;
export const ACTION_REMOVE_EXCHANGE_MOVEMENTS = 'removeExchangeMovements' as const;

export const MUTATION_ADD_LEDGER_ACTION = 'addLedgerAction' as const;
export const MUTATION_SET_LEDGER_ACTIONS = 'setLedgerActions' as const;

export const ACTION_INCOME = 'income';
export const ACTION_LOSS = 'loss';
export const ACTION_DONATION = 'donation received';
export const ACTION_EXPENSE = 'expense';
export const ACTION_DIVIDENDS = 'dividends income';
export const ACTION_AIRDROP = 'airdrop';
export const ACTION_GIFT = 'gift';
export const ACTION_GRANT = 'grant';

export const LEDGER_ACTION_TYPES = [
  ACTION_INCOME,
  ACTION_LOSS,
  ACTION_DONATION,
  ACTION_EXPENSE,
  ACTION_DIVIDENDS,
  ACTION_AIRDROP,
  ACTION_GIFT,
  ACTION_GRANT
] as const;

type ActionDataEntry = { readonly identifier: string; readonly label: string };

export const ledgerActionsData: ActionDataEntry[] = [
  {
    identifier: ACTION_INCOME,
    label: i18n.t('ledger_actions.actions.income').toString()
  },
  {
    identifier: ACTION_LOSS,
    label: i18n.t('ledger_actions.actions.loss').toString()
  },
  {
    identifier: ACTION_DONATION,
    label: i18n.t('ledger_actions.actions.donation').toString()
  },
  {
    identifier: ACTION_EXPENSE,
    label: i18n.t('ledger_actions.actions.expense').toString()
  },
  {
    identifier: ACTION_DIVIDENDS,
    label: i18n.t('ledger_actions.actions.dividends').toString()
  },
  {
    identifier: ACTION_AIRDROP,
    label: i18n.t('ledger_actions.actions.airdrop').toString()
  },
  {
    identifier: ACTION_GIFT,
    label: i18n.t('ledger_actions.actions.gift').toString()
  },
  {
    identifier: ACTION_GRANT,
    label: i18n.t('ledger_actions.actions.grant').toString()
  }
];

export const IGNORE_TRANSACTIONS = 'ethereum transaction';
export const IGNORE_MOVEMENTS = 'asset movement';
export const IGNORE_TRADES = 'trade';
export const IGNORE_LEDGER_ACTION = 'ledger action';

export const IGNORE_ACTION_TYPE = [
  IGNORE_TRANSACTIONS,
  IGNORE_MOVEMENTS,
  IGNORE_TRADES,
  IGNORE_LEDGER_ACTION
] as const;

export const FETCH_FROM_CACHE = 'fromCache' as const;
export const FETCH_FROM_SOURCE = 'fromSource' as const;
export const FETCH_REFRESH = 'refresh' as const;

export const FETCH_SOURCE = [
  FETCH_FROM_CACHE,
  FETCH_FROM_SOURCE,
  FETCH_REFRESH
] as const;
