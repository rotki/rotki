import { bigNumberify } from '@rotki/common';
import { type DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type MaybeRefOrGetter, toValue } from 'vue';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import HistoricalBalancesView from '@/modules/statistics/historical-balances/components/HistoricalBalancesView.vue';
import { createRuiPlugin } from '@/plugins/rui';

const {
  blockedReason,
  empty,
  error,
  exportCsv,
  filtered,
  loadedAt,
  processingRequired,
  refresh,
  restamp,
  rows,
  triggerProcessing,
  valuedAt,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  const valuedAt: { current?: MaybeRefOrGetter<number> } = {};
  return {
    blockedReason: ref<string>(),
    empty: ref<boolean>(false),
    error: ref<string>(),
    exportCsv: vi.fn<() => void>(),
    filtered: ref<boolean>(false),
    loadedAt: ref<number>(),
    processingRequired: ref<boolean>(false),
    refresh: vi.fn<() => Promise<void>>(),
    restamp: vi.fn<() => boolean>(),
    rows: ref<unknown[]>([]),
    triggerProcessing: vi.fn<() => Promise<boolean>>(),
    valuedAt,
  };
});

vi.mock('@/modules/statistics/historical-balances/use-as-of-date', async () => {
  const { ref } = await import('vue');
  return { useAsOfDate: (): Record<string, unknown> => ({ modelDay: ref('2024-12-31'), restamp, timestamp: ref(1735689599) }) };
});
vi.mock('@/modules/statistics/historical-balances/use-historical-balances-at', async () => {
  const { ref } = await import('vue');
  return {
    useHistoricalBalancesAt: (): Record<string, unknown> => ({ empty, error, groups: ref([]), loadedAt, loading: ref(false), processingRequired, refresh }),
  };
});
vi.mock('@/modules/statistics/historical-balances/use-historical-balance-values', async (importOriginal) => {
  const { ref } = await import('vue');
  return {
    ...await importOriginal<typeof import('@/modules/statistics/historical-balances/use-historical-balance-values')>(),
    useHistoricalBalanceValues: (_groups: unknown, at: MaybeRefOrGetter<number>): Record<string, unknown> => {
      valuedAt.current = at;
      return { rows: ref([]) };
    },
  };
});
vi.mock('@/modules/statistics/historical-balances/use-historical-balances-view', async () => {
  const { computed, ref } = await import('vue');
  const { bigNumberify: toBigNumber } = await import('@rotki/common');
  return {
    useHistoricalBalancesView: (): Record<string, unknown> => ({
      accounts: ref([]),
      filtered,
      locations: ref([]),
      modelAccounts: ref([]),
      modelLocations: ref([]),
      modelMode: ref('collection'),
      modelSearch: ref(''),
      rows,
      summary: computed(() => ({ missingCount: 0, pendingCount: 0, spamCount: 0, total: toBigNumber('100') })),
    }),
  };
});
vi.mock('@/modules/statistics/historical-balances/use-historical-balances-export', () => ({
  useHistoricalBalancesExport: (): Record<string, unknown> => ({ blockedReason, exportCsv }),
}));
vi.mock('@/modules/history/balances/use-historical-balances', () => ({
  useHistoricalBalances: (): { triggerHistoricalBalancesProcessing: typeof triggerProcessing } => ({
    triggerHistoricalBalancesProcessing: triggerProcessing,
  }),
}));

function createWrapper(): VueWrapper<InstanceType<typeof HistoricalBalancesView>> {
  return mount(HistoricalBalancesView, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: { DateDisplay: true, FiatDisplay: true, HistoricalBalancesAsOf: true, HistoricalBalancesFilters: true, HistoricalBalancesTable: true },
    },
  });
}

describe('historical balances view', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(blockedReason, undefined);
    set(empty, false);
    set(error, undefined);
    set(filtered, false);
    exportCsv.mockReset();
    set(loadedAt, undefined);
    set(processingRequired, false);
    set(rows, [{ amount: bigNumberify('1'), asset: 'ETH' }]);
    refresh.mockReset().mockResolvedValue();
    restamp.mockReset().mockReturnValue(false);
    triggerProcessing.mockReset().mockResolvedValue(true);
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

  it('should stop offering processing once a run finished and the day is still empty', async () => {
    set(empty, true);
    const wrapper = createWrapper();

    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-processing]').text()).toContain('historical_balances.processing.done_empty');
    expect(wrapper.find('[data-testid=historical-balances-process]').exists()).toBe(false);
  });

  it('should still offer processing after a run when events are unprocessed again', async () => {
    const wrapper = createWrapper();
    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await flushPromises();

    set(processingRequired, true);
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-process]').exists()).toBe(true);
  });

  it('should say so when the backend could not start processing', async () => {
    set(empty, true);
    triggerProcessing.mockResolvedValue(false);
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=historical-balances-process]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-process-not-started]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=historical-balances-process]').attributes('disabled')).toBeUndefined();
  });

  it('should show why starting processing failed', async () => {
    set(empty, true);
    triggerProcessing.mockRejectedValue(new Error('backend down'));
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=historical-balances-process]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-process-failed]').text()).toContain('historical_balances.processing.failed');
  });

  it('should price the shown balances at the day they were loaded for, not the one being loaded', () => {
    set(loadedAt, 1704067199);
    createWrapper();

    expect(toValue(valuedAt.current)).toBe(1704067199);
  });

  it('should price at the requested day before any balances have loaded', () => {
    createWrapper();

    expect(toValue(valuedAt.current)).toBe(1735689599);
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

  it('should export the shown balances when nothing blocks it', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=historical-balances-export]').trigger('click');

    expect(exportCsv).toHaveBeenCalledOnce();
  });

  it('should hold the export back while something blocks it', () => {
    set(blockedReason, 'prices loading');
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=historical-balances-export]').attributes('disabled')).toBeDefined();
  });

  it('should say under the total what the balances leave out', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=historical-balances-coverage]').text()).toBe('historical_balances.total.coverage');
  });

  it('should mark the total as filtered only while a filter narrows it', async () => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=historical-balances-total-filtered]').exists()).toBe(false);

    set(filtered, true);
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-total-filtered]').exists()).toBe(true);
  });

  it('should show a failure in place of the total', async () => {
    set(error, 'backend down');
    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('[data-testid=historical-balances-error]').text()).toContain('backend down');
    expect(wrapper.find('[data-testid=historical-balances-total]').exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'HistoricalBalancesTable' }).exists()).toBe(false);
  });
});
