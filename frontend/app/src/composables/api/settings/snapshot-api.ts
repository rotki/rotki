import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithoutSessionStatus,
  validWithSessionAndExternalService,
} from '@/services/utils';
import { Snapshot, type SnapshotPayload } from '@/types/snapshots';

interface UseSnapshotApiReturn {
  getSnapshotData: (timestamp: number) => Promise<Snapshot>;
  updateSnapshotData: (timestamp: number, payload: SnapshotPayload) => Promise<boolean>;
  exportSnapshotCSV: ({ path, timestamp }: { path: string; timestamp: number }) => Promise<boolean>;
  downloadSnapshot: (timestamp: number) => Promise<any>;
  deleteSnapshot: (payload: { timestamp: number }) => Promise<boolean>;
  importBalancesSnapshot: (balancesSnapshotFile: string, locationDataSnapshotFile: string) => Promise<boolean>;
  uploadBalancesSnapshot: (balancesSnapshotFile: File, locationDataSnapshotFile: File) => Promise<boolean>;
}

export function useSnapshotApi(): UseSnapshotApiReturn {
  const getSnapshotData = async (timestamp: number): Promise<Snapshot> => {
    const response = await api.instance.get<ActionResult<Snapshot>>(`/snapshots/${timestamp}`, {
      validateStatus: validWithoutSessionStatus,
    });

    return Snapshot.parse(handleResponse(response));
  };

  const updateSnapshotData = async (timestamp: number, payload: SnapshotPayload): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      `/snapshots/${timestamp}`,
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const exportSnapshotCSV = async ({ path, timestamp }: { path: string; timestamp: number }): Promise<boolean> => {
    const response = await api.instance.get<ActionResult<boolean>>(`/snapshots/${timestamp}`, {
      params: snakeCaseTransformer({
        action: 'export',
        path,
      }),
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  const downloadSnapshot = async (timestamp: number): Promise<any> =>
    api.instance.get<any>(`/snapshots/${timestamp}`, {
      params: snakeCaseTransformer({ action: 'download' }),
      responseType: 'blob',
      validateStatus: validWithoutSessionStatus,
    });

  const deleteSnapshot = async (payload: { timestamp: number }): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/snapshots', {
      data: snakeCaseTransformer(payload),
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  const importBalancesSnapshot = async (
    balancesSnapshotFile: string,
    locationDataSnapshotFile: string,
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/snapshots',
      snakeCaseTransformer({
        balancesSnapshotFile,
        locationDataSnapshotFile,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );
    return handleResponse(response);
  };

  const uploadBalancesSnapshot = async (
    balancesSnapshotFile: File,
    locationDataSnapshotFile: File,
  ): Promise<boolean> => {
    const data = new FormData();
    data.append('balances_snapshot_file', balancesSnapshotFile);
    data.append('location_data_snapshot_file', locationDataSnapshotFile);
    const response = await api.instance.post<ActionResult<boolean>>('/snapshots', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return handleResponse(response);
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
