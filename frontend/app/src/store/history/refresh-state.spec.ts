import type { Exchange } from '@/types/exchanges';
import type { ChainAddress } from '@/types/history/events';
import { beforeEach, describe, expect, it } from 'vitest';
import { useHistoryRefreshStateStore } from './refresh-state';

describe('useHistoryRefreshStateStore', () => {
  let store: ReturnType<typeof useHistoryRefreshStateStore>;

  const mockAccounts: ChainAddress[] = [
    { address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', chain: 'eth' },
    { address: '0x71C7656EC7ab88b098defB751B7401B5f6d8976F', chain: 'eth' },
    { address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc' },
  ];

  const mockExchanges: Exchange[] = [
    { location: 'kraken', name: 'Kraken1' },
    { location: 'binance', name: 'Binance1' },
  ];

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useHistoryRefreshStateStore();
  });

  describe('initialization', () => {
    it('should initialize with default values', () => {
      expect(get(store.isRefreshing)).toBe(false);
      expect(get(store.lastRefreshTime)).toBeNull();
      expect(get(store.accountsAtLastRefresh).size).toBe(0);
      expect(get(store.exchangesAtLastRefresh).size).toBe(0);
      expect(get(store.pendingAccounts).size).toBe(0);
      expect(get(store.pendingExchanges).size).toBe(0);
      expect(get(store.accountsBeingRefreshed).size).toBe(0);
      expect(get(store.exchangesBeingRefreshed).size).toBe(0);
    });
  });

  describe('startRefresh', () => {
    it('should start refresh with accounts only', () => {
      store.startRefresh(mockAccounts);

      expect(get(store.isRefreshing)).toBe(true);
      expect(get(store.lastRefreshTime)).not.toBeNull();
      expect(get(store.accountsAtLastRefresh).size).toBe(3);
      expect(get(store.exchangesAtLastRefresh).size).toBe(0);
      expect(get(store.accountsBeingRefreshed).size).toBe(3);
      expect(get(store.exchangesBeingRefreshed).size).toBe(0);
      expect(get(store.pendingAccounts).size).toBe(0);
      expect(get(store.pendingExchanges).size).toBe(0);
    });

    it('should start refresh with both accounts and exchanges', () => {
      store.startRefresh(mockAccounts, mockExchanges);

      expect(get(store.isRefreshing)).toBe(true);
      expect(get(store.accountsAtLastRefresh).size).toBe(3);
      expect(get(store.exchangesAtLastRefresh).size).toBe(2);
      expect(get(store.accountsBeingRefreshed).size).toBe(3);
      expect(get(store.exchangesBeingRefreshed).size).toBe(2);
    });

    it('should merge with existing accounts and exchanges on subsequent refreshes', () => {
      store.startRefresh([mockAccounts[0]], [mockExchanges[0]]);
      expect(get(store.accountsAtLastRefresh).size).toBe(1);
      expect(get(store.exchangesAtLastRefresh).size).toBe(1);

      store.startRefresh([mockAccounts[1]], [mockExchanges[1]]);
      expect(get(store.accountsAtLastRefresh).size).toBe(2);
      expect(get(store.exchangesAtLastRefresh).size).toBe(2);
    });

    it('should clear pending accounts and exchanges on refresh', () => {
      store.startRefresh([mockAccounts[0]]);
      store.addPendingAccounts([mockAccounts[1]]);
      store.addPendingExchanges([mockExchanges[0]]);

      expect(get(store.pendingAccounts).size).toBe(1);
      expect(get(store.pendingExchanges).size).toBe(1);

      store.finishRefresh();
      store.startRefresh([mockAccounts[1]], [mockExchanges[0]]);

      expect(get(store.pendingAccounts).size).toBe(0);
      expect(get(store.pendingExchanges).size).toBe(0);
    });
  });

  describe('finishRefresh', () => {
    it('should finish refresh and clear being refreshed state', () => {
      store.startRefresh(mockAccounts, mockExchanges);
      expect(get(store.isRefreshing)).toBe(true);
      expect(get(store.accountsBeingRefreshed).size).toBe(3);
      expect(get(store.exchangesBeingRefreshed).size).toBe(2);

      store.finishRefresh();

      expect(get(store.isRefreshing)).toBe(false);
      expect(get(store.accountsBeingRefreshed).size).toBe(0);
      expect(get(store.exchangesBeingRefreshed).size).toBe(0);
      expect(get(store.accountsAtLastRefresh).size).toBe(3);
      expect(get(store.exchangesAtLastRefresh).size).toBe(2);
    });

    it('should preserve pending accounts and exchanges after finish', () => {
      store.startRefresh([mockAccounts[0]]);
      store.addPendingAccounts([mockAccounts[1]]);
      store.addPendingExchanges([mockExchanges[0]]);

      store.finishRefresh();

      expect(get(store.pendingAccounts).size).toBe(1);
      expect(get(store.pendingExchanges).size).toBe(1);
    });
  });

  describe('addPendingAccounts', () => {
    it('should add new accounts to pending', () => {
      store.startRefresh([mockAccounts[0]]);

      store.addPendingAccounts([mockAccounts[1], mockAccounts[2]]);

      expect(get(store.pendingAccounts).size).toBe(2);
    });

    it('should not add accounts that were already refreshed', () => {
      store.startRefresh([mockAccounts[0], mockAccounts[1]]);

      store.addPendingAccounts([mockAccounts[0], mockAccounts[2]]);

      expect(get(store.pendingAccounts).size).toBe(1);
    });

    it('should not add accounts that are currently being refreshed', () => {
      store.startRefresh([mockAccounts[0]]);

      store.addPendingAccounts([mockAccounts[0], mockAccounts[1]]);

      expect(get(store.pendingAccounts).size).toBe(1);
    });
  });

  describe('addPendingExchanges', () => {
    it('should add new exchanges to pending', () => {
      store.startRefresh([], [mockExchanges[0]]);

      store.addPendingExchanges([mockExchanges[1]]);

      expect(get(store.pendingExchanges).size).toBe(1);
    });

    it('should not add exchanges that were already refreshed', () => {
      store.startRefresh([], mockExchanges);

      store.addPendingExchanges([mockExchanges[0]]);

      expect(get(store.pendingExchanges).size).toBe(0);
    });

    it('should not add exchanges that are currently being refreshed', () => {
      store.startRefresh([], [mockExchanges[0]]);

      store.addPendingExchanges([mockExchanges[0], mockExchanges[1]]);

      expect(get(store.pendingExchanges).size).toBe(1);
    });
  });

  describe('getNewAccounts', () => {
    it('should return all accounts when none have been refreshed', () => {
      const newAccounts = store.getNewAccounts(mockAccounts);

      expect(newAccounts).toHaveLength(3);
    });

    it('should return only new accounts', () => {
      store.startRefresh([mockAccounts[0], mockAccounts[1]]);
      store.finishRefresh();

      const newAccounts = store.getNewAccounts(mockAccounts);

      expect(newAccounts).toHaveLength(1);
      expect(newAccounts[0]).toEqual(mockAccounts[2]);
    });

    it('should exclude accounts currently being refreshed', () => {
      store.startRefresh([mockAccounts[0]]);

      const newAccounts = store.getNewAccounts(mockAccounts);

      expect(newAccounts).toHaveLength(2);
      expect(newAccounts).not.toContainEqual(mockAccounts[0]);
    });
  });

  describe('getNewExchanges', () => {
    it('should return all exchanges when none have been refreshed', () => {
      const newExchanges = store.getNewExchanges(mockExchanges);

      expect(newExchanges).toHaveLength(2);
    });

    it('should return only new exchanges', () => {
      store.startRefresh([], [mockExchanges[0]]);
      store.finishRefresh();

      const newExchanges = store.getNewExchanges(mockExchanges);

      expect(newExchanges).toHaveLength(1);
      expect(newExchanges[0]).toEqual(mockExchanges[1]);
    });

    it('should exclude exchanges currently being refreshed', () => {
      store.startRefresh([], [mockExchanges[0]]);

      const newExchanges = store.getNewExchanges(mockExchanges);

      expect(newExchanges).toHaveLength(1);
      expect(newExchanges).not.toContainEqual(mockExchanges[0]);
    });
  });

  describe('getPendingAccountsForRefresh', () => {
    it('should return empty array when no pending accounts', () => {
      const pending = store.getPendingAccountsForRefresh();

      expect(pending).toHaveLength(0);
    });

    it('should return pending accounts', () => {
      store.startRefresh([mockAccounts[0]]);
      store.addPendingAccounts([mockAccounts[1], mockAccounts[2]]);

      const pending = store.getPendingAccountsForRefresh();

      expect(pending).toHaveLength(2);
      expect(pending).toContainEqual(mockAccounts[1]);
      expect(pending).toContainEqual(mockAccounts[2]);
    });

    it('should filter out accounts currently being refreshed', () => {
      store.startRefresh([mockAccounts[0]]);
      store.addPendingAccounts([mockAccounts[1]]);

      // Start another refresh with the pending account
      store.startRefresh([mockAccounts[1]]);

      const pending = store.getPendingAccountsForRefresh();

      expect(pending).toHaveLength(0);
    });
  });

  describe('getPendingExchangesForRefresh', () => {
    it('should return empty array when no pending exchanges', () => {
      const pending = store.getPendingExchangesForRefresh();

      expect(pending).toHaveLength(0);
    });

    it('should return pending exchanges', () => {
      store.startRefresh([], [mockExchanges[0]]);
      store.addPendingExchanges([mockExchanges[1]]);

      const pending = store.getPendingExchangesForRefresh();

      expect(pending).toHaveLength(1);
      expect(pending).toContainEqual(mockExchanges[1]);
    });

    it('should filter out exchanges currently being refreshed', () => {
      store.startRefresh([], [mockExchanges[0]]);
      store.addPendingExchanges([mockExchanges[1]]);

      // Start another refresh with the pending exchange
      store.startRefresh([], [mockExchanges[1]]);

      const pending = store.getPendingExchangesForRefresh();

      expect(pending).toHaveLength(0);
    });
  });

  describe('hasPendingAccounts', () => {
    it('should return false when no pending accounts', () => {
      expect(get(store.hasPendingAccounts)).toBe(false);
    });

    it('should return true when there are pending accounts', () => {
      store.startRefresh([mockAccounts[0]]);
      store.addPendingAccounts([mockAccounts[1]]);

      expect(get(store.hasPendingAccounts)).toBe(true);
    });
  });

  describe('hasPendingExchanges', () => {
    it('should return false when no pending exchanges', () => {
      expect(get(store.hasPendingExchanges)).toBe(false);
    });

    it('should return true when there are pending exchanges', () => {
      store.startRefresh([], [mockExchanges[0]]);
      store.addPendingExchanges([mockExchanges[1]]);

      expect(get(store.hasPendingExchanges)).toBe(true);
    });
  });

  describe('shouldRefreshAll', () => {
    it('should return true when never refreshed', () => {
      const shouldRefresh = store.shouldRefreshAll(mockAccounts, mockExchanges);

      expect(shouldRefresh).toBe(true);
    });

    it('should return false when already refreshing', () => {
      store.startRefresh(mockAccounts, mockExchanges);

      const shouldRefresh = store.shouldRefreshAll(mockAccounts, mockExchanges);

      expect(shouldRefresh).toBe(false);
    });

    it('should return true when there are new accounts', () => {
      store.startRefresh([mockAccounts[0]]);
      store.finishRefresh();

      const shouldRefresh = store.shouldRefreshAll(mockAccounts, []);

      expect(shouldRefresh).toBe(true);
    });

    it('should return true when there are new exchanges', () => {
      store.startRefresh([], [mockExchanges[0]]);
      store.finishRefresh();

      const shouldRefresh = store.shouldRefreshAll([], mockExchanges);

      expect(shouldRefresh).toBe(true);
    });

    it('should return false when no new accounts or exchanges', () => {
      store.startRefresh(mockAccounts, mockExchanges);
      store.finishRefresh();

      const shouldRefresh = store.shouldRefreshAll(mockAccounts, mockExchanges);

      expect(shouldRefresh).toBe(false);
    });
  });

  describe('reset', () => {
    it('should reset all state to initial values', () => {
      store.startRefresh(mockAccounts, mockExchanges);
      store.addPendingAccounts([mockAccounts[0]]);
      store.addPendingExchanges([mockExchanges[0]]);

      store.reset();

      expect(get(store.isRefreshing)).toBe(false);
      expect(get(store.lastRefreshTime)).toBeNull();
      expect(get(store.accountsAtLastRefresh).size).toBe(0);
      expect(get(store.exchangesAtLastRefresh).size).toBe(0);
      expect(get(store.pendingAccounts).size).toBe(0);
      expect(get(store.pendingExchanges).size).toBe(0);
      expect(get(store.accountsBeingRefreshed).size).toBe(0);
      expect(get(store.exchangesBeingRefreshed).size).toBe(0);
    });
  });

  describe('exchange key generation', () => {
    it('should create unique keys based on location and name only', () => {
      const exchange1: Exchange = { krakenAccountType: 'pro', location: 'kraken', name: 'Kraken1' };
      const exchange2: Exchange = { krakenAccountType: 'starter', location: 'kraken', name: 'Kraken1' };

      store.startRefresh([], [exchange1]);
      store.finishRefresh();

      const newExchanges = store.getNewExchanges([exchange2]);

      // Should treat them as the same exchange since location:name is the same
      expect(newExchanges).toHaveLength(0);
    });

    it('should differentiate exchanges with different names', () => {
      const exchange1: Exchange = { location: 'kraken', name: 'Kraken1' };
      const exchange2: Exchange = { location: 'kraken', name: 'Kraken2' };

      store.startRefresh([], [exchange1]);
      store.finishRefresh();

      const newExchanges = store.getNewExchanges([exchange2]);

      expect(newExchanges).toHaveLength(1);
      expect(newExchanges[0]).toEqual(exchange2);
    });
  });

  describe('special characters in keys', () => {
    it('should handle exchange names with colons', () => {
      const exchange: Exchange = { location: 'kraken', name: 'My Kraken: Trading' };

      store.startRefresh([], [exchange]);
      store.addPendingExchanges([{ location: 'binance', name: 'Main: Account' }]);
      store.finishRefresh();

      const pending = store.getPendingExchangesForRefresh();

      expect(pending).toHaveLength(1);
      expect(pending[0]).toEqual({ location: 'binance', name: 'Main: Account' });
    });

    it('should handle exchange names with multiple colons', () => {
      const exchange: Exchange = { location: 'kraken', name: 'Account: Trading: Main' };

      store.startRefresh([], [exchange]);
      store.finishRefresh();

      const newExchanges = store.getNewExchanges([exchange]);

      // Should recognize it as already refreshed
      expect(newExchanges).toHaveLength(0);
    });

    it('should handle addresses with colons in IPv6 format', () => {
      const accountWithColon: ChainAddress = {
        address: '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
        chain: 'test',
      };

      store.startRefresh([accountWithColon]);
      store.addPendingAccounts([{ address: 'fe80::1', chain: 'test' }]);
      store.finishRefresh();

      const pending = store.getPendingAccountsForRefresh();

      expect(pending).toHaveLength(1);
      expect(pending[0]).toEqual({ address: 'fe80::1', chain: 'test' });
    });

    it('should reconstruct exchange names with colons correctly when getting pending', () => {
      const exchangeWithColons: Exchange = { location: 'kraken', name: 'Acc:1:Main' };

      store.startRefresh([], []);
      store.addPendingExchanges([exchangeWithColons]);

      const pending = store.getPendingExchangesForRefresh();

      expect(pending).toHaveLength(1);
      expect(pending[0].location).toBe('kraken');
      expect(pending[0].name).toBe('Acc:1:Main');
    });

    it('should handle account addresses with multiple colons correctly', () => {
      const accountWithMultipleColons: ChainAddress = {
        address: 'addr:with:multiple:colons',
        chain: 'test',
      };

      store.startRefresh([]);
      store.addPendingAccounts([accountWithMultipleColons]);

      const pending = store.getPendingAccountsForRefresh();

      expect(pending).toHaveLength(1);
      expect(pending[0].chain).toBe('test');
      expect(pending[0].address).toBe('addr:with:multiple:colons');
    });
  });
});
