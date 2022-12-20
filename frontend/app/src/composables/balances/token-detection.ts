import { type MaybeRef } from '@vueuse/core';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type Ref } from 'vue';
import { useBlockchainBalancesStore } from '@/store/blockchain/balances';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { isTokenChain } from '@/types/blockchain/chains';

export const useTokenDetection = (
  chain: Ref<Blockchain>,
  accountAddress: MaybeRef<string | null> = null
) => {
  const { isTaskRunning } = useTasks();
  const { fetchBlockchainBalances } = useBlockchainBalancesStore();
  const { getEthDetectedTokensInfo, fetchDetectedTokens } =
    useBlockchainTokensStore();

  const detectingTokens = computed<boolean>(() => {
    const address = get(accountAddress);
    return get(
      isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, address ? { address } : {})
    );
  });

  const detectedTokens = getEthDetectedTokensInfo(chain, accountAddress);

  const fetchDetectedTokensAndQueryBalance = async (address: string) => {
    const blockchain = get(chain);
    assert(isTokenChain(blockchain));
    await fetchDetectedTokens(blockchain, address);
    await fetchBlockchainBalances({
      blockchain,
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
