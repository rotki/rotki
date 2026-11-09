import type { UseDataIssuesDetectionReturn } from '@/modules/history/data-issues/use-data-issues-detection';
import type { UseBucketReconciliationApiReturn } from '@/modules/history/reconciliation/api/use-bucket-reconciliation-api';
import type { ReconciliationAccount, ReconciliationResponse, StatusCounts } from '@/modules/history/reconciliation/schemas';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ReconciliationView from '@/modules/history/reconciliation/ReconciliationView.vue';
import { useBucketReconciliationStore } from '@/modules/history/reconciliation/use-bucket-reconciliation-store';

const { fetchAccount, fetchSummary } = vi.hoisted(() => ({
  fetchAccount: vi.fn<() => Promise<ReconciliationAccount | undefined>>(),
  fetchSummary: vi.fn<() => Promise<ReconciliationResponse>>(),
}));

vi.mock('@/modules/history/reconciliation/api/use-bucket-reconciliation-api', () => ({
  ACCOUNT_PAGE_SIZE: 50,
  MAX_ACCOUNT_BUCKETS: 500,
  useBucketReconciliationApi: (): UseBucketReconciliationApiReturn => ({ fetchAccount, fetchSummary }),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-auto-reload', () => ({
  useDataIssuesAutoReload: vi.fn(),
}));

vi.mock('@/modules/history/data-issues/use-data-issues-detection', async () => {
  const { ref } = await import('vue');
  return {
    useDataIssuesDetection: (): UseDataIssuesDetectionReturn => ({
      detect: vi.fn(async () => ({ conflict: false, success: true })),
      detectFailure: ref<NamedFailure | undefined>(undefined),
      detecting: ref<boolean>(false),
    }),
  };
});

function report(stale: boolean): ReconciliationResponse {
  const counts: StatusCounts = {
    blocked: 0,
    mismatch: 0,
    notCompared: 0,
    pending: stale ? 1 : 0,
    reconciled: stale ? 0 : 1,
  };
  return {
    accounts: [{
      counts,
      historySyncedTo: 100,
      isExchange: false,
      lastComparedAt: 100,
      lastEventTs: 1000,
      location: 'ethereum',
      locationLabel: '0x0000000000000000000000000000000000000001',
    }],
    bucketsTotal: 1,
    processing: false,
    stale,
    totals: counts,
  };
}

describe('reconciliation view freshness', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchAccount.mockResolvedValue(undefined);
  });

  it('should stop offering a check when returning to a cached view after history becomes stale', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    useBucketReconciliationStore().setSummary(report(false));
    fetchSummary.mockResolvedValue(report(true));

    const wrapper = mount(ReconciliationView, {
      global: {
        plugins: [pinia],
        stubs: {
          DataIssuesTabs: true,
          ReconciliationTable: true,
          TablePageLayout: { template: '<main><slot /></main>' },
        },
      },
    });
    await flushPromises();

    expect(wrapper.get('[data-testid="reconciliation-check-now"]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid="reconciliation-recalculating"]').exists()).toBe(true);
  });
});
