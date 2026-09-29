import { bigNumberify } from '@rotki/common';
import { type DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import HistoricalBalancesView from '@/modules/statistics/historical-balances/components/HistoricalBalancesView.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { empty, error, processingRequired, refresh, restamp, rows, triggerProcessing } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    empty: ref<boolean>(false),
    error: ref<string>(),
    processingRequired: ref<boolean>(false),
    refresh: vi.fn<() => Promise<void>>(),
    restamp: vi.fn<() => boolean>(),
    rows: ref<unknown[]>([]),
    triggerProcessing: vi.fn<() => Promise<void>>(),
  };
});

vi.mock('@/modules/statistics/historical-balances/use-as-of-date', async () => {
  const { ref } = await import('vue');
  return { useAsOfDate: (): Record<string, unknown> => ({ modelDay: ref('2024-12-31'), restamp, timestamp: ref(1735689599) }) };
});
vi.mock('@/modules/statistics/historical-balances/use-historical-balances-at', async () => {
  const { ref } = await import('vue');
  return {
    useHistoricalBalancesAt: (): Record<string, unknown> => ({ empty, error, groups: ref([]), loading: ref(false), processingRequired, refresh }),
  };
});
vi.mock('@/modules/statistics/historical-balances/use-historical-balance-values', async () => {
  const { computed, ref } = await import('vue');
  const { bigNumberify: toBigNumber } = await import('@rotki/common');
  return {
    useHistoricalBalanceValues: (): Record<string, unknown> => ({
      missingCount: ref(0),
      pendingCount: ref(0),
      rows,
      total: computed(() => toBigNumber('100')),
    }),
  };
});
vi.mock('@/modules/history/balances/use-historical-balances', () => ({
  useHistoricalBalances: (): { triggerHistoricalBalancesProcessing: typeof triggerProcessing } => ({
    triggerHistoricalBalancesProcessing: triggerProcessing,
  }),
}));

function createWrapper(): VueWrapper<InstanceType<typeof HistoricalBalancesView>> {
  return mount(HistoricalBalancesView, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: { DateDisplay: true, FiatDisplay: true, HistoricalBalancesAsOf: true, HistoricalBalancesTable: true },
    },
  });
}

describe('historical balances view', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(empty, false);
    set(error, undefined);
    set(processingRequired, false);
    set(rows, [{ amount: bigNumberify('1'), asset: 'ETH' }]);
    refresh.mockReset().mockResolvedValue();
    restamp.mockReset().mockReturnValue(false);
    triggerProcessing.mockReset().mockResolvedValue();
  });

  it('should offer to process events only while some are unprocessed', async () => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=historical-balances-processing]').exists()).toBe(false);

    set(processingRequired, true);
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-processing]').exists()).toBe(true);
  });

  it('should stay busy after starting processing until the backend reports it finished', async () => {
    set(processingRequired, true);
    const wrapper = createWrapper();
    const processButton = (): DOMWrapper<Element> => wrapper.find('[data-testid=historical-balances-processing] button');

    await processButton().trigger('click');
    await flushPromises();

    expect(triggerProcessing).toHaveBeenCalledOnce();
    expect(refresh).not.toHaveBeenCalled();
    expect(processButton().attributes('disabled')).toBeDefined();

    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await flushPromises();

    expect(processButton().attributes('disabled')).toBeUndefined();
  });

  it('should offer processing when a day comes back empty, since it may never have run', async () => {
    set(empty, true);
    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-processing]').text()).toContain('historical_balances.processing.empty_message');
  });

  it('should leave the reload to the timestamp when refresh moves today\'s as-of time', async () => {
    restamp.mockReturnValue(true);
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=historical-balances-refresh]').trigger('click');
    await flushPromises();

    expect(restamp).toHaveBeenCalledOnce();
    expect(refresh).not.toHaveBeenCalled();
  });

  it('should reload directly when refresh leaves a past day\'s as-of time alone', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=historical-balances-refresh]').trigger('click');
    await flushPromises();

    expect(refresh).toHaveBeenCalledOnce();
  });

  it('should show a failure in place of the total', async () => {
    set(error, 'backend down');
    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-error]').text()).toContain('backend down');
    expect(wrapper.find('[data-testid=historical-balances-total]').exists()).toBe(false);
  });
});
