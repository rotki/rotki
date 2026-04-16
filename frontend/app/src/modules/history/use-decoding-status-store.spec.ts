import type { EvmUnDecodedTransactionsData } from '@/modules/core/messaging/types';
import { beforeEach, describe, expect, it } from 'vitest';
import { useDecodingStatusStore } from './use-decoding-status-store';

describe('useDecodingStatusStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  const createStatus = (chain: string, total: number, processed: number): EvmUnDecodedTransactionsData => ({
    chain,
    processed,
    total,
  });

  describe('setUndecodedTransactionsStatus', () => {
    it('should set status for a chain', () => {
      const store = useDecodingStatusStore();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));

      expect(get(store.undecodedTransactionsStatus)).toEqual({
        eth: { chain: 'eth', processed: 50, total: 100 },
      });
    });

    it('should merge with existing statuses', () => {
      const store = useDecodingStatusStore();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.setUndecodedTransactionsStatus(createStatus('optimism', 200, 100));

      const status = get(store.undecodedTransactionsStatus);
      expect(Object.keys(status)).toHaveLength(2);
      expect(status.eth.total).toBe(100);
      expect(status.optimism.total).toBe(200);
    });

    it('should update sync progress when syncing', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress(); // sets decodingSyncing = true
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));

      const syncProgress = get(store.decodingSyncProgress);
      expect(syncProgress.eth).toEqual({ chain: 'eth', processed: 50, total: 100 });
    });

    it('should not update sync progress when not syncing', () => {
      const store = useDecodingStatusStore();
      // decodingSyncing defaults to false
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));

      expect(get(store.decodingSyncProgress)).toEqual({});
    });

    it('should not update sync progress for cancelled chains', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.markDecodingCancelled('eth');

      // Try to update the cancelled chain
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 80));

      const syncProgress = get(store.decodingSyncProgress);
      expect(syncProgress.eth.cancelled).toBe(true);
      expect(syncProgress.eth.processed).toBe(50); // unchanged
    });
  });

  describe('updateUndecodedTransactionsStatus', () => {
    it('should batch update multiple chain statuses', () => {
      const store = useDecodingStatusStore();
      store.updateUndecodedTransactionsStatus({
        eth: createStatus('eth', 100, 50),
        optimism: createStatus('optimism', 200, 100),
      });

      const status = get(store.undecodedTransactionsStatus);
      expect(Object.keys(status)).toHaveLength(2);
    });

    it('should update sync progress for non-cancelled chains when syncing', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.markDecodingCancelled('eth');

      store.updateUndecodedTransactionsStatus({
        eth: createStatus('eth', 100, 80),
        optimism: createStatus('optimism', 200, 100),
      });

      const syncProgress = get(store.decodingSyncProgress);
      // eth should remain unchanged (cancelled)
      expect(syncProgress.eth.processed).toBe(50);
      // optimism should be updated
      expect(syncProgress.optimism.processed).toBe(100);
    });

    it('should not update sync progress when not syncing', () => {
      const store = useDecodingStatusStore();
      store.updateUndecodedTransactionsStatus({
        eth: createStatus('eth', 100, 50),
      });

      expect(get(store.decodingSyncProgress)).toEqual({});
    });

    it('should not regress processed count in sync progress', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 80));

      store.updateUndecodedTransactionsStatus({
        eth: createStatus('eth', 100, 50), // lower processed
      });

      const syncProgress = get(store.decodingSyncProgress);
      expect(syncProgress.eth.processed).toBe(80); // stays at higher value
    });
  });

  describe('decodingStatus', () => {
    it('should filter out chains with total 0', () => {
      const store = useDecodingStatusStore();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.setUndecodedTransactionsStatus(createStatus('optimism', 0, 0));

      expect(get(store.decodingStatus)).toHaveLength(1);
      expect(get(store.decodingStatus)[0].chain).toBe('eth');
    });
  });

  describe('decodingSyncStatus', () => {
    it('should filter out chains with total 0 from sync progress', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.setUndecodedTransactionsStatus(createStatus('optimism', 0, 0));

      expect(get(store.decodingSyncStatus)).toHaveLength(1);
      expect(get(store.decodingSyncStatus)[0].chain).toBe('eth');
    });
  });

  describe('markDecodingCancelled', () => {
    it('should mark a chain as cancelled', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.markDecodingCancelled('eth');

      const syncProgress = get(store.decodingSyncProgress);
      expect(syncProgress.eth.cancelled).toBe(true);
    });

    it('should not error when marking non-existent chain', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.markDecodingCancelled('nonexistent');

      expect(get(store.decodingSyncProgress)).toEqual({});
    });
  });

  describe('resetUndecodedTransactionsStatus', () => {
    it('should clear all undecoded transaction statuses', () => {
      const store = useDecodingStatusStore();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.resetUndecodedTransactionsStatus();

      expect(get(store.undecodedTransactionsStatus)).toEqual({});
    });
  });

  describe('resetDecodingSyncProgress', () => {
    it('should clear sync progress and set syncing to true', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();

      expect(get(store.decodingSyncProgress)).toEqual({});
      expect(get(store.decodingSyncing)).toBe(true);
    });
  });

  describe('stopDecodingSyncProgress', () => {
    it('should set syncing to false', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      expect(get(store.decodingSyncing)).toBe(true);

      store.stopDecodingSyncProgress();
      expect(get(store.decodingSyncing)).toBe(false);
    });
  });

  describe('getUndecodedTransactionStatus', () => {
    it('should return all statuses as array', () => {
      const store = useDecodingStatusStore();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.setUndecodedTransactionsStatus(createStatus('optimism', 200, 100));

      const result = store.getUndecodedTransactionStatus();
      expect(result).toHaveLength(2);
    });
  });
});
