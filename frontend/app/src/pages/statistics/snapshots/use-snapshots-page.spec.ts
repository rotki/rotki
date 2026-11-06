import type { ComputedRef, Ref } from 'vue';
import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSnapshotsPage } from './use-snapshots-page';

const ITEMS_PER_PAGE = 10;

const {
  deleteSnapshot,
  exportSnapshot,
  forceSave,
  hasSnapshotsState,
  pushMock,
  refresh,
  replaceMock,
  routeQuery,
  rowsState,
} = vi.hoisted(() => {
  const hasSnapshotsState = { current: true };
  const routeQuery: { current: Record<string, string> } = { current: {} };
  const rowsState: { current: SnapshotListRow[] } = { current: [] };

  return {
    deleteSnapshot: vi.fn(async (): Promise<boolean> => true),
    exportSnapshot: vi.fn(async (): Promise<boolean> => true),
    forceSave: vi.fn(async (): Promise<void> => {}),
    hasSnapshotsState,
    pushMock: vi.fn(async (): Promise<void> => {}),
    refresh: vi.fn(async (): Promise<void> => {}),
    replaceMock: vi.fn(async (): Promise<void> => {}),
    routeQuery,
    rowsState,
  };
});

vi.mock('vue-router', async () => {
  const { computed } = await import('vue');
  return {
    useRoute: (): ComputedRef<{ query: Record<string, string> }> => computed(() => ({ query: routeQuery.current })),
    useRouter: (): { push: typeof pushMock; replace: typeof replaceMock } => ({ push: pushMock, replace: replaceMock }),
  };
});

vi.mock('@/modules/session/use-items-per-page', async () => {
  const { shallowRef } = await import('vue');
  return { useItemsPerPage: (): Ref<number> => shallowRef(ITEMS_PER_PAGE) };
});

vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-list', async () => {
  const { computed, shallowRef } = await import('vue');
  return {
    useSnapshotList: (): Record<string, unknown> => ({
      hasSnapshots: computed(() => hasSnapshotsState.current),
      loading: shallowRef(false),
      refresh,
      rows: computed(() => rowsState.current),
    }),
  };
});

vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-actions', async () => {
  const { shallowRef } = await import('vue');
  return {
    useSnapshotActions: (): Record<string, unknown> => ({
      forceSave,
      forceSaving: shallowRef(false),
      importSnapshot: vi.fn(),
      importing: shallowRef(false),
      modelBalanceFile: shallowRef(undefined),
      modelImportFailure: shallowRef(undefined),
      modelLocationFile: shallowRef(undefined),
    }),
  };
});

vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-export', async () => {
  const { shallowRef } = await import('vue');
  return {
    useSnapshotExport: (): Record<string, unknown> => ({ exporting: shallowRef(undefined), exportSnapshot }),
  };
});

vi.mock('@/modules/settings/api/use-snapshot-api', () => ({
  useSnapshotApi: (): { deleteSnapshot: typeof deleteSnapshot } => ({ deleteSnapshot }),
}));

describe('pages/statistics/snapshots/useSnapshotsPage', () => {
  function setup(): ReturnType<typeof useSnapshotsPage> {
    return withSetup(() => useSnapshotsPage()).result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    hasSnapshotsState.current = true;
    routeQuery.current = {};
    rowsState.current = [];
    deleteSnapshot.mockResolvedValue(true);
  });

  describe('restoring the view-state from the URL', () => {
    it('should read the date range out of the query', async () => {
      routeQuery.current = { from: '100', to: '200' };

      const { modelFilters } = setup();
      await flushPromises();

      expect(get(modelFilters)).toEqual({ fromTimestamp: 100, toTimestamp: 200 });
    });

    it('should start unfiltered when the query is bare', async () => {
      const { modelFilters } = setup();
      await flushPromises();

      expect(get(modelFilters)).toEqual({ fromTimestamp: undefined, toTimestamp: undefined });
    });
  });

  describe('mirroring the view-state back into the URL', () => {
    it('should replace rather than push, so the range does not fill the history', async () => {
      const { modelFilters } = setup();
      await flushPromises();

      set(modelFilters, { fromTimestamp: 100, toTimestamp: 200 });
      await flushPromises();

      expect(replaceMock).toHaveBeenCalledWith({ query: { from: 100, to: 200 } });
      expect(pushMock).not.toHaveBeenCalled();
    });

    it('should follow a page change', async () => {
      const { modelPagination } = setup();
      await flushPromises();

      set(modelPagination, { ...get(modelPagination), page: 3 });
      await flushPromises();

      expect(replaceMock).toHaveBeenCalledWith({ query: { page: 3 } });
    });

    it('should not write anything on mount alone', async () => {
      setup();
      await flushPromises();

      expect(replaceMock).not.toHaveBeenCalled();
    });
  });

  describe('the empty message', () => {
    it('should blame the filter when the account does have snapshots', async () => {
      hasSnapshotsState.current = true;

      const { emptyDescription } = setup();
      await flushPromises();

      expect(get(emptyDescription)).toBe('dashboard.snapshot.list.empty_filtered');
    });

    it('should say the account is empty when it has none at all', async () => {
      hasSnapshotsState.current = false;

      const { emptyDescription } = setup();
      await flushPromises();

      expect(get(emptyDescription)).toBe('dashboard.snapshot.list.empty');
    });
  });

  it('should export a row straight away', async () => {
    const { exportSnapshot: exportRow } = setup();
    await flushPromises();

    await exportRow(200);

    expect(exportSnapshot).toHaveBeenCalledWith(200);
  });

  it('should open a snapshot detail page', async () => {
    const { open } = setup();
    await flushPromises();

    open(1234);

    expect(pushMock).toHaveBeenCalledWith('/statistics/snapshots/1234');
  });

  describe('deleting a snapshot the row already confirmed', () => {
    it('should delete it and re-read the list, so the row goes, without a failure', async () => {
      const { deleteFailure, deleteSnapshotAt } = setup();
      await flushPromises();

      await deleteSnapshotAt(100);

      expect(deleteSnapshot).toHaveBeenCalledWith({ timestamp: 100 });
      expect(refresh).toHaveBeenCalledTimes(1);
      expect(get(deleteFailure)).toBeUndefined();
    });

    it('should keep a refused delete as a failure without refreshing', async () => {
      deleteSnapshot.mockResolvedValue(false);
      const { deleteFailure, deleteSnapshotAt } = setup();
      await flushPromises();

      await deleteSnapshotAt(100);

      expect(refresh).not.toHaveBeenCalled();
      expect(get(deleteFailure)).toEqual({ failure: 'dashboard.snapshot.delete.message.failure', title: 'dashboard.snapshot.delete.message.title' });
    });

    it('should keep a thrown error as the failure rather than rejecting', async () => {
      const error = new Error('backend said no');
      deleteSnapshot.mockRejectedValue(error);
      const { deleteFailure, deleteSnapshotAt } = setup();
      await flushPromises();

      await expect(deleteSnapshotAt(100)).resolves.toBeUndefined();

      expect(get(deleteFailure)).toEqual({ failure: error, title: 'dashboard.snapshot.delete.message.title' });
      expect(refresh).not.toHaveBeenCalled();
    });

    it('should drop the last failure once a later delete succeeds', async () => {
      deleteSnapshot.mockRejectedValueOnce(new Error('backend said no'));
      const { deleteFailure, deleteSnapshotAt } = setup();
      await flushPromises();

      await deleteSnapshotAt(100);
      await deleteSnapshotAt(100);

      expect(get(deleteFailure)).toBeUndefined();
    });
  });

  it('should force-save when asked to take a snapshot', async () => {
    const { takeSnapshot } = setup();
    await flushPromises();

    await takeSnapshot();

    expect(forceSave).toHaveBeenCalledTimes(1);
  });
});
