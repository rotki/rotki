import type { EvmUnDecodedTransactionsData } from '@/modules/core/messaging/types';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDecodingStatusStore } from './use-decoding-status-store';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    matchChain: (location: string): string | undefined => ({
      bitcoin: 'btc',
      btc: 'btc',
      eth: 'eth',
      ethereum: 'eth',
      optimism: 'optimism',
    })[location.toLowerCase()],
  }),
}));

describe('useDecodingStatusStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  const createStatus = (chain: string, total: number, processed: number): EvmUnDecodedTransactionsData => ({
    chain,
    processed,
    total,
  });

  describe('canonical chain keys', () => {
    it('should key an uppercase SupportedBlockchain value under the canonical chain id', () => {
      const store = useDecodingStatusStore();
      // The shape bitcoin decoding progress arrives in: `chain` is the enum value, not the id.
      store.setUndecodedTransactionsStatus(createStatus('BTC', 1, 1));

      expect(get(store.undecodedTransactionsStatus)).toEqual({
        btc: { chain: 'btc', processed: 1, total: 1 },
      });
    });

    it('should key the EVM decoder chain name under the canonical chain id', () => {
      const store = useDecodingStatusStore();
      // The EVM decoder reports ChainID.to_name(), which is not the frontend's chain id.
      store.setUndecodedTransactionsStatus(createStatus('ethereum', 100, 50));

      expect(Object.keys(get(store.undecodedTransactionsStatus))).toEqual(['eth']);
    });

    it('should collapse different spellings of one chain into a single entry', () => {
      const store = useDecodingStatusStore();
      store.setUndecodedTransactionsStatus(createStatus('ethereum', 100, 50));
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 80));

      const status = get(store.undecodedTransactionsStatus);
      expect(Object.keys(status)).toHaveLength(1);
      expect(status.eth.processed).toBe(80);
    });

    it('should cancel a decode addressed by the canonical id after progress arrived under another spelling', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('ethereum', 100, 50));

      store.markDecodingCancelled('eth');

      expect(get(store.decodingSyncProgress).eth.cancelled).toBe(true);
    });

    it('should not file an unrecognised chain under ethereum', () => {
      const store = useDecodingStatusStore();
      // `getChain` defaults to ETH for anything it cannot match, which would misattribute the row.
      store.setUndecodedTransactionsStatus(createStatus('Unknownchain', 10, 5));

      expect(Object.keys(get(store.undecodedTransactionsStatus))).toEqual(['unknownchain']);
    });

    it('should canonicalise the keys of a bulk breakdown update', () => {
      const store = useDecodingStatusStore();
      store.updateUndecodedTransactionsStatus({
        BTC: createStatus('BTC', 4, 1),
        ethereum: createStatus('ethereum', 100, 50),
      });

      const status = get(store.undecodedTransactionsStatus);
      expect(Object.keys(status).sort()).toEqual(['btc', 'eth']);
      expect(status.btc.chain).toBe('btc');
      expect(status.eth.chain).toBe('eth');
    });
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
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));

      expect(get(store.decodingSyncProgress)).toEqual({});
    });

    it('should not update sync progress for cancelled chains', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));
      store.markDecodingCancelled('eth');

      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 80));

      const syncProgress = get(store.decodingSyncProgress);
      expect(syncProgress.eth.cancelled).toBe(true);
      expect(syncProgress.eth.processed).toBe(50); // unchanged
    });
  });

  describe('resumeDecodingSyncProgress', () => {
    it('should reopen the progress gate a stopped sync closed', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.stopDecodingSyncProgress();

      store.resumeDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 50));

      expect(get(store.decodingSyncProgress).eth).toEqual({ chain: 'eth', processed: 50, total: 100 });
    });

    it('should keep the progress an earlier wave recorded', () => {
      const store = useDecodingStatusStore();
      store.resetDecodingSyncProgress();
      store.setUndecodedTransactionsStatus(createStatus('eth', 100, 100));
      store.stopDecodingSyncProgress();

      store.resumeDecodingSyncProgress();

      expect(get(store.decodingSyncProgress).eth).toEqual({ chain: 'eth', processed: 100, total: 100 });
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
