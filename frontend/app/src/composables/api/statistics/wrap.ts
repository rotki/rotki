import { api } from '@/services/rotkehlchen-api';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { nonEmptyProperties } from '@/utils/data';
import type { ActionResult } from '@rotki/common';

export interface WrapStatisticsResult {
  ethOnGas: string;
  ethOnGasPerAddress: Record<string, string>;
  gnosisMaxPaymentsByCurrency: Record<string, string>;
  topDaysByNumberOfTransactions: Array<{
    timestamp: number;
    amount: string;
  }>;
  tradesByExchange: Record<string, number>;
  transactionsPerChain: Record<string, number>;
  transactionsPerProtocol: Array<{
    protocol: string;
    transactions: number;
  }>;
}

interface WrapStatisticsApi {
  fetchWrapStatistics: () => Promise<WrapStatisticsResult>;
}

export function useWrapStatisticsApi(): WrapStatisticsApi {
  const fetchWrapStatistics = async (): Promise<WrapStatisticsResult> => {
    const response = await api.instance.post<ActionResult<WrapStatisticsResult>>(
      '/statistics/wrap',
      snakeCaseTransformer(nonEmptyProperties({
        from_timestamp: 1704067200,
        to_timestamp: 1735689599,
      })),
    );

    if (!response?.data?.result) {
      throw new Error('Invalid response format');
    }

    return response.data.result;
  };

  return {
    fetchWrapStatistics,
  };
}
