import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import { type AllLocationResponse, AllLocationResponseSchema, type LocationLabel, LocationLabelsSchema } from '@/types/location';
import { ReportProgress } from '@/types/reports';

interface UseHistoryApiReturn {
  getProgress: () => Promise<ReportProgress>;
  fetchAssociatedLocations: () => Promise<string[]>;
  fetchAllLocations: () => Promise<AllLocationResponse>;
  fetchLocationLabels: () => Promise<LocationLabel[]>;
}

export function useHistoryApi(): UseHistoryApiReturn {
  const getProgress = async (): Promise<ReportProgress> => {
    const response = await api.get<ReportProgress>(`/history/status`, {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });
    return ReportProgress.parse(response);
  };

  const fetchAssociatedLocations = async (): Promise<string[]> => api.get<string[]>('/locations/associated');

  const fetchAllLocations = async (): Promise<AllLocationResponse> => {
    const response = await api.get<AllLocationResponse>('/locations/all');
    return AllLocationResponseSchema.parse(response);
  };

  const fetchLocationLabels = async (): Promise<LocationLabel[]> => {
    const response = await api.get<LocationLabel[]>('/locations/labels');

    return LocationLabelsSchema.parse(response.filter(item => item.locationLabel));
  };

  return {
    fetchAllLocations,
    fetchAssociatedLocations,
    fetchLocationLabels,
    getProgress,
  };
}
