import { beforeEach, describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import { Section, Status } from '@/modules/core/common/status';
import { useStatusStore } from '@/modules/core/common/use-status-store';

describe('useBalanceStatus', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('per-chain', () => {
    it('should report initial loading when no status has been set', () => {
      const { hasCachedData, isInitialLoading, isRefreshing } = useBalanceStatus('eth');
      expect(get(hasCachedData)).toBe(false);
      expect(get(isInitialLoading)).toBe(true);
      expect(get(isRefreshing)).toBe(false);
    });

    it('should flip hasCachedData when the cache reaches LOADED', () => {
      const { setStatus } = useStatusStore();
      const { hasCachedData, isInitialLoading } = useBalanceStatus('eth');

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADING, subsection: 'eth' });
      expect(get(hasCachedData)).toBe(false);
      expect(get(isInitialLoading)).toBe(true);

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED, subsection: 'eth' });
      expect(get(hasCachedData)).toBe(true);
      expect(get(isInitialLoading)).toBe(false);
    });

    it('should track refresh independently of cache status', () => {
      const { setStatus } = useStatusStore();
      const refreshState = useBalanceRefreshState();
      const { hasCachedData, isRefreshing } = useBalanceStatus('eth');

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED, subsection: 'eth' });
      refreshState.start('eth');

      expect(get(hasCachedData)).toBe(true);
      expect(get(isRefreshing)).toBe(true);

      refreshState.stop('eth');
      expect(get(hasCachedData)).toBe(true);
      expect(get(isRefreshing)).toBe(false);
    });

    it('should react to a reactive chain argument', () => {
      const { setStatus } = useStatusStore();
      const chain = ref<string>('eth');
      const { hasCachedData } = useBalanceStatus(chain);

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED, subsection: 'eth' });
      expect(get(hasCachedData)).toBe(true);

      set(chain, 'optimism');
      expect(get(hasCachedData)).toBe(false);

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED, subsection: 'optimism' });
      expect(get(hasCachedData)).toBe(true);
    });
  });

  describe('aggregate', () => {
    it('should be false/false when no chain has been touched', () => {
      const { hasCachedData, isInitialLoading, isRefreshing } = useBalanceStatus();
      expect(get(hasCachedData)).toBe(false);
      expect(get(isInitialLoading)).toBe(false);
      expect(get(isRefreshing)).toBe(false);
    });

    it('should report hasCachedData when at least one chain is LOADED', () => {
      const { setStatus } = useStatusStore();
      const { hasCachedData } = useBalanceStatus();

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADING, subsection: 'eth' });
      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADING, subsection: 'optimism' });
      expect(get(hasCachedData)).toBe(false);

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED, subsection: 'eth' });
      expect(get(hasCachedData)).toBe(true);
    });

    it('should report isInitialLoading while any chain is still LOADING', () => {
      const { setStatus } = useStatusStore();
      const { isInitialLoading } = useBalanceStatus();

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADING, subsection: 'eth' });
      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADING, subsection: 'optimism' });
      expect(get(isInitialLoading)).toBe(true);

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED, subsection: 'eth' });
      expect(get(isInitialLoading)).toBe(true);

      setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED, subsection: 'optimism' });
      expect(get(isInitialLoading)).toBe(false);
    });

    it('should report isRefreshing when any chain has a refresh in flight', () => {
      const refreshState = useBalanceRefreshState();
      const { isRefreshing } = useBalanceStatus();

      refreshState.start('eth');
      expect(get(isRefreshing)).toBe(true);

      refreshState.start('optimism');
      refreshState.stop('eth');
      expect(get(isRefreshing)).toBe(true);

      refreshState.stop('optimism');
      expect(get(isRefreshing)).toBe(false);
    });
  });
});
