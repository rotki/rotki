import {
  AssetMovementEntry,
  EthTransactionEntry,
  HistoryState,
  LedgerActionEntry,
  TradeEntry
} from '@/store/history/types';
import { Collection } from '@/types/collection';

export const defaultHistoricState = <T>(): Collection<T> => ({
  found: 0,
  limit: 0,
  data: [],
  total: 0
});

export const defaultState = (): HistoryState => ({
  ignored: {},
  associatedLocations: [],
  trades: defaultHistoricState<TradeEntry>(),
  assetMovements: defaultHistoricState<AssetMovementEntry>(),
  transactions: defaultHistoricState<EthTransactionEntry>(),
  ledgerActions: defaultHistoricState<LedgerActionEntry>()
});

export const state: HistoryState = defaultState();
