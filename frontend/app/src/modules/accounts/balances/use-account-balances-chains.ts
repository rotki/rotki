import type { Ref } from 'vue';
import type { BlockchainAccountData } from '@/types/blockchain/accounts';
import { getGroupId } from '@/utils/blockchain/accounts/utils';

interface AccountWithChains {
  data: BlockchainAccountData;
  chains: string[];
}

interface AccountBalancesChainsReturn {
  getChains: (row: AccountWithChains) => string[];
}

export function useAccountBalancesChains(chainExclusionFilter: Ref<Record<string, string[]>>): AccountBalancesChainsReturn {
  const getChains = (row: AccountWithChains): string[] => {
    const chains = row.chains;
    const excludedChains = get(chainExclusionFilter)[getGroupId(row)];
    return excludedChains ? chains.filter(chain => !excludedChains.includes(chain)) : chains;
  };

  return {
    getChains,
  };
}
