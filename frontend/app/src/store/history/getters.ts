import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/types';
import { HistoryState } from './types';

export const getters: GetterTree<HistoryState, RotkehlchenState> = {
  associatedLocations: ({ associatedLocations }) => {
    return associatedLocations;
  },
  assetMovements: ({ assetMovements }) => {
    return assetMovements.data;
  },
  assetMovementsFound: ({ assetMovements }) => {
    return assetMovements.found;
  },
  assetMovementsLimit: ({ assetMovements }) => {
    return assetMovements.limit;
  },
  assetMovementsTotal: ({ assetMovements }) => {
    return assetMovements.total;
  },
  ledgerActions: ({ ledgerActions }) => {
    return ledgerActions.data;
  },
  ledgerActionsFound: ({ ledgerActions }) => {
    return ledgerActions.found;
  },
  ledgerActionsLimit: ({ ledgerActions }) => {
    return ledgerActions.limit;
  },
  ledgerActionsTotal: ({ ledgerActions }) => {
    return ledgerActions.total;
  },
  trades: ({ trades }) => {
    return trades.data;
  },
  tradesFound: ({ trades }) => {
    return trades.found;
  },
  tradesLimit: ({ trades }) => {
    return trades.limit;
  },
  tradesTotal: ({ trades }) => {
    return trades.total;
  },
  transactions: ({ transactions }) => {
    return transactions.data;
  },
  transactionsTotal: ({ transactions }) => {
    return transactions.total;
  },
  transactionsFound: ({ transactions }) => {
    return transactions.found;
  },
  transactionsLimit: ({ transactions }) => {
    return transactions.limit;
  }
};
