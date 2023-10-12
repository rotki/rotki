import { type MaybeRef } from '@vueuse/core';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { isEqual } from 'lodash-es';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import {
  type EthDetectedTokensInfo,
  type EvmTokensRecord
} from '@/types/balances';
import { type BlockchainAssetBalances } from '@/types/blockchain/balances';
import { isRestChain } from '@/types/blockchain/chains';

const noTokens = (): EthDetectedTokensInfo => ({
  tokens: [],
  total: 0,
  timestamp: null
});

type Tokens = Record<string, EvmTokensRecord>;

const defaultTokens = (): Tokens => ({
  [Blockchain.ETH]: {},
  [Blockchain.OPTIMISM]: {},
  [Blockchain.POLYGON_POS]: {},
  [Blockchain.ARBITRUM_ONE]: {},
  [Blockchain.BASE]: {},
  [Blockchain.GNOSIS]: {}
});

export const useBlockchainTokensStore = defineStore('blockchain/tokens', () => {
  const tokensState: Ref<Tokens> = ref(defaultTokens());

  const shouldRefreshBalances: Ref<boolean> = ref(true);

  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { t } = useI18n();
  const { ethAddresses } = storeToRefs(useEthAccountsStore());
  const {
    optimismAddresses,
    polygonAddresses,
    arbitrumAddresses,
    baseAddresses,
    gnosisAddresses
  } = storeToRefs(useChainsAccountsStore());
  const {
    fetchDetectedTokensTask,
    fetchDetectedTokens: fetchDetectedTokensCaller
  } = useBlockchainBalancesApi();
  const { supportsTransactions } = useSupportedChains();

  const { balances: ethBalances } = storeToRefs(useEthBalancesStore());
  const { balances: chainBalances } = storeToRefs(useChainBalancesStore());

  const fetchDetected = async (
    chain: Blockchain,
    addresses: string[]
  ): Promise<void> => {
    await Promise.allSettled(
      addresses.map(address => fetchDetectedTokens(chain, address))
    );
  };

  const setState = (chain: Blockchain, data: EvmTokensRecord) => {
    const tokensVal = { ...get(tokensState) };
    set(tokensState, {
      ...tokensVal,
      [chain]: {
        ...tokensVal[chain],
        ...data
      }
    });
  };

  const fetchDetectedTokens = async (
    chain: Blockchain,
    address: string | null = null
  ) => {
    try {
      if (address) {
        const { awaitTask } = useTaskStore();
        const taskType = TaskType.FETCH_DETECTED_TOKENS;

        const { taskId } = await fetchDetectedTokensTask(chain, [address]);

        const taskMeta = {
          title: t('actions.balances.detect_tokens.task.title'),
          description: t('actions.balances.detect_tokens.task.description', {
            address,
            chain
          }),
          address,
          chain
        };

        const { result } = await awaitTask<EvmTokensRecord, TaskMeta>(
          taskId,
          taskType,
          taskMeta,
          true
        );

        setState(chain, result);
      } else {
        const result = await fetchDetectedTokensCaller(chain, null);
        setState(chain, result);
      }
    } catch (e) {
      logger.error(e);
    }
  };

  const getTokens = (balances: BlockchainAssetBalances, address: string) => {
    const assets = balances[address]?.assets ?? [];
    return Object.keys(assets).filter(id => !get(isAssetIgnored(id)));
  };

  const getEthDetectedTokensInfo = (
    chain: MaybeRef<Blockchain>,
    address: MaybeRef<string | null>
  ): ComputedRef<EthDetectedTokensInfo> =>
    computed(() => {
      const blockchain = get(chain);
      if (!supportsTransactions(blockchain)) {
        return noTokens();
      }
      const state = get(tokensState);
      const detected: EvmTokensRecord | undefined = state[blockchain];
      const addr = get(address);

      if (!addr) {
        return noTokens();
      }

      const info = detected?.[addr];
      if (!info) {
        return noTokens();
      }

      let tokens: string[];
      if (blockchain === Blockchain.ETH) {
        tokens = getTokens(get(ethBalances)[blockchain], addr);
      } else if (isRestChain(blockchain)) {
        tokens = getTokens(get(chainBalances)[blockchain], addr);
      } else {
        tokens = info.tokens?.filter(id => !get(isAssetIgnored(id))) ?? [];
      }

      return {
        tokens,
        total: tokens.length,
        timestamp: info.lastUpdateTimestamp || null
      };
    });

  watch(ethAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev)) {
      return;
    }
    await fetchDetectedTokens(Blockchain.ETH);
  });

  watch(optimismAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev)) {
      return;
    }
    await fetchDetectedTokens(Blockchain.OPTIMISM);
  });

  watch(polygonAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev)) {
      return;
    }
    await fetchDetectedTokens(Blockchain.POLYGON_POS);
  });

  watch(arbitrumAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev)) {
      return;
    }
    await fetchDetectedTokens(Blockchain.ARBITRUM_ONE);
  });

  watch(baseAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev)) {
      return;
    }
    await fetchDetectedTokens(Blockchain.BASE);
  });

  watch(gnosisAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev)) {
      return;
    }
    await fetchDetectedTokens(Blockchain.GNOSIS);
  });

  const { isTaskRunning } = useTaskStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();

  const isEthDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
    chain: Blockchain.ETH
  });

  watch(isEthDetecting, async (isDetecting, wasDetecting) => {
    if (get(shouldRefreshBalances) && wasDetecting && !isDetecting) {
      await fetchBlockchainBalances({
        blockchain: Blockchain.ETH,
        ignoreCache: true
      });
    }
  });

  const isOptimismDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
    chain: Blockchain.OPTIMISM
  });
  watch(isOptimismDetecting, async (isDetecting, wasDetecting) => {
    if (get(shouldRefreshBalances) && wasDetecting && !isDetecting) {
      await fetchBlockchainBalances({
        blockchain: Blockchain.OPTIMISM,
        ignoreCache: true
      });
    }
  });

  const isPolygonDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
    chain: Blockchain.POLYGON_POS
  });
  watch(isPolygonDetecting, async (isDetecting, wasDetecting) => {
    if (get(shouldRefreshBalances) && wasDetecting && !isDetecting) {
      await fetchBlockchainBalances({
        blockchain: Blockchain.POLYGON_POS,
        ignoreCache: true
      });
    }
  });

  const isArbitrumDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
    chain: Blockchain.ARBITRUM_ONE
  });
  watch(isArbitrumDetecting, async (isDetecting, wasDetecting) => {
    if (get(shouldRefreshBalances) && wasDetecting && !isDetecting) {
      await fetchBlockchainBalances({
        blockchain: Blockchain.ARBITRUM_ONE,
        ignoreCache: true
      });
    }
  });

  const isBaseDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
    chain: Blockchain.BASE
  });
  watch(isBaseDetecting, async (isDetecting, wasDetecting) => {
    if (get(shouldRefreshBalances) && wasDetecting && !isDetecting) {
      await fetchBlockchainBalances({
        blockchain: Blockchain.BASE,
        ignoreCache: true
      });
    }
  });

  const isGnosisDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
    chain: Blockchain.GNOSIS
  });
  watch(isGnosisDetecting, async (isDetecting, wasDetecting) => {
    if (get(shouldRefreshBalances) && wasDetecting && !isDetecting) {
      await fetchBlockchainBalances({
        blockchain: Blockchain.GNOSIS,
        ignoreCache: true
      });
    }
  });

  return {
    shouldRefreshBalances,
    fetchDetected,
    fetchDetectedTokens,
    getEthDetectedTokensInfo
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBlockchainTokensStore, import.meta.hot)
  );
}
