import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremium } from '@/composables/premium';
import { useItemsPerPage } from '@/composables/session/use-items-per-page';
import { useEth2Staking } from '@/composables/staking/eth2/eth2';

describe('composables::staking/eth2/eth2', () => {
  setActivePinia(createPinia());

  beforeEach(() => {
    const premium = usePremium();
    set(premium, true);
    vi.clearAllMocks();
  });

  describe('fetchPerformance', () => {
    it('should fetch limited validators based on static limit and ignore global limit', async () => {
      const { fetchPerformance, performance, pagination } = useEth2Staking();
      await fetchPerformance({ limit: 10, offset: 0 });

      expect(get(performance).validators).toHaveLength(10);
      expect(get(performance).entriesTotal).toBe(11);

      const itemsPerPage = useItemsPerPage();

      set(itemsPerPage, 25);
      set(pagination, { ...get(pagination), offset: 10 });

      await flushPromises();
      await nextTick();

      expect(get(pagination).limit).toBe(10);

      set(itemsPerPage, 50);

      expect(get(pagination).limit).toBe(10);
    });
  });
});
