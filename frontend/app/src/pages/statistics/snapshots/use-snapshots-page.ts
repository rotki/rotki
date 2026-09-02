import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { LocationQuery } from '@/modules/core/table/route';
import { type BigNumber, type Message, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { applyPaginationDefaults, parseQueryPagination } from '@/modules/core/table/pagination-filter-utils';
import { useSnapshotActions } from '@/modules/dashboard/snapshots/composables/use-snapshot-actions';
import { type SnapshotListFilters, type SnapshotListRow, useSnapshotList } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import { parseSnapshotFilters, toSnapshotQuery } from '@/pages/statistics/snapshots/snapshot-query';

type SnapshotActions = ReturnType<typeof useSnapshotActions>;

interface UseSnapshotsPageReturn {
  confirmDelete: (timestamp: number) => void;
  confirmTakeSnapshot: () => void;
  emptyDescription: ComputedRef<string>;
  forceSaving: SnapshotActions['forceSaving'];
  importSnapshot: SnapshotActions['importSnapshot'];
  importing: SnapshotActions['importing'];
  loading: Readonly<Ref<boolean>>;
  modelBalanceFile: SnapshotActions['modelBalanceFile'];
  modelExportDialog: Ref<boolean>;
  modelFilters: Ref<SnapshotListFilters>;
  modelImportDialog: Ref<boolean>;
  modelLocationFile: SnapshotActions['modelLocationFile'];
  modelPagination: Ref<TablePaginationData>;
  open: (timestamp: number) => void;
  openExport: (timestamp: number) => void;
  refresh: () => Promise<void>;
  rows: Readonly<Ref<SnapshotListRow[]>>;
  selectedBalance: ComputedRef<BigNumber>;
  selectedTimestamp: Readonly<Ref<number>>;
}

export function useSnapshotsPage(): UseSnapshotsPageReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = useRoute();
  const itemsPerPage = useItemsPerPage();

  const modelExportDialog = shallowRef<boolean>(false);
  const modelImportDialog = shallowRef<boolean>(false);
  const selectedTimestamp = shallowRef<number>(0);

  // View state lives in the URL query, so a reload or a back navigation restores it.
  const modelFilters = ref<SnapshotListFilters>({});
  const modelPagination = ref<TablePaginationData>(applyPaginationDefaults(get(itemsPerPage)));

  const { hasSnapshots, loading, refresh, rows } = useSnapshotList(modelFilters);
  const { deleteSnapshot } = useSnapshotApi();
  const { setMessage } = useMessageStore();
  const { show } = useConfirmStore();
  const { forceSave, forceSaving, importing, importSnapshot, modelBalanceFile, modelLocationFile } = useSnapshotActions();

  function readQuery(query: LocationQuery): void {
    set(modelFilters, parseSnapshotFilters(query));
    set(modelPagination, parseQueryPagination(query, get(modelPagination)));
  }

  /** Mirrors the view-state back into the URL query (replace: no history spam). */
  function writeQuery(): void {
    startPromise(router.replace({ query: toSnapshotQuery(get(modelFilters), get(modelPagination), get(itemsPerPage)) }));
  }

  readQuery(get(route).query);

  watch([
    (): number | undefined => get(modelFilters).fromTimestamp,
    (): number | undefined => get(modelFilters).toTimestamp,
    (): number => get(modelPagination).page,
    (): number => get(modelPagination).limit,
  ], writeQuery);

  // Tells a genuinely empty account apart from a range filter that excludes everything.
  const emptyDescription = computed<string>(() => get(hasSnapshots)
    ? t('dashboard.snapshot.list.empty_filtered')
    : t('dashboard.snapshot.list.empty'));

  function open(timestamp: number): void {
    startPromise(router.push(`/statistics/snapshots/${timestamp}`));
  }

  // The stored USD net worth: the export dialog converts it at the historic rate itself, lazily.
  const selectedRow = computed<SnapshotListRow | undefined>(() =>
    get(rows).find(item => item.timestamp === get(selectedTimestamp)));
  const selectedBalance = computed<BigNumber>(() => get(selectedRow)?.usdValue ?? Zero);

  function openExport(timestamp: number): void {
    set(selectedTimestamp, timestamp);
    set(modelExportDialog, true);
  }

  async function performDelete(timestamp: number): Promise<void> {
    let message: Message;
    try {
      const success = await deleteSnapshot({ timestamp });
      message = {
        description: success
          ? t('dashboard.snapshot.delete.message.success')
          : t('dashboard.snapshot.delete.message.failure'),
        success,
        title: t('dashboard.snapshot.delete.message.title'),
      };
      if (success)
        await refresh();
    }
    catch (error: unknown) {
      message = {
        description: getErrorMessage(error),
        success: false,
        title: t('dashboard.snapshot.delete.message.title'),
      };
    }
    setMessage(message);
  }

  function confirmDelete(timestamp: number): void {
    show(
      {
        message: t('dashboard.snapshot.delete.dialog.message'),
        title: t('dashboard.snapshot.delete.dialog.title'),
      },
      async () => performDelete(timestamp),
    );
  }

  /**
   * Asks for confirmation, then forces a new snapshot to be taken.
   *
   * @remarks
   * The save refetches every balance, which is slow and prone to provider rate limits, so it is
   * never started straight off a click.
   */
  function confirmTakeSnapshot(): void {
    show(
      {
        message: t('dashboard.snapshot.list.take_snapshot_confirm.message'),
        title: t('dashboard.snapshot.list.take_snapshot_confirm.title'),
      },
      async () => forceSave(),
    );
  }

  return {
    confirmDelete,
    confirmTakeSnapshot,
    emptyDescription,
    forceSaving,
    importing,
    importSnapshot,
    loading,
    modelBalanceFile,
    modelExportDialog,
    modelFilters,
    modelImportDialog,
    modelLocationFile,
    modelPagination,
    open,
    openExport,
    refresh,
    rows,
    selectedBalance,
    selectedTimestamp: readonly(selectedTimestamp),
  };
}
