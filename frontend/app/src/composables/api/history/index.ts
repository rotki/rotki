import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';
import { type AllLocationResponse, type LocationLabel, LocationLabels } from '@/types/location';
import { ReportProgress } from '@/types/reports';

interface UseHistoryApiReturn {
  getProgress: () => Promise<ReportProgress>;
  fetchAssociatedLocations: () => Promise<string[]>;
  fetchAllLocations: () => Promise<AllLocationResponse>;
  fetchLocationLabels: () => Promise<LocationLabel[]>;
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

  const fetchLocationLabels = async (): Promise<LocationLabel[]> => {
    const response = await api.instance.get<ActionResult<LocationLabel[]>>('/locations/labels', {
      validateStatus: validStatus,
    });

    return LocationLabels.parse(handleResponse(response).filter(item => item.locationLabel));
  };

  return {
    fetchAllLocations,
    fetchAssociatedLocations,
    fetchLocationLabels,
    getProgress,
  };
}
