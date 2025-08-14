import type { ActionResult } from '@rotki/common';
import type { AllLocationResponse } from '@/types/location';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';
import { ReportProgress } from '@/types/reports';

interface UseHistoryApiReturn {
  getProgress: () => Promise<ReportProgress>;
  fetchAssociatedLocations: () => Promise<string[]>;
  fetchAllLocations: () => Promise<AllLocationResponse>;
}

export function useHistoryApi(): UseHistoryApiReturn {
  const getProgress = async (): Promise<ReportProgress> => {
    const response = await api.instance.get<ActionResult<ReportProgress>>(`/history/status`, {
      validateStatus: validWithSessionStatus,
    });
    const data = handleResponse(response);
    return ReportProgress.parse(data);
  };

  const fetchAssociatedLocations = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>('/locations/associated', {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const fetchAllLocations = async (): Promise<AllLocationResponse> => {
    const response = await api.instance.get<ActionResult<AllLocationResponse>>('/locations/all', {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    fetchAllLocations,
    fetchAssociatedLocations,
    getProgress,
  };
}
