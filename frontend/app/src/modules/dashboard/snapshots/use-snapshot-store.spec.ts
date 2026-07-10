import type { Snapshot } from '@/modules/dashboard/snapshots';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSnapshotStore } from '@/modules/dashboard/snapshots/use-snapshot-store';

const mockDeleteSnapshot = vi.fn();
const mockGetSnapshotData = vi.fn();
const mockUpdateSnapshotData = vi.fn();

vi.mock('@/modules/settings/api/use-snapshot-api', () => ({
  useSnapshotApi: vi.fn(() => ({
    deleteSnapshot: mockDeleteSnapshot,
    getSnapshotData: mockGetSnapshotData,
    updateSnapshotData: mockUpdateSnapshotData,
  })),
}));

function snapshot(): Snapshot {
  return createMock<Snapshot>({ balancesSnapshot: [], locationDataSnapshot: [] });
}

describe('useSnapshotStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('fetchSnapshot', () => {
    it('should fetch and cache a snapshot on the first request', async () => {
      const data = snapshot();
      mockGetSnapshotData.mockResolvedValue(data);
      const store = useSnapshotStore();

      const result = await store.fetchSnapshot(1000);

      expect(result).toBe(data);
      expect(mockGetSnapshotData).toHaveBeenCalledOnce();
    });

    it('should return the cached snapshot without a second fetch', async () => {
      mockGetSnapshotData.mockResolvedValue(snapshot());
      const store = useSnapshotStore();

      await store.fetchSnapshot(1000);
      await store.fetchSnapshot(1000);

      expect(mockGetSnapshotData).toHaveBeenCalledOnce();
    });

    it('should bypass the cache when refresh is requested', async () => {
      mockGetSnapshotData.mockResolvedValue(snapshot());
      const store = useSnapshotStore();

      await store.fetchSnapshot(1000);
      await store.fetchSnapshot(1000, true);

      expect(mockGetSnapshotData).toHaveBeenCalledTimes(2);
    });
  });

  describe('persist', () => {
    it('should cache the snapshot after a successful update', async () => {
      mockUpdateSnapshotData.mockResolvedValue(true);
      const store = useSnapshotStore();
      const data = snapshot();

      const success = await store.persist(1000, data);
      const fetched = await store.fetchSnapshot(1000);

      expect(success).toBe(true);
      expect(fetched).toBe(data);
      expect(mockGetSnapshotData).not.toHaveBeenCalled();
    });

    it('should not cache the snapshot when the update fails', async () => {
      mockUpdateSnapshotData.mockResolvedValue(false);
      mockGetSnapshotData.mockResolvedValue(snapshot());
      const store = useSnapshotStore();

      const success = await store.persist(1000, snapshot());
      await store.fetchSnapshot(1000);

      expect(success).toBe(false);
      expect(mockGetSnapshotData).toHaveBeenCalledOnce();
    });
  });

  describe('remove', () => {
    it('should evict the snapshot from the cache after a successful delete', async () => {
      mockGetSnapshotData.mockResolvedValue(snapshot());
      mockDeleteSnapshot.mockResolvedValue(true);
      const store = useSnapshotStore();

      await store.fetchSnapshot(1000);
      const success = await store.remove(1000);
      await store.fetchSnapshot(1000);

      expect(success).toBe(true);
      expect(mockGetSnapshotData).toHaveBeenCalledTimes(2);
    });

    it('should keep the cache when the delete fails', async () => {
      mockGetSnapshotData.mockResolvedValue(snapshot());
      mockDeleteSnapshot.mockResolvedValue(false);
      const store = useSnapshotStore();

      await store.fetchSnapshot(1000);
      const success = await store.remove(1000);
      await store.fetchSnapshot(1000);

      expect(success).toBe(false);
      expect(mockGetSnapshotData).toHaveBeenCalledOnce();
    });
  });

  describe('invalidate', () => {
    it('should drop a single timestamp from the cache', async () => {
      mockGetSnapshotData.mockResolvedValue(snapshot());
      const store = useSnapshotStore();

      await store.fetchSnapshot(1000);
      store.invalidate(1000);
      await store.fetchSnapshot(1000);

      expect(mockGetSnapshotData).toHaveBeenCalledTimes(2);
    });

    it('should clear the entire cache when no timestamp is given', async () => {
      mockGetSnapshotData.mockResolvedValue(snapshot());
      const store = useSnapshotStore();

      await store.fetchSnapshot(1000);
      await store.fetchSnapshot(2000);
      store.invalidate();
      await store.fetchSnapshot(1000);
      await store.fetchSnapshot(2000);

      expect(mockGetSnapshotData).toHaveBeenCalledTimes(4);
    });
  });
});
