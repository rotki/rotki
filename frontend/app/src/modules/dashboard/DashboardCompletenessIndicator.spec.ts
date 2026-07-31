import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import DashboardCompletenessIndicator from '@/modules/dashboard/DashboardCompletenessIndicator.vue';
import DashboardMissingPricesDialog from '@/modules/dashboard/DashboardMissingPricesDialog.vue';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import '@test/i18n';

interface MockState {
  actionableCount: number;
  processing: boolean;
  assetsWithoutOracleHistory: Set<string>;
  refreshSummary: ReturnType<typeof vi.fn>;
}

const state = vi.hoisted((): MockState => ({
  actionableCount: 0,
  assetsWithoutOracleHistory: new Set<string>(),
  processing: false,
  refreshSummary: vi.fn(),
}));

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): Record<string, unknown> => ({
    assetsHadOraclePrice: vi.fn(async (identifiers: string[]): Promise<Record<string, boolean>> =>
      Object.fromEntries(identifiers.map(id => [id, !state.assetsWithoutOracleHistory.has(id)]))),
  }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: (): Record<string, unknown> => ({
    actionableCount: ref(state.actionableCount),
    refreshSummary: state.refreshSummary,
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
        DashboardMissingPricesDialog: true,
        RouterLink: { template: '<div><slot /></div>' },
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('dashboardCompletenessIndicator', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    state.actionableCount = 0;
    state.processing = false;
    state.assetsWithoutOracleHistory = new Set<string>();
    state.refreshSummary = vi.fn().mockResolvedValue(undefined);
    // The flag is only set when the shell exports ROTKI_ACCOUNTING_UPDATE, so pin it
    // per test instead of inheriting whatever the developer's environment has.
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', '');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('should render nothing when there are no completeness issues', async () => {
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-testid=dashboard-completeness]').exists()).toBe(false);
  });

  it('should show a button when assets are missing prices', async () => {
    useBalancePricesStore().prices = {
      ETH: { isManualPrice: false, oracle: 'blockchain', priceMissing: true, usdPrice: null, value: bigNumberify(0) },
    };
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-testid=dashboard-completeness]').text()).toContain('missing_prices');
  });

  it('should open the missing-prices dialog with the affected assets', async () => {
    useBalancePricesStore().prices = {
      ETH: { isManualPrice: false, oracle: 'blockchain', priceMissing: true, usdPrice: null, value: bigNumberify(0) },
    };
    const wrapper = await createWrapper();

    const dialog = wrapper.findComponent(DashboardMissingPricesDialog);
    expect(dialog.props('open')).toBe(false);
    expect(dialog.props('identifiers')).toEqual(['ETH']);

    await wrapper.find('[data-testid=missing-prices-trigger]').trigger('click');
    expect(dialog.props('open')).toBe(true);
  });

  it('should not count a missing price for an asset the oracles never supported', async () => {
    state.assetsWithoutOracleHistory = new Set(['FOO']);
    useBalancePricesStore().prices = {
      FOO: { isManualPrice: false, oracle: 'blockchain', priceMissing: true, usdPrice: null, value: bigNumberify(0) },
    };
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-testid=dashboard-completeness]').exists()).toBe(false);
  });

  it('should show a button for leftover undecoded transactions', async () => {
    useDecodingStatusStore().setUndecodedTransactionsStatus({ chain: 'eth', processed: 2, total: 10 });
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-testid=dashboard-completeness]').text()).toContain('undecoded');
  });

  it('should hide the undecoded button while history is processing', async () => {
    state.processing = true;
    useDecodingStatusStore().setUndecodedTransactionsStatus({ chain: 'eth', processed: 2, total: 10 });
    const wrapper = await createWrapper();
    expect(wrapper.find('[data-testid=dashboard-completeness]').exists()).toBe(false);
  });

  it('should show a button when data issues need attention', async () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', 'true');
    state.actionableCount = 3;
    const wrapper = await createWrapper();
    expect(state.refreshSummary).toHaveBeenCalledOnce();
    expect(wrapper.find('[data-testid=dashboard-completeness]').text()).toContain('data_issues');
  });

  it('should not query or show data issues when the accounting update flag is off', async () => {
    state.actionableCount = 3;
    const wrapper = await createWrapper();
    expect(state.refreshSummary).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=dashboard-completeness]').exists()).toBe(false);
  });
});
