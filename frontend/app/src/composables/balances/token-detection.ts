import { Blockchain } from '@rotki/common/lib/blockchain';
import { MaybeRef } from '@vueuse/core';
import { useBlockchainBalancesStore } from '@/store/blockchain/balances';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';

export const useTokenDetection = (
  accountAddress: MaybeRef<string | null> = null
) => {
  const { isTaskRunning } = useTasks();
  const { fetchBlockchainBalances } = useBlockchainBalancesStore();
  const { getEthDetectedTokensInfo, fetchDetectedTokens } =
    useBlockchainTokensStore();

  const detectingTokens = computed<boolean>(() => {
    const address = get(accountAddress);
    return get(
      isTaskRunning(
        TaskType.FETCH_DETECTED_TOKENS,
        address ? { address: address } : {}
      )
    );
  });

  const detectedTokens = computed(() => {
    return get(getEthDetectedTokensInfo(accountAddress));
  });

  const fetchDetectedTokensAndQueryBalance = async (address: string) => {
    await fetchDetectedTokens(address);
    await fetchBlockchainBalances({
      blockchain: Blockchain.ETH,
      ignoreCache: true
    });
  };

  const detectTokensAndQueryBalances = async (addresses: string[] = []) => {
    const address = get(accountAddress);
    assert(address || addresses.length > 0);
    if (address) {
      await fetchDetectedTokensAndQueryBalance(address);
    } else {
      await Promise.allSettled(
        addresses.map(fetchDetectedTokensAndQueryBalance)
      );
    }
  };

  return {
    detectingTokens,
    detectedTokens,
    getEthDetectedTokensInfo,
    detectTokensAndQueryBalances
  };
};
