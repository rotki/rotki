import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/core/api/utils';
import { type SolanaStakeAccounts, SolanaStakeAccountsSchema } from '@/modules/staking/staking-types';

interface UseSolanaStakingApiReturn {
  fetchStakeAccounts: () => Promise<SolanaStakeAccounts>;
}

export function useSolanaStakingApi(): UseSolanaStakingApiReturn {
  const fetchStakeAccounts = async (): Promise<SolanaStakeAccounts> => {
    const response = await api.get<SolanaStakeAccounts>('/blockchains/solana/stake/accounts', {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return SolanaStakeAccountsSchema.parse(response);
  };

  return { fetchStakeAccounts };
}
