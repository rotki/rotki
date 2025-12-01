import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE, VALID_WITHOUT_SESSION_STATUS } from '@/modules/api/utils';
import { Snapshot, type SnapshotPayload } from '@/types/snapshots';

interface UseSnapshotApiReturn {
  getSnapshotData: (timestamp: number) => Promise<Snapshot>;
  updateSnapshotData: (timestamp: number, payload: SnapshotPayload) => Promise<boolean>;
  exportSnapshotCSV: ({ path, timestamp }: { path: string; timestamp: number }) => Promise<boolean>;
  downloadSnapshot: (timestamp: number) => Promise<Blob>;
  deleteSnapshot: (payload: { timestamp: number }) => Promise<boolean>;
  importBalancesSnapshot: (balancesSnapshotFile: string, locationDataSnapshotFile: string) => Promise<boolean>;
  uploadBalancesSnapshot: (balancesSnapshotFile: File, locationDataSnapshotFile: File) => Promise<boolean>;
}

export function useSnapshotApi(): UseSnapshotApiReturn {
  const getSnapshotData = async (timestamp: number): Promise<Snapshot> => {
    const response = await api.get<Snapshot>(`/snapshots/${timestamp}`, {
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    });

    return Snapshot.parse(response);
  };

  const updateSnapshotData = async (timestamp: number, payload: SnapshotPayload): Promise<boolean> => api.patch<boolean>(`/snapshots/${timestamp}`, payload);

  const exportSnapshotCSV = async ({ path, timestamp }: { path: string; timestamp: number }): Promise<boolean> => api.get<boolean>(`/snapshots/${timestamp}`, {
    query: {
      action: 'export',
      path,
    },
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  const downloadSnapshot = async (timestamp: number): Promise<Blob> => api.fetchBlob(`/snapshots/${timestamp}`, {
    method: 'GET',
    query: { action: 'download' },
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  const deleteSnapshot = async (payload: { timestamp: number }): Promise<boolean> => api.delete<boolean>('/snapshots', {
    body: payload,
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  const importBalancesSnapshot = async (
    balancesSnapshotFile: string,
    locationDataSnapshotFile: string,
  ): Promise<boolean> => api.put<boolean>(
    '/snapshots',
    {
      balancesSnapshotFile,
      locationDataSnapshotFile,
    },
    {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

  const uploadBalancesSnapshot = async (
    balancesSnapshotFile: File,
    locationDataSnapshotFile: File,
  ): Promise<boolean> => {
    const data = new FormData();
    data.append('balances_snapshot_file', balancesSnapshotFile);
    data.append('location_data_snapshot_file', locationDataSnapshotFile);
    return api.post<boolean>('/snapshots', data);
  };

  return {
    deleteSnapshot,
    downloadSnapshot,
    exportSnapshotCSV,
    getSnapshotData,
    importBalancesSnapshot,
    updateSnapshotData,
    uploadBalancesSnapshot,
  };
}
