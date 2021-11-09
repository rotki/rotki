import { HistoricData, HistoryState } from '@/store/history/types';

export const defaultHistoricState = <T>(): HistoricData<T> => ({
  found: 0,
  limit: 0,
  data: []
});

export const defaultState = (): HistoryState => ({
  ignored: {},
  trades: defaultHistoricState(),
  assetMovements: defaultHistoricState(),
  transactions: {
    entries: [],
    entriesFound: 0,
    entriesLimit: 0,
    entriesTotal: 0
  },
  ledgerActions: defaultHistoricState()
});

export const state: HistoryState = defaultState();
