import i18n from '@/i18n';

export enum HistoryActions {
  FETCH_TRADES = 'fetchTrades',
  ADD_EXTERNAL_TRADE = 'addExternalTrade',
  FETCH_LEDGER_ACTIONS = 'fetchLedgerActions',
  ADD_LEDGER_ACTION = 'addLedgerAction',
  EDIT_LEDGER_ACTION = 'editLedgerAction',
  DELETE_LEDGER_ACTION = 'deleteLedgerAction',
  PURGE_TRANSACTIONS = 'purgeTransactions',
  PURGE_EXCHANGE = 'purgeExchange',
  REMOVE_EXCHANGE_TRADES = 'removeExchangeTrades',
  REMOVE_EXCHANGE_MOVEMENTS = 'removeExchangeMovements',
  FETCH_TRANSACTIONS = 'fetchTransactions',
  FETCH_MOVEMENTS = 'fetchMovements',
  EDIT_EXTERNAL_TRADE = 'editExternalTrade',
  DELETE_EXTERNAL_TRADE = 'deleteExternalTrade',
  IGNORE_ACTIONS = 'ignoreActions',
  UNIGNORE_ACTION = 'unignoreActions'
}

export enum HistoryMutations {
  ADD_LEDGER_ACTION = 'addLedgerAction',
  SET_LEDGER_ACTIONS = 'setLedgerActions',
  RESET = 'reset',
  SET_TRANSACTIONS = 'setTransactions',
  SET_MOVEMENTS = 'setMovements',
  DELETE_TRADE = 'deleteTrade',
  UPDATE_TRADE = 'updateTrade',
  ADD_TRADE = 'addTrade',
  SET_TRADES = 'setTrades'
}

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
