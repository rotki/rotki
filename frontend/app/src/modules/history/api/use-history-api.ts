import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/core/api/utils';
import {
  type AllLocationResponse,
  AllLocationResponseSchema,
  type AssociatedLocations,
  AssociatedLocationsSchema,
  type LocationLabel,
  LocationLabelsSchema,
} from '@/modules/core/common/location';
import { ROOT_LOCATION } from '@/modules/locations/use-location-tree-store';
import { ReportProgress } from '@/modules/reports/report-types';

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

  /**
   * The locations the history can be filtered by: those holding data, then their ancestors below
   * the total. A location filter covers its sub-locations, so an ancestor such as Banks selects the
   * data of every bank.
   */
  const fetchAssociatedLocations = async (): Promise<string[]> => {
    const { ancestors, locations } = AssociatedLocationsSchema.parse(await api.get<AssociatedLocations>('/locations/associated'));
    return [...locations, ...ancestors.filter(ancestor => ancestor !== ROOT_LOCATION && !locations.includes(ancestor))];
  };

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
