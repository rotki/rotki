import type { FailedHistoricalAssetPriceResponse } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import MissingDailyPrices from '@/modules/statistics/MissingDailyPrices.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { addHistoricalPrice, fetchHistoricalPrices } = vi.hoisted(() => ({
  addHistoricalPrice: vi.fn(async () => Promise.resolve(true)),
  fetchHistoricalPrices: vi.fn(),
}));

let failedDailyPrices: Ref<Record<string, FailedHistoricalAssetPriceResponse>>;
let resolvedFailedDailyPrices: Ref<Record<string, number[]>>;

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): Record<string, unknown> => ({
    addHistoricalPrice,
    deleteHistoricalPrice: vi.fn(),
    editHistoricalPrice: vi.fn(),
    fetchHistoricalPrices,
  }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): Record<string, unknown> => ({
    failedDailyPrices,
    resetHistoricalPricesData: vi.fn(),
    resolvedFailedDailyPrices,
  }),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): Record<string, unknown> => ({ getHistoricPrice: vi.fn() }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): Record<string, unknown> => ({
    useAssetField: (): Ref<string> => ref('Ethereum'),
  }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<string> => ref('USD'),
}));

function failures(overrides: Partial<FailedHistoricalAssetPriceResponse> = {}): FailedHistoricalAssetPriceResponse {
  return {
    noPricesTimestamps: [],
    rateLimitedPricesTimestamps: [],
    ...overrides,
  };
}

async function createWrapper(failed: FailedHistoricalAssetPriceResponse): Promise<VueWrapper> {
  set(failedDailyPrices, { ETH: failed });
  const wrapper = mount(MissingDailyPrices, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: { DateDisplay: true },
    },
    props: { asset: 'ETH' },
  });
  await flushPromises();
  return wrapper;
}

describe('modules/statistics/MissingDailyPrices.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    failedDailyPrices = ref<Record<string, FailedHistoricalAssetPriceResponse>>({});
    resolvedFailedDailyPrices = ref<Record<string, number[]>>({});
    fetchHistoricalPrices.mockResolvedValue([]);
  });

  it('should read the saved prices when it opens', async () => {
    await createWrapper(failures({ noPricesTimestamps: [1_700_000_000] }));

    expect(fetchHistoricalPrices).toHaveBeenCalledOnce();
  });

  it('should offer one editable row per unpriced day', async () => {
    const wrapper = await createWrapper(failures({ noPricesTimestamps: [1_700_000_000, 1_700_086_400] }));

    expect(wrapper.findAll('[data-testid=missing-daily-price-input]')).toHaveLength(2);
  });

  it('should offer a rate-limited tab only when days were rate limited', async () => {
    const withoutLimit = await createWrapper(failures({ noPricesTimestamps: [1_700_000_000] }));
    expect(withoutLimit.text()).not.toContain('failed_daily_prices.rate_limited.title');

    const withLimit = await createWrapper(failures({
      noPricesTimestamps: [1_700_000_000],
      rateLimitedPricesTimestamps: [1_700_086_400],
    }));
    expect(withLimit.text()).toContain('failed_daily_prices.rate_limited.title');
  });

  it('should offer a missing-prices tab only when days had no price', async () => {
    const wrapper = await createWrapper(failures({ rateLimitedPricesTimestamps: [1_700_086_400] }));

    expect(wrapper.text()).not.toContain('failed_daily_prices.missing_prices.title');
    expect(wrapper.findAll('[data-testid=missing-daily-price-input]')).toHaveLength(0);
  });

  it('should name the asset it is reporting on', async () => {
    const wrapper = await createWrapper(failures({ noPricesTimestamps: [1_700_000_000] }));

    expect(wrapper.text()).toContain('Ethereum');
  });

  it('should ask to be closed', async () => {
    const wrapper = await createWrapper(failures({ noPricesTimestamps: [1_700_000_000] }));

    await wrapper.find('[data-testid=close-missing-daily-prices]').trigger('click');

    expect(wrapper.emitted('close')).toHaveLength(1);
  });
});
