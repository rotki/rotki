import { bigNumberify, type FailedHistoricalAssetPriceResponse } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { get, set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import MissingDailyPrices from '@/modules/statistics/MissingDailyPrices.vue';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';
import { createRuiPlugin } from '@/plugins/rui';

const { addHistoricalPrice, deleteHistoricalPrice, fetchHistoricalPrices } = vi.hoisted(() => ({
  addHistoricalPrice: vi.fn(async () => Promise.resolve(true)),
  deleteHistoricalPrice: vi.fn(async () => Promise.resolve(true)),
  fetchHistoricalPrices: vi.fn(),
}));

let failedDailyPrices: Ref<Record<string, FailedHistoricalAssetPriceResponse>>;
let resolvedFailedDailyPrices: Ref<Record<string, number[]>>;

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): Record<string, unknown> => ({
    addHistoricalPrice,
    deleteHistoricalPrice,
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
    failedPricesTimestamps: [],
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

  it('should let a day no price source could be reached for be priced by hand too, once', async () => {
    const wrapper = await createWrapper(failures({
      failedPricesTimestamps: [1_700_172_800, 1_700_000_000],
      noPricesTimestamps: [1_700_000_000],
    }));

    expect(wrapper.findAll('[data-testid=missing-daily-price-input]')).toHaveLength(2);
  });

  it('should show a day the fetcher and the backfill filed at two times once, and settle both times with one price', async () => {
    const wrapper = await createWrapper(failures({
      failedPricesTimestamps: [1_699_920_000],
      noPricesTimestamps: [1_700_000_000],
    }));
    const inputs = wrapper.findAll('[data-testid=missing-daily-price-input] input');
    expect(inputs).toHaveLength(1);

    await inputs[0].setValue('0.5');
    await inputs[0].trigger('blur');
    await flushPromises();

    expect(get(resolvedFailedDailyPrices).ETH).toEqual(expect.arrayContaining([1_700_000_000, 1_699_920_000]));
  });

  it('should unsettle a day and drop its price from the graphs once its saved price is deleted, on the days next to it too', async () => {
    fetchHistoricalPrices.mockResolvedValue([{ fromAsset: 'ETH', price: bigNumberify('0.5'), timestamp: 1_700_000_000, toAsset: 'USD' }]);
    set(resolvedFailedDailyPrices, { ETH: [1_700_000_000] });
    const series = usePriceSeriesStore();
    // the cache answers within a day, so the 23:00 snapshot of the day before may hold the deleted rate
    series.addPrices('ETH', [
      { price: bigNumberify('0.5'), time: 1_699_916_400 },
      { price: bigNumberify('0.5'), time: 1_700_000_000 },
      { price: bigNumberify('0.6'), time: 1_700_172_800 },
    ]);
    const wrapper = await createWrapper(failures({ noPricesTimestamps: [1_700_000_000] }));
    const input = wrapper.find('[data-testid=missing-daily-price-input] input');

    await input.setValue('');
    await input.trigger('blur');
    await flushPromises();

    expect(deleteHistoricalPrice).toHaveBeenCalledOnce();
    expect(get(resolvedFailedDailyPrices).ETH).toEqual([]);
    expect(series.prices.ETH?.map(({ time }) => time)).toEqual([1_700_172_800]);
  });

  it('should list the days oldest first, whichever list and order they were filed in', async () => {
    const wrapper = await createWrapper(failures({
      failedPricesTimestamps: [1_700_172_800, 1_699_920_000],
      noPricesTimestamps: [1_700_259_200, 1_700_086_400],
    }));

    const shown = wrapper.findAllComponents({ name: 'DateDisplay' }).map(date => date.props('timestamp'));
    expect(shown).toEqual([1_699_920_000, 1_700_086_400, 1_700_172_800, 1_700_259_200]);
  });

  it('should hand out a new list of resolved days on every saved price, so watchers see each one', async () => {
    const wrapper = await createWrapper(failures({ noPricesTimestamps: [1_700_000_000, 1_700_086_400] }));
    const inputs = wrapper.findAll('[data-testid=missing-daily-price-input] input');

    await inputs[0].setValue('0.5');
    await inputs[0].trigger('blur');
    await flushPromises();
    const afterFirst = get(resolvedFailedDailyPrices).ETH;

    await inputs[1].setValue('0.6');
    await inputs[1].trigger('blur');
    await flushPromises();
    const afterSecond = get(resolvedFailedDailyPrices).ETH;

    expect(afterFirst).toHaveLength(1);
    expect(afterSecond).toHaveLength(2);
    expect(afterSecond).not.toBe(afterFirst);
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

  it('should list the days no price source could be reached for in a tab of their own', async () => {
    const withoutFailure = await createWrapper(failures({ noPricesTimestamps: [1_700_000_000] }));
    expect(withoutFailure.text()).not.toContain('failed_daily_prices.unreachable.title');

    const withFailure = await createWrapper(failures({
      failedPricesTimestamps: [1_700_172_800],
      noPricesTimestamps: [1_700_000_000],
    }));
    expect(withFailure.text()).toContain('failed_daily_prices.unreachable.title');
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
