import { HistoricData, HistoryState } from '@/store/history/types';

export const defaultHistoricState = <T>(): HistoricData<T> => ({
  found: 0,
  limit: 0,
  data: []
});

export const defaultState = (): HistoryState => ({
  trades: defaultHistoricState(),
  assetMovements: defaultHistoricState(),
  transactions: defaultHistoricState(),
  ledgerActions: defaultHistoricState()
});

export const state: HistoryState = defaultState();
