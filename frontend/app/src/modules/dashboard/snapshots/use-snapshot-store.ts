import type { Snapshot } from '@/modules/dashboard/snapshots';
import { toSnapshotPayload } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';

/**
 * Owns snapshot detail I/O for the Snapshot Manager: fetch (with a small
 * per-timestamp cache so prev/next navigation is instant), persist, and delete.
 * The list itself is sourced separately from the net-value series
 * (`use-snapshot-list`); this store backs the detail/editor page.
 */
export const useSnapshotStore = defineStore('snapshots', () => {
  const { deleteSnapshot, getSnapshotData, updateSnapshotData } = useSnapshotApi();

  // Internal, non-reactive cache — callers always receive a fresh fetch result
  // or the cached value; we never render straight off this map.
  const cache = new Map<number, Snapshot>();

  async function fetchSnapshot(timestamp: number, refresh = false): Promise<Snapshot> {
    const cached = cache.get(timestamp);
    if (!refresh && cached)
      return cached;

    const data = await getSnapshotData(timestamp);
    cache.set(timestamp, data);
    return data;
  }

  async function persist(timestamp: number, snapshot: Snapshot): Promise<boolean> {
    const success = await updateSnapshotData(timestamp, toSnapshotPayload(snapshot));
    if (success)
      cache.set(timestamp, snapshot);
    return success;
  }

  async function remove(timestamp: number): Promise<boolean> {
    const success = await deleteSnapshot({ timestamp });
    if (success)
      cache.delete(timestamp);
    return success;
  }

  function invalidate(timestamp?: number): void {
    if (timestamp === undefined)
      cache.clear();
    else
      cache.delete(timestamp);
  }

  return {
    fetchSnapshot,
    invalidate,
    persist,
    remove,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSnapshotStore, import.meta.hot));
