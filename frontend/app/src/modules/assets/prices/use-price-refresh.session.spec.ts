import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope } from 'vue';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import '@test/i18n';

const { fetchExchangeRates, fetchPrices } = vi.hoisted(() => ({
  fetchExchangeRates: vi.fn(),
  fetchPrices: vi.fn(),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): { fetchExchangeRates: typeof fetchExchangeRates; fetchPrices: typeof fetchPrices } => ({
    fetchExchangeRates,
    fetchPrices,
  }),
}));

describe('usePriceRefresh across a session end', () => {
  let scope: EffectScope;
  let priceRefresh: ReturnType<typeof usePriceRefresh>;
  let endSession: () => void;

  beforeEach(() => {
    setActivePinia(createPinia());
    fetchExchangeRates.mockReset().mockResolvedValue(undefined);
    fetchPrices.mockReset().mockResolvedValue(undefined);

    scope = effectScope();
    scope.run(() => {
      priceRefresh = usePriceRefresh();
      endSession = useNativeTask().reset;
    });
  });

  afterEach(() => {
    scope.stop();
  });

  it('should drop a refresh queued in a session that has since ended', async () => {
    const { refreshPrices } = priceRefresh;
    let release: () => void = () => {};
    fetchPrices.mockImplementationOnce(async () => new Promise<void>((resolve) => {
      release = resolve;
    }));

    const running = refreshPrices(false, ['BTC']);
    const queued = refreshPrices(false, ['ETH']);
    await flushPromises();

    endSession();
    release();

    await expect(Promise.all([running, queued])).resolves.toBeDefined();
    expect(fetchPrices).toHaveBeenCalledOnce();
    expect(fetchPrices.mock.calls[0][0].selectedAssets).toEqual(['BTC']);
  });

  it('should not fetch prices when the session ended during the exchange rate fetch', async () => {
    const { refreshPrices } = priceRefresh;
    fetchExchangeRates.mockImplementationOnce(async () => {
      endSession();
    });

    await refreshPrices(true, ['BTC']);

    expect(fetchExchangeRates).toHaveBeenCalledOnce();
    expect(fetchPrices).not.toHaveBeenCalled();
  });

  it('should run a refresh queued after the session ended', async () => {
    const { refreshPrices } = priceRefresh;
    endSession();

    await refreshPrices(false, ['BTC']);

    expect(fetchPrices).toHaveBeenCalledOnce();
  });
});
