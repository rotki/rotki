beforeAll(() => {
  vi.mock('@/services/assets/info', () => ({
    useAssetInfoApi: vi.fn().mockReturnValue({
      assetMapping: vi.fn().mockResolvedValue({})
    })
  }));

  vi.mock('@/services/balances/price', () => ({
    usePriceApi: vi.fn().mockReturnValue({
      getPriceCache: vi.fn().mockReturnValue([])
    })
  }));

  vi.mock('vue', async () => {
    const mod = await vi.importActual<typeof import('vue')>('vue');
    mod.default.config.devtools = false;
    mod.default.config.productionTip = false;
    return {
      ...mod,
      useListeners: vi.fn(),
      useAttrs: vi.fn()
    };
  });
});
