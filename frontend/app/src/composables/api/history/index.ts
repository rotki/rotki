import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import { ReportProgress } from '@/types/reports';
import { type AllLocationResponse } from '@/types/location';

export const useHistoryApi = () => {
  const getProgress = async (): Promise<ReportProgress> => {
    const response = await api.instance.get<ActionResult<ReportProgress>>(
      `/history/status`,
      {
        validateStatus: validWithSessionStatus
      }
    );
    const data = handleResponse(response);
    return ReportProgress.parse(data);
  };

  const fetchAssociatedLocations = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(
      '/locations/associated',
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const fetchAllLocations = async (): Promise<AllLocationResponse> => {
    const response = await api.instance.get<ActionResult<AllLocationResponse>>(
      '/locations/all',
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    getProgress,
    fetchAssociatedLocations,
    fetchAllLocations
  };
};
