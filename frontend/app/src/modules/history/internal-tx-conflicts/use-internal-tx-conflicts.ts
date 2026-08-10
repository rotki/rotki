import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { Filters } from './use-internal-tx-conflicts-filter';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';
import { internalTxFixedSignal } from '@/modules/core/messaging/handlers/internal-tx-fixed';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useInternalTxConflictsApi } from './internal-tx-conflicts-api';
import { type InternalTxConflict, type InternalTxConflictsRequestPayload, type InternalTxConflictStatus, InternalTxConflictStatuses } from './types';

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
  const refreshing = ref<boolean>(false);
  const issueCount = computed<number>(() => get(pendingCount) + get(failedCount));
  const activeFilter = ref<InternalTxConflictStatus>(InternalTxConflictStatuses.PENDING);

  const requestParams = computed<Partial<InternalTxConflictsRequestPayload>>(() => ({
    ...getStatusFilter(get(activeFilter)),
  }));

  const {
    collection: state,
    filter: filters,
    isLoading: loading,
    pagination,
    refetch: fetchData,
    setPage,
    sort,
  } = useServerTable<InternalTxConflict, InternalTxConflictsRequestPayload, Filters>({
    fetch: fetchInternalTxConflicts,
    params: [{ skipEmpty: true, to: 'request', values: requestParams }],
    sort: {
      default: {
        column: 'chain',
        direction: 'asc',
      },
    },
  });

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
    if (get(refreshing))
      return;

    set(refreshing, true);
    try {
      await Promise.all([fetchCounts(), fetchConflicts()]);
    }
    finally {
      set(refreshing, false);
    }
  }

  watchDebounced(internalTxFixedSignal, () => {
    startPromise(handleConflictFixed());
  }, { debounce: 2000, maxWait: 10000 });

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
    pagination,
    pendingCount,
    setFilter,
    sort,
    totalFound,
  };
});
