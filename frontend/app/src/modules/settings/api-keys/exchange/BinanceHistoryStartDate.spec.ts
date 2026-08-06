import { shallowMount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import BinanceHistoryStartDate from '@/modules/settings/api-keys/exchange/BinanceHistoryStartDate.vue';
import '@test/i18n';

const { queryBinanceHistoryStartTimestamp } = vi.hoisted(() => ({
  queryBinanceHistoryStartTimestamp: vi.fn<() => Promise<number>>(),
}));

vi.mock('@/modules/balances/api/use-exchange-api', () => ({
  useExchangeApi: (): { queryBinanceHistoryStartTimestamp: () => Promise<number> } => ({
    queryBinanceHistoryStartTimestamp,
  }),
}));

describe('binance-history-start-date', () => {
  let wrapper: VueWrapper<InstanceType<typeof BinanceHistoryStartDate>>;

  beforeEach(() => {
    queryBinanceHistoryStartTimestamp.mockClear();
    queryBinanceHistoryStartTimestamp.mockResolvedValue(1700000001);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should prepopulate the start date from the newest Binance CSV import', async () => {
    wrapper = shallowMount(BinanceHistoryStartDate, {
      props: { modelValue: 1800000000 },
    });
    await flushPromises();

    expect(wrapper.emitted<number[]>('update:modelValue')?.at(-1)).toEqual([1700000001]);
    expect(wrapper.find('[data-testid="binance-history-start"]').exists()).toBe(true);
  });
});
