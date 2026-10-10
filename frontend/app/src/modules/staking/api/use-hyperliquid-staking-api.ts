import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/core/api/utils';
import { type HyperliquidStakingSummaries, HyperliquidStakingSummariesSchema } from '@/modules/staking/staking-types';

interface UseHyperliquidStakingApiReturn {
  fetchStakingSummaries: () => Promise<HyperliquidStakingSummaries>;
}

export function useHyperliquidStakingApi(): UseHyperliquidStakingApiReturn {
  const fetchStakingSummaries = async (): Promise<HyperliquidStakingSummaries> => {
    const response = await api.get<HyperliquidStakingSummaries>('/blockchains/hyperliquid/stake/summary', {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return HyperliquidStakingSummariesSchema.parse(response);
  };

  return { fetchStakingSummaries };
}
