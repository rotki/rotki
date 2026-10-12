import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/core/api/utils';
import {
  type HyperliquidStakingSummaries,
  HyperliquidStakingSummariesSchema,
  type SolanaStakeAccounts,
  SolanaStakeAccountsSchema,
} from '@/modules/staking/staking-types';

interface UseStakingApiReturn {
  fetchHyperliquidStakingSummaries: () => Promise<HyperliquidStakingSummaries>;
  fetchSolanaStakeAccounts: () => Promise<SolanaStakeAccounts>;
}

export function useStakingApi(): UseStakingApiReturn {
  const fetchSolanaStakeAccounts = async (): Promise<SolanaStakeAccounts> => {
    const response = await api.get<SolanaStakeAccounts>('/blockchains/solana/stake/accounts', {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return SolanaStakeAccountsSchema.parse(response);
  };

  const fetchHyperliquidStakingSummaries = async (): Promise<HyperliquidStakingSummaries> => {
    const response = await api.get<HyperliquidStakingSummaries>('/blockchains/hyperliquid/stake/summary', {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return HyperliquidStakingSummariesSchema.parse(response);
  };

  return { fetchHyperliquidStakingSummaries, fetchSolanaStakeAccounts };
}
