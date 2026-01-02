import type { HistoricalAssetBalance, HistoricalBalancesPayload, HistoricalBalancesResponse } from '@/types/balances';
import { api } from '@/modules/api/rotki-api';

interface UseHistoricalBalancesApiReturn {
  fetchHistoricalBalances: (payload: HistoricalBalancesPayload) => Promise<HistoricalBalancesResponse | HistoricalAssetBalance>;
}

export function useHistoricalBalancesApi(): UseHistoricalBalancesApiReturn {
  const fetchHistoricalBalances = async (payload: HistoricalBalancesPayload): Promise<HistoricalBalancesResponse | HistoricalAssetBalance> => api.post<HistoricalBalancesResponse | HistoricalAssetBalance>('/balances/historical', payload);

  return {
    fetchHistoricalBalances,
  };
}
