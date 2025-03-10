import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { nonEmptyProperties } from '@/utils/data';
import { type ActionResult, NumericString } from '@rotki/common';
import { z } from 'zod';

export const WrapStatisticsSchema = z.object({
  ethOnGas: NumericString,
  ethOnGasPerAddress: z.record(NumericString),
  gnosisMaxPaymentsByCurrency: z.array(
    z.object({
      amount: NumericString,
      symbol: z.string(),
    }),
  ),
  score: z.number(),
  topDaysByNumberOfTransactions: z.array(
    z.object({
      amount: NumericString,
      timestamp: z.number(),
    }),
  ),
  tradesByExchange: z.record(NumericString),
  transactionsPerChain: z.record(NumericString),
  transactionsPerProtocol: z.array(
    z.object({
      protocol: z.string(),
      transactions: NumericString,
    }),
  ),
});

export type WrapStatisticsResult = z.infer<typeof WrapStatisticsSchema>;

interface WrapStatisticsApi {
  fetchWrapStatistics: (params: { end: number; start: number }) => Promise<WrapStatisticsResult>;
}

export function useWrapStatisticsApi(): WrapStatisticsApi {
  const fetchWrapStatistics = async ({ end, start }: { end: number; start: number }): Promise<WrapStatisticsResult> => {
    const response = await api.instance.post<ActionResult<WrapStatisticsResult>>(
      '/statistics/wrap',
      snakeCaseTransformer(nonEmptyProperties({
        from_timestamp: start,
        to_timestamp: end,
      })),
    );

    if (!response?.data?.result) {
      throw new Error('Invalid response format');
    }

    return WrapStatisticsSchema.parse(response.data.result);
  };

  return {
    fetchWrapStatistics,
  };
}
