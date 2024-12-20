import { z } from 'zod';
import { api } from '@/services/rotkehlchen-api';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { nonEmptyProperties } from '@/utils/data';
import type { ActionResult } from '@rotki/common';

export const scoresData = [
  { description: 'Too scared to spend gas (ngmi) 🐣', imageUrl: './assets/images/wrap/wee_wren.png', min: 0, name: 'Wee Wren' },
  { description: 'Repeating successful trades but playing it safer 🦜', imageUrl: './assets/images/wrap/parrot.png', min: 1000, name: 'Parrot' },
  { description: 'Standing out in the crypto pool with bold moves 💅', imageUrl: './assets/images/wrap/flamingo.png', min: 4000, name: 'Flamingo' },
  { description: 'Fearless trader seeking out the juiciest opportunities 💪', imageUrl: './assets/images/wrap/eagle.png', min: 8000, name: 'Defi Eagle' },
  { description: 'Ultimate degen bird, burning through gas like there\'s no tomorrow 🔥', imageUrl: './assets/images/wrap/pelican.png', min: 10000, name: 'Degen Pelican' },
];

export const WrapStatisticsSchema = z.object({
  ethOnGas: NumericString,
  ethOnGasPerAddress: z.record(NumericString),
  gnosisMaxPaymentsByCurrency: z.record(NumericString),
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
