import type { VueWrapper } from '@vue/test-utils';
import type { ComputedRef, Ref } from 'vue';
import type { SnapshotListRow } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';
import { bigNumberify } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSnapshotsPage } from './use-snapshots-page';

const ITEMS_PER_PAGE = 10;

const {
  confirmCallbacks,
  deleteSnapshot,
  forceSave,
  hasSnapshotsState,
  pushMock,
  refresh,
  replaceMock,
  routeQuery,
  rowsState,
  setMessage,
  show,
} = vi.hoisted(() => {
  const confirmCallbacks: (() => Promise<void> | void)[] = [];
  const hasSnapshotsState = { current: true };
  const routeQuery: { current: Record<string, string> } = { current: {} };
  const rowsState: { current: SnapshotListRow[] } = { current: [] };

  return {
    confirmCallbacks,
    deleteSnapshot: vi.fn(async (): Promise<boolean> => true),
    forceSave: vi.fn(async (): Promise<void> => {}),
    hasSnapshotsState,
    pushMock: vi.fn(async (): Promise<void> => {}),
    refresh: vi.fn(async (): Promise<void> => {}),
    replaceMock: vi.fn(async (): Promise<void> => {}),
    routeQuery,
    rowsState,
    setMessage: vi.fn(),
    show: vi.fn((_options: unknown, onConfirm: () => Promise<void> | void) => {
      confirmCallbacks.push(onConfirm);
    }),
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
      modelLocationFile: shallowRef(undefined),
    }),
  };
});

vi.mock('@/modules/settings/api/use-snapshot-api', () => ({
  useSnapshotApi: (): { deleteSnapshot: typeof deleteSnapshot } => ({ deleteSnapshot }),
}));

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): { setMessage: typeof setMessage } => ({ setMessage }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { show: typeof show } => ({ show }),
}));

function row(timestamp: number, usdValue: number): SnapshotListRow {
  return { timestamp, usdValue: bigNumberify(usdValue) };
}

describe('pages/statistics/snapshots/useSnapshotsPage', () => {
  // The composable installs a watcher that writes the URL, so a leftover harness would keep
  // replacing the query during a later test.
  const mounted: VueWrapper[] = [];

  function setup(): ReturnType<typeof useSnapshotsPage> {
    const { result, wrapper } = withSetup(() => useSnapshotsPage());
    mounted.push(wrapper);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    confirmCallbacks.length = 0;
    hasSnapshotsState.current = true;
    routeQuery.current = {};
    rowsState.current = [];
    deleteSnapshot.mockResolvedValue(true);
  });

  afterEach(() => {
    while (mounted.length > 0)
      mounted.pop()?.unmount();
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

  describe('the export dialog', () => {
    it('should open on the chosen snapshot and carry its stored value', async () => {
      rowsState.current = [row(100, 500), row(200, 900)];

      const { modelExportDialog, openExport, selectedBalance, selectedTimestamp } = setup();
      await flushPromises();

      openExport(200);

      expect(get(modelExportDialog)).toBe(true);
      expect(get(selectedTimestamp)).toBe(200);
      expect(get(selectedBalance).toNumber()).toBe(900);
    });

    it('should fall back to zero when the chosen snapshot is not in the current page', async () => {
      rowsState.current = [row(100, 500)];

      const { openExport, selectedBalance } = setup();
      await flushPromises();

      openExport(999);

      expect(get(selectedBalance).toNumber()).toBe(0);
    });
  });

  it('should open a snapshot detail page', async () => {
    const { open } = setup();
    await flushPromises();

    open(1234);

    expect(pushMock).toHaveBeenCalledWith('/statistics/snapshots/1234');
  });

  describe('deleting a snapshot', () => {
    it('should ask first and delete nothing until it is confirmed', async () => {
      const { confirmDelete } = setup();
      await flushPromises();

      confirmDelete(100);

      expect(show).toHaveBeenCalledTimes(1);
      expect(deleteSnapshot).not.toHaveBeenCalled();
    });

    it('should delete, refresh and report success once confirmed', async () => {
      const { confirmDelete } = setup();
      await flushPromises();

      confirmDelete(100);
      await confirmCallbacks[0]();

      expect(deleteSnapshot).toHaveBeenCalledWith({ timestamp: 100 });
      expect(refresh).toHaveBeenCalledTimes(1);
      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: true }));
    });

    it('should report a refused delete without refreshing', async () => {
      deleteSnapshot.mockResolvedValue(false);
      const { confirmDelete } = setup();
      await flushPromises();

      confirmDelete(100);
      await confirmCallbacks[0]();

      expect(refresh).not.toHaveBeenCalled();
      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({ success: false }));
    });

    it('should report a thrown error as a message rather than rejecting', async () => {
      deleteSnapshot.mockRejectedValue(new Error('backend said no'));
      const { confirmDelete } = setup();
      await flushPromises();

      confirmDelete(100);
      await expect(confirmCallbacks[0]()).resolves.toBeUndefined();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({
        description: 'backend said no',
        success: false,
      }));
      expect(refresh).not.toHaveBeenCalled();
    });
  });

  describe('taking a snapshot', () => {
    it('should ask first, because a force-save refetches every balance', async () => {
      const { confirmTakeSnapshot } = setup();
      await flushPromises();

      confirmTakeSnapshot();

      expect(show).toHaveBeenCalledTimes(1);
      expect(forceSave).not.toHaveBeenCalled();
    });

    it('should force-save once confirmed', async () => {
      const { confirmTakeSnapshot } = setup();
      await flushPromises();

      confirmTakeSnapshot();
      await confirmCallbacks[0]();

      expect(forceSave).toHaveBeenCalledTimes(1);
    });
  });
});
