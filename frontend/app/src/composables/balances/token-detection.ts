import { type MaybeRef } from '@vueuse/core';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { isTokenChain } from '@/types/blockchain/chains';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';
import { useChainsAccountsStore } from '@/store/blockchain/accounts/chains';

export const useTokenDetection = (
  chain: MaybeRef<Blockchain>,
  accountAddress: MaybeRef<string | null> = null
) => {
  const { isTaskRunning } = useTasks();
  const {
    getEthDetectedTokensInfo,
    fetchDetectedTokens: fetchDetectedTokensCaller
  } = useBlockchainTokensStore();

  const { ethAddresses } = storeToRefs(useEthAccountsStore());
  const { optimismAddresses } = storeToRefs(useChainsAccountsStore());

  const detectingTokens = computed<boolean>(() => {
    const address = get(accountAddress);
    const blockchain = get(chain);
    return get(
      isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
        chain: blockchain,
        ...(address ? { address } : {})
      })
    );
  });

  const detectedTokens = getEthDetectedTokensInfo(chain, accountAddress);

  const fetchDetectedTokens = async (address: string) => {
    const blockchain = get(chain);
    assert(isTokenChain(blockchain));
    await fetchDetectedTokensCaller(blockchain, address);
  };

  const detectTokens = async (addresses: string[] = []) => {
    const address = get(accountAddress);
    assert(address || addresses.length > 0);
    if (address) {
      await fetchDetectedTokens(address);
    } else {
      await Promise.allSettled(addresses.map(fetchDetectedTokens));
    }
  };

  const detectTokensOfAllAddresses = async () => {
    const blockchain = get(chain);
    if (blockchain === Blockchain.OPTIMISM) {
      await detectTokens(get(optimismAddresses));
    } else if (blockchain === Blockchain.ETH) {
      await detectTokens(get(ethAddresses));
    }
  };

  return {
    detectingTokens,
    detectedTokens,
    getEthDetectedTokensInfo,
    detectTokens,
    detectTokensOfAllAddresses
  };
};
