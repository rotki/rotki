import type { AccountHistorySelection } from '@/modules/balances/account-history/account-history-selection';
import { mount, type VueWrapper } from '@vue/test-utils';
import { set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import AccountHistoryView from '@/modules/balances/account-history/components/AccountHistoryView.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { empty, error, loadedRange, processingRequired, refresh, selection } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    empty: ref<boolean>(false),
    error: ref<string>(),
    loadedRange: ref<{ from: number; to: number }>(),
    processingRequired: ref<boolean>(false),
    refresh: vi.fn<() => Promise<void>>(),
    selection: ref<AccountHistorySelection>({ account: undefined, asset: undefined, location: undefined, range: 'all' }),
  };
});

vi.mock('@/modules/balances/account-history/use-account-history', async () => {
  const { computed, ref } = await import('vue');
  const { Zero } = await import('@rotki/common');
  return {
    useAccountHistory: (): Record<string, unknown> => ({
      assets: computed(() => ['ETH']),
      assetsLoading: ref(false),
      assetsProcessingRequired: ref(false),
      buckets: computed(() => []),
      empty,
      error,
      loadedRange,
      loading: ref(false),
      locations: computed(() => ['ethereum']),
      modelAccount: ref(),
      modelAsset: ref(),
      modelLocation: ref(),
      modelRange: ref('all'),
      processingRequired,
      refresh,
      selection,
      summary: computed(() => ({ change: Zero, current: Zero, start: Zero })),
      total: computed(() => []),
    }),
  };
});

function createWrapper(): VueWrapper<InstanceType<typeof AccountHistoryView>> {
  return mount(AccountHistoryView, {
    global: {
      plugins: [createPinia(), createRuiPlugin({})],
      stubs: {
        AccountBalanceChart: { name: 'AccountBalanceChart', props: ['buckets', 'total'], template: '<div data-testid="chart-stub" />' },
        AccountHistoryEvents: { name: 'AccountHistoryEvents', props: ['account', 'asset', 'location', 'range'], template: '<div data-testid="events-stub" />' },
        AccountHistorySelectors: true,
        AccountHistorySummary: { name: 'AccountHistorySummary', props: ['asset', 'summary', 'processingRequired'], template: '<div data-testid="summary-stub" />' },
      },
    },
  });
}

describe('account history view', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(empty, false);
    set(error, undefined);
    set(loadedRange, { from: 100, to: 200 });
    set(processingRequired, false);
    set(selection, { account: '0xA', asset: 'ETH', location: 'ethereum', range: 'all' });
    refresh.mockReset().mockResolvedValue();
  });

  it('should ask for an account and asset, and show nothing else, until both are picked', () => {
    set(selection, { account: '0xA', asset: undefined, location: undefined, range: 'all' });
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-history-pick]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=chart-stub]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=account-history-refresh]').attributes('disabled')).toBeDefined();
  });

  it('should show the chart and the events pinned to the picked account, asset, location and range', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=chart-stub]').exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'AccountHistoryEvents' }).props()).toEqual({
      account: '0xA',
      asset: 'ETH',
      location: 'ethereum',
      range: { from: 100, to: 200 },
    });
  });

  it('should hold the events back for a bounded range until its window is loaded', async () => {
    set(loadedRange, undefined);
    set(selection, { account: '0xA', asset: 'ETH', location: undefined, range: '1m' });
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(false);

    set(loadedRange, { from: 100, to: 200 });
    await nextTick();

    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(true);
  });

  it('should show the events at once for all time', () => {
    set(loadedRange, undefined);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(true);
  });

  it('should pass pending processing to the summary rather than raising an error', () => {
    set(processingRequired, true);
    const wrapper = createWrapper();

    expect(wrapper.findComponent({ name: 'AccountHistorySummary' }).props('processingRequired')).toBe(true);
    expect(wrapper.find('[data-testid=account-history-error]').exists()).toBe(false);
  });

  it('should replace the chart with an empty state when nothing was held, and say so differently while processing', async () => {
    set(empty, true);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=chart-stub]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=account-history-empty]').text()).toBe('account_history.empty');

    set(processingRequired, true);
    await nextTick();

    expect(wrapper.find('[data-testid=account-history-empty]').text()).toBe('account_history.empty_processing');
  });

  it('should show only the error when loading failed', () => {
    set(error, 'backend down');
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-history-error]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=chart-stub]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=summary-stub]').exists()).toBe(false);
  });

  it('should reload when refresh is pressed', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=account-history-refresh]').trigger('click');

    expect(refresh).toHaveBeenCalledOnce();
  });
});
