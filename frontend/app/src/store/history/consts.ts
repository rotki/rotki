import i18n from '@/i18n';
import { LedgerActionType } from '@/types/ledger-actions';

export enum HistoryActions {
  FETCH_ASSOCIATED_LOCATIONS = 'fetchAssociatedLocations',
  FETCH_TRADES = 'fetchTrades',
  ADD_EXTERNAL_TRADE = 'addExternalTrade',
  FETCH_LEDGER_ACTIONS = 'fetchLedgerActions',
  ADD_LEDGER_ACTION = 'addLedgerAction',
  EDIT_LEDGER_ACTION = 'editLedgerAction',
  DELETE_LEDGER_ACTION = 'deleteLedgerAction',
  PURGE_EXCHANGE = 'purgeExchange',
  REMOVE_EXCHANGE_TRADES = 'removeExchangeTrades',
  REMOVE_EXCHANGE_MOVEMENTS = 'removeExchangeMovements',
  FETCH_TRANSACTIONS = 'fetchTransactions',
  FETCH_MOVEMENTS = 'fetchMovements',
  EDIT_EXTERNAL_TRADE = 'editExternalTrade',
  DELETE_EXTERNAL_TRADE = 'deleteExternalTrade',
  IGNORE_ACTIONS = 'ignoreActions',
  UNIGNORE_ACTION = 'unignoreActions',
  FETCH_IGNORED = 'fetchIgnored',
  FETCH_GITCOIN_GRANT = 'fetchGitcoinGrant'
}

export enum HistoryMutations {
  SET_ASSOCIATED_LOCATIONS = 'setAssociatedLocations',
  ADD_LEDGER_ACTION = 'addLedgerAction',
  SET_LEDGER_ACTIONS = 'setLedgerActions',
  RESET = 'reset',
  SET_TRANSACTIONS = 'setTransactions',
  SET_MOVEMENTS = 'setMovements',
  SET_TRADES = 'setTrades',
  SET_IGNORED = 'setIgnored'
}

type ActionDataEntry = { readonly identifier: string; readonly label: string };

export const ledgerActionsData: ActionDataEntry[] = [
  {
    identifier: LedgerActionType.ACTION_INCOME,
    label: i18n.t('ledger_actions.actions.income').toString()
  },
  {
    identifier: LedgerActionType.ACTION_LOSS,
    label: i18n.t('ledger_actions.actions.loss').toString()
  },
  {
    identifier: LedgerActionType.ACTION_DONATION,
    label: i18n.t('ledger_actions.actions.donation').toString()
  },
  {
    identifier: LedgerActionType.ACTION_EXPENSE,
    label: i18n.t('ledger_actions.actions.expense').toString()
  },
  {
    identifier: LedgerActionType.ACTION_DIVIDENDS,
    label: i18n.t('ledger_actions.actions.dividends').toString()
  },
  {
    identifier: LedgerActionType.ACTION_AIRDROP,
    label: i18n.t('ledger_actions.actions.airdrop').toString()
  },
  {
    identifier: LedgerActionType.ACTION_GIFT,
    label: i18n.t('ledger_actions.actions.gift').toString()
  },
  {
    identifier: LedgerActionType.ACTION_GRANT,
    label: i18n.t('ledger_actions.actions.grant').toString()
  }
];

export const FETCH_FROM_CACHE = 'fromCache' as const;
export const FETCH_FROM_SOURCE = 'fromSource' as const;
export const FETCH_REFRESH = 'refresh' as const;

export const FETCH_SOURCE = [
  FETCH_FROM_CACHE,
  FETCH_FROM_SOURCE,
  FETCH_REFRESH
] as const;
