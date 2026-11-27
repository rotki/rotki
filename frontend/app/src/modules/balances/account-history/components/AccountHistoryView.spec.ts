import type { AccountHistorySelection } from '@/modules/balances/account-history/account-history-selection';
import { mount, type VueWrapper } from '@vue/test-utils';
import { set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import AccountHistoryView from '@/modules/balances/account-history/components/AccountHistoryView.vue';
import { createRuiPlugin } from '@/plugins/rui';

const state = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    empty: ref<boolean>(false),
    error: ref<string>(),
    eventsRange: ref<{ from: number; to: number }>(),
    premium: ref<boolean>(true),
    processingRequired: ref<boolean>(false),
    refresh: vi.fn<() => Promise<void>>(),
    reloadEvents: vi.fn<() => void>(),
    selection: ref<AccountHistorySelection>({ account: undefined, asset: undefined, location: undefined, range: 'all' }),
  };
});

vi.mock('@/modules/history/events/use-history-events-section', () => ({
  provideHistoryEventsSection: (): { reload: () => void } => ({ reload: state.reloadEvents }),
}));
vi.mock('@/modules/assets/use-asset-info-retrieval', async (importOriginal) => {
  const { computed } = await import('vue');
  return {
    ...await importOriginal<Record<string, unknown>>(),
    useAssetInfoRetrieval: (): Record<string, unknown> => ({ useAssetField: (): unknown => computed(() => 'ETH') }),
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
      empty: state.empty,
      error: state.error,
      eventsRange: state.eventsRange,
      loadedRange: state.eventsRange,
      loading: ref(false),
      modelAccount: ref(),
      modelAsset: ref(),
      modelLocation: ref(),
      locations: computed(() => ['ethereum']),
      modelRange: ref('all'),
      picked: computed(() => !!state.selection.value.account && !!state.selection.value.asset),
      premium: state.premium,
      processingRequired: state.processingRequired,
      refresh: state.refresh,
      selection: state.selection,
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
        AccountBalanceChart: {
          name: 'AccountBalanceChart',
          props: ['buckets', 'total', 'loading'],
          template: '<div data-testid="chart-stub"><slot name="placeholder" /></div><div data-testid="chart-actions"><slot name="actions" /></div>',
        },
        AccountHistoryEvents: { name: 'AccountHistoryEvents', props: ['account', 'asset', 'location', 'range'], template: '<div data-testid="events-stub" />' },
        AccountHistorySelectors: { name: 'AccountHistorySelectors', props: ['restrictAssets'], template: '<div />' },
        AccountHistorySummary: { name: 'AccountHistorySummary', props: ['asset', 'summary', 'processingRequired', 'showChange'], template: '<div data-testid="summary-stub" />' },
        GetPremiumPlaceholder: { name: 'GetPremiumPlaceholder', template: '<div />' },
      },
    },
  });
}

function placeholderOf(wrapper: VueWrapper<InstanceType<typeof AccountHistoryView>>): string | undefined {
  return wrapper.find('[data-testid=chart-stub]').element.firstElementChild?.getAttribute('data-testid') ?? undefined;
}

describe('account history view', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(state.empty, false);
    set(state.error, undefined);
    set(state.eventsRange, { from: 100, to: 200 });
    set(state.premium, true);
    set(state.processingRequired, false);
    set(state.selection, { account: '0xA', asset: 'ETH', location: 'ethereum', range: 'all' });
    state.refresh.mockReset().mockResolvedValue();
    state.reloadEvents.mockReset();
  });

  it('should keep the summary and chart in place, with a pick prompt in the chart, until both are picked', () => {
    set(state.selection, { account: '0xA', asset: undefined, location: undefined, range: 'all' });
    const wrapper = createWrapper();

    expect(wrapper.findComponent({ name: 'AccountHistorySummary' }).props('asset')).toBeUndefined();
    expect(placeholderOf(wrapper)).toBe('account-history-pick');
    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=account-history-refresh]').attributes('disabled')).toBeDefined();
  });

  it('should draw the chart and the events pinned to the picked account, asset, location and range', () => {
    const wrapper = createWrapper();

    expect(placeholderOf(wrapper)).toBeUndefined();
    expect(wrapper.findComponent({ name: 'AccountHistorySummary' }).props('asset')).toBe('ETH');
    expect(wrapper.findComponent({ name: 'AccountHistoryEvents' }).props()).toEqual({
      account: '0xA',
      asset: 'ETH',
      location: 'ethereum',
      range: { from: 100, to: 200 },
    });
  });

  it('should hold the events back for a bounded range until its window is known', async () => {
    set(state.eventsRange, undefined);
    set(state.selection, { account: '0xA', asset: 'ETH', location: undefined, range: '1m' });
    const wrapper = createWrapper();
    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(false);

    set(state.eventsRange, { from: 100, to: 200 });
    await nextTick();

    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(true);
  });

  it('should show the events at once for all time', () => {
    set(state.eventsRange, undefined);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(true);
  });

  it('should pass pending processing to the summary rather than raising an error', () => {
    set(state.processingRequired, true);
    const wrapper = createWrapper();

    expect(wrapper.findComponent({ name: 'AccountHistorySummary' }).props('processingRequired')).toBe(true);
    expect(placeholderOf(wrapper)).toBeUndefined();
  });

  it('should say in the chart when nothing was held, and differently while processing', async () => {
    set(state.empty, true);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=account-history-empty]').text()).toBe('account_history.empty');

    set(state.processingRequired, true);
    await nextTick();

    expect(wrapper.find('[data-testid=account-history-empty]').text()).toBe('account_history.empty_processing');
  });

  it('should show a failed load in the chart and blank the summary', () => {
    set(state.error, 'backend down');
    const wrapper = createWrapper();

    expect(placeholderOf(wrapper)).toBe('account-history-error');
    expect(wrapper.findComponent({ name: 'AccountHistorySummary' }).props('asset')).toBeUndefined();
  });

  it('should show the premium placeholder in the chart without premium, and still list the events', () => {
    set(state.premium, false);
    const wrapper = createWrapper();

    expect(wrapper.findComponent({ name: 'GetPremiumPlaceholder' }).exists()).toBe(true);
    expect(wrapper.find('[data-testid=summary-stub]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=events-stub]').exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'AccountHistorySelectors' }).props('restrictAssets')).toBe(false);
  });

  it('should reload the balances and the events together when refresh is pressed', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=account-history-refresh]').trigger('click');

    expect(state.refresh).toHaveBeenCalledOnce();
    expect(state.reloadEvents).toHaveBeenCalledOnce();
  });

  it('should reload only the events without premium', async () => {
    set(state.premium, false);
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=account-history-refresh]').trigger('click');

    expect(state.reloadEvents).toHaveBeenCalledOnce();
    expect(state.refresh).not.toHaveBeenCalled();
  });

  it('should leave the change out of the summary for all time', async () => {
    const wrapper = createWrapper();
    expect(wrapper.findComponent({ name: 'AccountHistorySummary' }).props('showChange')).toBe(false);

    set(state.selection, { ...state.selection.value, range: '1y' });
    await nextTick();

    expect(wrapper.findComponent({ name: 'AccountHistorySummary' }).props('showChange')).toBe(true);
  });

  it('should put the range in the chart header, where it stays usable over any placeholder', () => {
    set(state.premium, false);
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=chart-actions]').findComponent({ name: 'AccountHistoryRangeSelector' }).exists()).toBe(true);
  });
});
