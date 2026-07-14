import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import BalanceDivergenceView from '@/modules/history/balances/BalanceDivergenceView.vue';
import { useHistoryStore } from '@/modules/history/use-history-store';

const mockFindDivergence = vi.fn();
const mockFetchLocationLabels = vi.fn();
const mockRequestNavigation = vi.fn();
const mockSetHighlightTarget = vi.fn();

const { archiveState } = vi.hoisted(() => ({ archiveState: { hasArchive: true } }));

vi.mock('@/modules/settings/api/use-evm-nodes-api', () => ({
  useEvmNodesApi: (): object => ({
    fetchEvmNodes: async (): Promise<{ isArchive: boolean }[]> => [{ isArchive: archiveState.hasArchive }],
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getEvmChainName: (chain: string): string | undefined => chain === 'eth' ? 'ethereum' : undefined,
    isEvm: (chain: string): boolean => chain === 'eth',
    matchChain: (location: string): string | undefined => ['eth', 'ethereum'].includes(location) ? 'eth' : undefined,
  }),
}));

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): object => ({
    findHistoricalBalanceDivergence: mockFindDivergence,
  }),
}));

const { taskControl } = vi.hoisted(() => ({ taskControl: { failure: null as null | Record<string, unknown> } }));

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  isActionableFailure: (outcome: { success: boolean; cancelled: boolean; skipped: boolean }): boolean =>
    !outcome.success && !outcome.cancelled && !outcome.skipped,
  useTaskHandler: (): object => ({
    runTask: async (task: () => Promise<unknown>): Promise<object> => {
      await task();
      return taskControl.failure ?? makeDivergenceResult();
    },
  }),
}));

vi.mock('@/modules/history/use-history-data-fetching', () => ({
  useHistoryDataFetching: (): object => ({
    fetchLocationLabels: mockFetchLocationLabels,
  }),
}));

vi.mock('@/modules/history/events/use-history-event-navigation', () => ({
  HighlightTargetTypes: {
    ACCOUNTING_EVENT: 'accountingEvent',
  },
  useHistoryEventNavigation: (): object => ({
    requestNavigation: mockRequestNavigation,
    setHighlightTarget: mockSetHighlightTarget,
  }),
}));

const stubs = {
  AssetAmountDisplay: { props: ['amount', 'asset'], template: '<span class="amount">{{ amount?.toString() }}</span>' },
  AssetSelect: defineComponent({
    emits: ['update:modelValue'],
    props: {
      label: String,
      modelValue: String,
    },
    template: '<label><span>{{ label }}</span><input data-testid="asset-select-input" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" /></label>',
  }),
  ChainSelect: defineComponent({
    emits: ['update:modelValue'],
    props: {
      items: Array,
      label: String,
      modelValue: String,
    },
    template: '<label><span>{{ label }}</span><select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in items" :key="item" :value="item">{{ item }}</option></select></label>',
  }),
  LocationLabelSelector: defineComponent({
    emits: ['update:modelValue'],
    props: {
      label: String,
      modelValue: String,
      options: Array,
    },
    template: '<label><span>{{ label }}</span><select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in options" :key="item.locationLabel" :value="item.locationLabel">{{ item.locationLabel }}</option></select></label>',
  }),
  RuiButton: defineComponent({
    props: {
      disabled: Boolean,
      loading: Boolean,
    },
    template: '<button :disabled="disabled"><slot name="prepend" /><slot /></button>',
  }),
  RuiIcon: { template: '<i class="icon" />' },
  RuiTooltip: { template: '<div><slot name="activator" /><slot /></div>' },
  I18nT: { template: '<span><slot name="chain" /><slot name="link" /></span>' },
  InternalLink: { template: '<a><slot /></a>' },
  HashLink: { props: ['text'], template: '<span class="hash">{{ text }}</span>' },
  RuiAlert: { template: '<div class="alert"><slot /></div>' },
  HistoryEventNote: { props: ['notes'], template: '<div class="notes">{{ notes }}</div>' },
};

function makeDivergenceResult(): object {
  return {
    result: {
      address: '0xA',
      asset: 'ETH',
      firstDiverged: {
        blockNumber: 12,
        difference: '0.1',
        eventIdentifier: 102,
        groupIdentifier: `1${'b'.repeat(64)}`,
        onchainBalance: '4.9',
        timestamp: 200,
        trackedBalance: '5',
      },
      lastMatching: {
        blockNumber: 11,
        difference: '0',
        eventIdentifier: 101,
        groupIdentifier: `1${'a'.repeat(64)}`,
        onchainBalance: '5',
        timestamp: 100,
        trackedBalance: '5',
      },
      location: 'ethereum',
      probes: [],
      status: 'diverged',
      tolerance: '0',
      totalEvents: 2,
    },
    success: true,
  };
}

function mountView(): VueWrapper {
  const pinia = createPinia();
  setActivePinia(pinia);
  useHistoryStore().setLocationLabels([]);
  useBlockchainAccountsStore().updateAccounts('eth', [{
    chain: 'eth',
    data: {
      address: '0xA',
      type: 'address',
    },
    nativeAsset: 'ETH',
  }]);
  mockFindDivergence.mockResolvedValue({ taskId: 1 });

  return mount(BalanceDivergenceView, {
    global: {
      plugins: [pinia],
      stubs,
    },
  });
}

describe('balanceDivergenceView.vue', () => {
  beforeEach(() => {
    archiveState.hasArchive = true;
    taskControl.failure = null;
    mockFetchLocationLabels.mockResolvedValue(undefined);
    mockFindDivergence.mockReset();
    mockRequestNavigation.mockReset();
    mockSetHighlightTarget.mockReset();
  });

  it('should find divergence for the selected scope and navigate to a boundary event', async () => {
    const wrapper = mountView();

    await nextTick();
    await flushPromises();
    await wrapper.find('[data-testid=asset-select-input]').setValue('ETH');
    await wrapper.find('[data-testid=find-divergence]').trigger('click');
    await flushPromises();

    expect(mockFindDivergence).toHaveBeenCalledWith({
      address: '0xA',
      asset: 'ETH',
      evmChain: 'ethereum',
    });
    expect(wrapper.find('[data-testid=divergence-last_matching]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=divergence-first_diverged]').exists()).toBe(true);

    await wrapper.find('[data-testid=view-divergence-last_matching]').trigger('click');

    expect(mockSetHighlightTarget).toHaveBeenCalledWith('accountingEvent', {
      groupIdentifier: `1${'a'.repeat(64)}`,
      identifier: 101,
    });
    expect(mockRequestNavigation).toHaveBeenCalledWith({
      assetFilter: 'ETH',
      highlightedAccountingEvent: 101,
      targetGroupIdentifier: `1${'a'.repeat(64)}`,
    });
  });

  it('should block the search and link to rpc settings when the selected chain has no archive node', async () => {
    archiveState.hasArchive = false;
    const wrapper = mountView();

    await nextTick();
    await flushPromises();

    expect(wrapper.find('[data-testid=balance-divergence-missing-archive]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=find-divergence]').attributes('disabled')).toBeDefined();
  });

  it('should render an actionable failure as an alert with the parsed message', async () => {
    taskControl.failure = {
      cancelled: false,
      message: 'No historical wallet balance data found for eip155:1/erc20:0xA at 0xA on ethereum',
      skipped: false,
      success: false,
    };
    const wrapper = mountView();

    await nextTick();
    await flushPromises();
    await wrapper.find('[data-testid=asset-select-input]').setValue('ETH');
    await wrapper.find('[data-testid=find-divergence]').trigger('click');
    await flushPromises();

    const alert = wrapper.find('[data-testid=divergence-error]');
    expect(alert.exists()).toBe(true);
    expect(alert.text()).toContain('No historical wallet balance data');
  });

  it('should emit close when the panel header is closed', async () => {
    const wrapper = mountView();

    await wrapper.find('[data-testid=balance-divergence-close]').trigger('click');

    expect(wrapper.emitted('close')).toHaveLength(1);
  });
});
