import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import DashboardCompletenessIndicator from '@/modules/dashboard/DashboardCompletenessIndicator.vue';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import '@test/i18n';

interface MockState {
  actionableCount: number;
  processing: boolean;
}

const state = vi.hoisted((): MockState => ({
  actionableCount: 0,
  processing: false,
}));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: (): Record<string, unknown> => ({
    actionableCount: ref(state.actionableCount),
    refreshSummary: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('@/modules/history/events/tx/use-history-transaction-decoding', () => ({
  useHistoryTransactionDecoding: (): Record<string, unknown> => ({
    fetchUndecodedTransactionsBreakdown: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: (): Record<string, unknown> => ({
    processing: computed(() => state.processing),
  }),
}));

async function createWrapper(): Promise<VueWrapper<InstanceType<typeof DashboardCompletenessIndicator>>> {
  const wrapper = mount(DashboardCompletenessIndicator, {
    global: {
      stubs: {
        RouterLink: { template: '<div><slot /></div>' },
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('dashboardCompletenessIndicator', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    state.actionableCount = 0;
    state.processing = false;
  });

  it('should render nothing when there are no completeness issues', async () => {
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-cy=dashboard-completeness]').exists()).toBe(false);
  });

  it('should show a chip when assets are missing prices', async () => {
    useBalancePricesStore().prices = {
      ETH: { isManualPrice: false, oracle: 'blockchain', priceMissing: true, usdPrice: null, value: '0' },
    } as never;
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-cy=dashboard-completeness]').text()).toContain('missing_prices');
  });

  it('should show a chip for leftover undecoded transactions', async () => {
    useDecodingStatusStore().setUndecodedTransactionsStatus({ chain: 'eth', processed: 2, total: 10 });
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-cy=dashboard-completeness]').text()).toContain('undecoded');
  });

  it('should hide the undecoded chip while history is processing', async () => {
    state.processing = true;
    useDecodingStatusStore().setUndecodedTransactionsStatus({ chain: 'eth', processed: 2, total: 10 });
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-cy=dashboard-completeness]').exists()).toBe(false);
  });

  it('should show a chip when data issues need attention', async () => {
    state.actionableCount = 3;
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-cy=dashboard-completeness]').text()).toContain('data_issues');
  });
});
