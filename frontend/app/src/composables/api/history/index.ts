import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import { type TradeLocation } from '@/types/history/trade/location';
import { ReportProgress } from '@/types/reports';

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

  const fetchAssociatedLocations = async (): Promise<TradeLocation[]> => {
    const response = await api.instance.get<ActionResult<TradeLocation[]>>(
      '/locations/associated',
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    getProgress,
    fetchAssociatedLocations
  };
};
