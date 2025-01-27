import type BigNumber from 'bignumber.js';
import type { ComputedRef, Ref } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { bigNumberSum } from '@/utils/calculation';
import { Zero } from '@rotki/common';

interface UseBalanceQueriesReturn {
  addressTracked: ComputedRef<boolean>;
  availableBalance: ComputedRef<BigNumber>;
  useQueryingBalances: ComputedRef<boolean>;
}

export function useBalanceQueries(connected: Ref<boolean>, connectedAddress: Ref<string | undefined>): UseBalanceQueriesReturn {
  const { useIsTaskRunning } = useTaskStore();
  const { balances } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { addresses } = useAccountAddresses();
  const { getAccountList } = useBlockchainAccountData();

  const queryingBalances = useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
  const queryingBalancesDebounced = refDebounced(queryingBalances, 200);
  const useQueryingBalances = logicOr(queryingBalances, queryingBalancesDebounced);

  const addressTracked = computed<boolean>(() => {
    const connectedVal = get(connected);
    const address = get(connectedAddress);

    if (!connectedVal || !address) {
      return false;
    }

    const accountsAddresses = [...new Set(Object.values(get(addresses)).flat())];
    return connectedVal && accountsAddresses.includes(address);
  });

  const availableBalance = computed<BigNumber>(() => {
    if (!get(addressTracked))
      return Zero;

    const filteredAccounts = getAccountList(get(accounts), get(balances)).filter(account => account.groupId === get(connectedAddress));

    const usdValues = filteredAccounts.map(item => item.usdValue);
    return bigNumberSum(usdValues);
  });

  return {
    addressTracked,
    availableBalance,
    useQueryingBalances,
  };
}
