import { NumericString } from '@rotki/common';
import { z } from 'zod/v4';
import { api } from '@/modules/api/rotki-api';

export const WrapStatisticsSchema = z.object({
  ethOnGas: NumericString,
  ethOnGasPerAddress: z.record(z.string(), NumericString),
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
  tradesByExchange: z.record(z.string(), NumericString),
  transactionsPerChain: z.record(z.string(), NumericString),
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
    const response = await api.post<WrapStatisticsResult>(
      '/statistics/events',
      {
        fromTimestamp: start,
        toTimestamp: end,
      },
      {
        filterEmptyProperties: true,
      },
    );

    return WrapStatisticsSchema.parse(response);
  };

  return {
    fetchWrapStatistics,
  };
}
