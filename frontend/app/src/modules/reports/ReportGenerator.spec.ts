import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ReportGenerator from '@/modules/reports/ReportGenerator.vue';

const mocks = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    exchangesWithoutMarkets: ref<string[]>([]),
    hasExchangesWithoutMarkets: ref<boolean>(false),
    isOutOfSync: ref<boolean>(true),
    processing: ref<boolean>(false),
    progress: ref<number>(0),
    refreshTransactions: vi.fn<(params?: { userInitiated?: boolean }) => Promise<void>>().mockResolvedValue(undefined),
  };
});

vi.mock('@/modules/history/sync-status/use-transaction-status-check', () => ({
  useTransactionStatusCheck: (): Record<string, unknown> => ({ isOutOfSync: mocks.isOutOfSync, processing: mocks.processing }),
}));

vi.mock('@/modules/history/events/tx/use-sync-rollup', () => ({
  useSyncRollup: (): Record<string, unknown> => ({ progress: mocks.progress }),
}));

vi.mock('@/modules/history/events/tx/use-history-transactions', () => ({
  useHistoryTransactions: (): Record<string, unknown> => ({ refreshTransactions: mocks.refreshTransactions }),
}));

vi.mock('@/modules/reports/use-binance-market-check', () => ({
  useBinanceMarketCheck: (): Record<string, unknown> => ({
    checkMarketPairs: vi.fn(),
    exchangesWithoutMarkets: mocks.exchangesWithoutMarkets,
    hasExchangesWithoutMarkets: mocks.hasExchangesWithoutMarkets,
  }),
}));

function mountGenerator(): VueWrapper {
  return mount(ReportGenerator, {
    global: {
      plugins: [createCustomPinia()],
      provide: libraryDefaults,
      stubs: { RangeSelector: true, ReportDebugMenu: true, RouterLink: true },
    },
  });
}

describe('modules/reports/ReportGenerator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mocks.isOutOfSync, true);
  });

  it('should sync history as a refresh the user asked for, so an already loaded history is not skipped', async () => {
    const wrapper = mountGenerator();

    await wrapper.find('[data-testid="report-generator-sync-history"]').trigger('click');

    expect(mocks.refreshTransactions).toHaveBeenCalledExactlyOnceWith({ userInitiated: true });
  });

  it('should offer no sync while history is in sync', () => {
    set(mocks.isOutOfSync, false);

    const wrapper = mountGenerator();

    expect(wrapper.find('[data-testid="report-generator-sync-history"]').exists()).toBe(false);
  });
});
