import type { ProtocolCacheUpdatesData } from '@/modules/core/messaging/types';
import { beforeEach, describe, expect, it } from 'vitest';
import { useProtocolCacheStatusStore } from './use-protocol-cache-status-store';

describe('useProtocolCacheStatusStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  const createStatus = (chain: string, protocol: string, total: number, processed: number): ProtocolCacheUpdatesData => ({
    chain,
    processed,
    protocol,
    total,
  });

  describe('setProtocolCacheStatus', () => {
    it('should set status for a chain/protocol pair', () => {
      const store = useProtocolCacheStatusStore();
      store.setProtocolCacheStatus(createStatus('eth', 'uniswap', 200, 100));

      const status = get(store.protocolCacheUpdateStatus);
      expect(status['eth#uniswap']).toEqual(expect.objectContaining({
        chain: 'eth',
        processed: 100,
        protocol: 'uniswap',
        total: 200,
      }));
    });

    it('should set receivingProtocolCacheStatus to true', () => {
      const store = useProtocolCacheStatusStore();
      store.setProtocolCacheStatus(createStatus('eth', 'uniswap', 200, 100));

      expect(get(store.receivingProtocolCacheStatus)).toBe(true);
    });

    it('should mark old entries as completed when new entry arrives', () => {
      const store = useProtocolCacheStatusStore();
      store.setProtocolCacheStatus(createStatus('eth', 'uniswap', 200, 100));
      store.setProtocolCacheStatus(createStatus('optimism', 'aave', 300, 50));

      const status = get(store.protocolCacheUpdateStatus);
      // Old entry should have processed = total
      expect(status['eth#uniswap'].processed).toBe(200);
      // New entry should keep its values
      expect(status['optimism#aave'].processed).toBe(50);
    });

    it('should not update cancelled entries', () => {
      const store = useProtocolCacheStatusStore();
      store.setProtocolCacheStatus(createStatus('eth', 'uniswap', 200, 100));
      store.markAllProtocolCacheCancelled();

      store.setProtocolCacheStatus(createStatus('eth', 'uniswap', 200, 150));

      const status = get(store.protocolCacheUpdateStatus);
      expect(status['eth#uniswap'].cancelled).toBe(true);
      expect(status['eth#uniswap'].processed).toBe(100); // unchanged
    });
  });

  describe('protocolCacheStatus', () => {
    it('should filter out entries with total 0', () => {
      const store = useProtocolCacheStatusStore();
      store.setProtocolCacheStatus(createStatus('eth', 'uniswap', 200, 100));
      store.setProtocolCacheStatus(createStatus('optimism', 'aave', 0, 0));

      const filtered = get(store.protocolCacheStatus);
      // Both have been set, but the old one (eth#uniswap) was auto-completed
      // and new one (optimism#aave) has total=0, so it should be filtered out
      expect(filtered.every(s => s.total > 0)).toBe(true);
    });
  });

  describe('markAllProtocolCacheCancelled', () => {
    it('should mark all entries as cancelled', () => {
      const store = useProtocolCacheStatusStore();
      store.setProtocolCacheStatus(createStatus('eth', 'uniswap', 200, 100));
      // Setting a new status auto-completes old ones, so set another one
      // to have at least one non-completed entry
      store.markAllProtocolCacheCancelled();

      const status = get(store.protocolCacheUpdateStatus);
      for (const entry of Object.values(status)) {
        expect(entry.cancelled).toBe(true);
      }
    });
  });

  describe('resetProtocolCacheUpdatesStatus', () => {
    it('should clear all statuses and set receiving to false', () => {
      const store = useProtocolCacheStatusStore();
      store.setProtocolCacheStatus(createStatus('eth', 'uniswap', 200, 100));

      store.resetProtocolCacheUpdatesStatus();

      expect(get(store.protocolCacheUpdateStatus)).toEqual({});
      expect(get(store.receivingProtocolCacheStatus)).toBe(false);
    });
  });

  describe('setReceivingProtocolCacheStatus', () => {
    it('should set the receiving flag', () => {
      const store = useProtocolCacheStatusStore();
      store.setReceivingProtocolCacheStatus(true);
      expect(get(store.receivingProtocolCacheStatus)).toBe(true);

      store.setReceivingProtocolCacheStatus(false);
      expect(get(store.receivingProtocolCacheStatus)).toBe(false);
    });
  });
});
