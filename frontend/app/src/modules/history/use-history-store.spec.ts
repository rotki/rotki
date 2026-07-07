import { beforeEach, describe, expect, it } from 'vitest';
import { useHistoryStore } from './use-history-store';

describe('useHistoryStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should track unprocessed modifications via version counters', () => {
    const store = useHistoryStore();
    expect(get(store.hasUnprocessedModifications)).toBe(false);

    store.signalEventsModified();
    expect(get(store.eventsVersion)).toBe(1);
    expect(get(store.hasUnprocessedModifications)).toBe(true);

    store.acknowledgeModifications();
    expect(get(store.hasUnprocessedModifications)).toBe(false);
  });

  it('should keep flagging modifications while newer signals arrive', () => {
    const store = useHistoryStore();
    store.signalEventsModified();
    store.signalEventsModified();
    store.acknowledgeModifications();
    expect(get(store.hasUnprocessedModifications)).toBe(false);

    store.signalEventsModified();
    expect(get(store.hasUnprocessedModifications)).toBe(true);
  });

  it('should store associated locations, labels and the transaction summary', () => {
    const store = useHistoryStore();
    const labels = [{ location: 'kraken', locationLabel: 'Kraken' }];
    const summary = {
      evmLastQueriedTs: 100,
      exchangesLastQueriedTs: 200,
      hasEvmAccounts: true,
      hasExchangesAccounts: false,
      undecodedTxCount: 3,
    };
    store.setAssociatedLocations(['kraken', 'binance']);
    store.setLocationLabels(labels);
    store.setTransactionStatusSummary(summary);

    expect(get(store.associatedLocations)).toEqual(['kraken', 'binance']);
    expect(get(store.locationLabels)).toEqual(labels);
    expect(get(store.transactionStatusSummary)).toEqual(summary);
  });
});
