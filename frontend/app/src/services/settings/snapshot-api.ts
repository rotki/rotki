import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithoutSessionStatus,
  validWithSessionAndExternalService
} from '@/services/utils';
import { Snapshot, SnapshotPayload } from '@/types/snapshots';

export const useSnapshotApi = () => {
  const getSnapshotData = async (timestamp: number): Promise<Snapshot> => {
    const response = await api.instance.get<ActionResult<Snapshot>>(
      `/snapshots/${timestamp}`,
      {
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return Snapshot.parse(handleResponse(response));
  };

  const updateSnapshotData = async (
    timestamp: number,
    payload: SnapshotPayload
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      `/snapshots/${timestamp}`,
      axiosSnakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  };

  const exportSnapshotCSV = async ({
    path,
    timestamp
  }: {
    path: string;
    timestamp: number;
  }): Promise<boolean> => {
    const response = await api.instance.get<ActionResult<boolean>>(
      `/snapshots/${timestamp}`,
      {
        params: axiosSnakeCaseTransformer({
          path,
          action: 'export'
        }),
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  };

  const downloadSnapshot = async (timestamp: number): Promise<any> => {
    return api.instance.get<any>(`/snapshots/${timestamp}`, {
      params: axiosSnakeCaseTransformer({ action: 'download' }),
      validateStatus: validWithoutSessionStatus,
      responseType: 'arraybuffer'
    });
  };

  const deleteSnapshot = async (payload: {
    timestamp: number;
  }): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/snapshots',
      {
        data: axiosSnakeCaseTransformer(payload),
        validateStatus: validWithoutSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  };

  const importBalancesSnapshot = async (
    balancesSnapshotFile: string,
    locationDataSnapshotFile: string
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/snapshots',
      axiosSnakeCaseTransformer({
        balancesSnapshotFile,
        locationDataSnapshotFile
      }),
      {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  };

  const uploadBalancesSnapshot = async (
    balancesSnapshotFile: File,
    locationDataSnapshotFile: File
  ): Promise<boolean> => {
    const data = new FormData();
    data.append('balances_snapshot_file', balancesSnapshotFile);
    data.append('location_data_snapshot_file', locationDataSnapshotFile);
    const response = await api.instance.post<ActionResult<boolean>>(
      '/snapshots',
      data,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return handleResponse(response);
  };

  return {
    getSnapshotData,
    updateSnapshotData,
    exportSnapshotCSV,
    downloadSnapshot,
    deleteSnapshot,
    importBalancesSnapshot,
    uploadBalancesSnapshot
  };
};
