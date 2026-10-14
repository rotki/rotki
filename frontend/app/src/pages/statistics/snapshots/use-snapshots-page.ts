import type { Message } from '@rotki/common';
import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { LocationQuery } from '@/modules/core/table/route';
import { startPromise } from '@shared/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { applyPaginationDefaults, parseQueryPagination } from '@/modules/core/table/pagination-filter-utils';
import { useSnapshotActions } from '@/modules/dashboard/snapshots/composables/use-snapshot-actions';
import { useSnapshotExport } from '@/modules/dashboard/snapshots/composables/use-snapshot-export';
import { type SnapshotListFilters, type SnapshotListRow, useSnapshotList } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import { parseSnapshotFilters, toSnapshotQuery } from '@/pages/statistics/snapshots/snapshot-query';

type SnapshotActions = ReturnType<typeof useSnapshotActions>;

type SnapshotExport = ReturnType<typeof useSnapshotExport>;

interface UseSnapshotsPageReturn {
  confirmDelete: (timestamp: number) => void;
  emptyDescription: ComputedRef<string>;
  exportSnapshot: SnapshotExport['exportSnapshot'];
  exporting: SnapshotExport['exporting'];
  forceSaving: SnapshotActions['forceSaving'];
  importSnapshot: SnapshotActions['importSnapshot'];
  importing: SnapshotActions['importing'];
  loading: Readonly<Ref<boolean>>;
  modelBalanceFile: SnapshotActions['modelBalanceFile'];
  modelFilters: Ref<SnapshotListFilters>;
  modelImportDialog: Ref<boolean>;
  modelLocationFile: SnapshotActions['modelLocationFile'];
  modelPagination: Ref<TablePaginationData>;
  open: (timestamp: number) => void;
  refresh: () => Promise<void>;
  rows: Readonly<Ref<SnapshotListRow[]>>;
  /**
   * Forces a new snapshot. It refetches every balance, slow and prone to provider rate limits, so
   * the page asks first, in a popover on the button.
   */
  takeSnapshot: SnapshotActions['forceSave'];
}

export function useSnapshotsPage(): UseSnapshotsPageReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = useRoute();
  const itemsPerPage = useItemsPerPage();

  const modelImportDialog = shallowRef<boolean>(false);

  // View state lives in the URL query, so a reload or a back navigation restores it.
  const modelFilters = ref<SnapshotListFilters>({});
  const modelPagination = ref<TablePaginationData>(applyPaginationDefaults(get(itemsPerPage)));

  const { hasSnapshots, loading, refresh, rows } = useSnapshotList(modelFilters);
  const { deleteSnapshot } = useSnapshotApi();
  const { setMessage } = useMessageStore();
  const { show } = useConfirmStore();
  const { forceSave, forceSaving, importing, importSnapshot, modelBalanceFile, modelLocationFile } = useSnapshotActions();
  const { exporting, exportSnapshot } = useSnapshotExport();

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

  return {
    confirmDelete,
    emptyDescription,
    exporting,
    exportSnapshot,
    forceSaving,
    importing,
    importSnapshot,
    loading,
    modelBalanceFile,
    modelFilters,
    modelImportDialog,
    modelLocationFile,
    modelPagination,
    open,
    refresh,
    rows,
    takeSnapshot: forceSave,
  };
}
