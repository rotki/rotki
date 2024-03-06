import flushPromises from 'flush-promises';

describe('composables::staking/eth2/eth2', () => {
  setActivePinia(createPinia());

  beforeEach(() => {
    const { premium } = storeToRefs(usePremiumStore());
    set(premium, true);
    vi.clearAllMocks();
  });

  describe('fetchPerformance', async () => {
    it('should fetch limited validators based on static limit and ignore global limit', async () => {
      const { fetchPerformance, performance, pagination } = useEth2Staking();
      await fetchPerformance({ limit: 10, offset: 0 });

      expect(get(performance).validators).toHaveLength(10);
      expect(get(performance).entriesTotal).toBe(11);

      const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

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
