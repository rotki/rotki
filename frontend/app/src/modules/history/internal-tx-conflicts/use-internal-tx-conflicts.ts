import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import { startPromise } from '@shared/utils';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { internalTxFixedSignal } from '@/modules/messaging/handlers/internal-tx-fixed';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { logger } from '@/utils/logging';
import { useInternalTxConflictsApi } from './internal-tx-conflicts-api';
import { type InternalTxConflict, type InternalTxConflictsRequestPayload, type InternalTxConflictStatus, InternalTxConflictStatuses } from './types';
import { type Filters, type Matcher, useInternalTxConflictsFilter } from './use-internal-tx-conflicts-filter';

export function getConflictKey(conflict: InternalTxConflict): string {
  return `${conflict.chain}:${conflict.txHash}`;
}

function getStatusFilter(status: InternalTxConflictStatus): { failed?: boolean; fixed?: boolean } {
  if (status === InternalTxConflictStatuses.PENDING)
    return { failed: false, fixed: false };

  if (status === InternalTxConflictStatuses.FAILED)
    return { failed: true };

  return { fixed: true };
}

interface UseInternalTxConflictsReturn {
  activeFilter: Ref<InternalTxConflictStatus>;
  conflicts: ComputedRef<InternalTxConflict[]>;
  failedCount: Ref<number>;
  fetchConflicts: () => Promise<void>;
  fetchCounts: () => Promise<void>;
  filters: WritableComputedRef<Filters>;
  handleConflictFixed: () => Promise<void>;
  issueCount: ComputedRef<number>;
  loading: Ref<boolean>;
  matchers: ComputedRef<Matcher[]>;
  pagination: WritableComputedRef<TablePaginationData>;
  pendingCount: Ref<number>;
  setFilter: (status: InternalTxConflictStatus) => void;
  sort: WritableComputedRef<DataTableSortData<InternalTxConflict>>;
  totalFound: ComputedRef<number>;
}

export const useInternalTxConflicts = createSharedComposable((): UseInternalTxConflictsReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { showErrorMessage } = useNotifications();
  const { fetchInternalTxConflicts, fetchInternalTxConflictsCount } = useInternalTxConflictsApi();

  const pendingCount = ref<number>(0);
  const failedCount = ref<number>(0);
  const issueCount = computed<number>(() => get(pendingCount) + get(failedCount));
  const activeFilter = ref<InternalTxConflictStatus>(InternalTxConflictStatuses.PENDING);

  const requestParams = computed<Partial<InternalTxConflictsRequestPayload>>(() => ({
    ...getStatusFilter(get(activeFilter)),
  }));

  const {
    fetchData,
    filters,
    isLoading: loading,
    matchers,
    pagination,
    setPage,
    sort,
    state,
  } = usePaginationFilters<InternalTxConflict, InternalTxConflictsRequestPayload, Filters, Matcher>(
    fetchInternalTxConflicts,
    {
      defaultSortBy: {
        column: 'chain',
        direction: 'asc',
      },
      filterSchema: () => useInternalTxConflictsFilter(),
      requestParams,
    },
  );

  const conflicts = computed<InternalTxConflict[]>(() => get(state).data);
  const totalFound = computed<number>(() => get(state).found);

  async function fetchCounts(): Promise<void> {
    try {
      const result = await fetchInternalTxConflictsCount();
      set(pendingCount, result.pending);
      set(failedCount, result.failed);
    }
    catch (error: any) {
      logger.error('Failed to fetch internal tx conflicts counts:', error);
    }
  }

  async function fetchConflicts(): Promise<void> {
    try {
      await fetchData();
    }
    catch (error: any) {
      logger.error('Failed to fetch internal tx conflicts:', error);
      showErrorMessage(
        t('internal_tx_conflicts.errors.fetch_title'),
        t('internal_tx_conflicts.errors.fetch', { error: error.message }),
      );
    }
  }

  function setFilter(status: InternalTxConflictStatus): void {
    set(activeFilter, status);
    setPage(1);
  }

  async function handleConflictFixed(): Promise<void> {
    await Promise.all([fetchCounts(), fetchConflicts()]);
  }

  watchDebounced(internalTxFixedSignal, () => {
    startPromise(handleConflictFixed());
  }, { debounce: 800 });

  return {
    activeFilter,
    conflicts,
    failedCount,
    fetchConflicts,
    fetchCounts,
    filters,
    handleConflictFixed,
    issueCount,
    loading,
    matchers,
    pagination,
    pendingCount,
    setFilter,
    sort,
    totalFound,
  };
});
