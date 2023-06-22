import { type MaybeRef } from '@vueuse/core';
import { Blockchain } from '@rotki/common/lib/blockchain';
import isEqual from 'lodash/isEqual';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type BlockchainAssetBalances } from '@/types/blockchain/balances';
import {
  type EthDetectedTokensInfo,
  type EvmTokensRecord
} from '@/types/balances';

const noTokens = (): EthDetectedTokensInfo => ({
  tokens: [],
  total: 0,
  timestamp: null
});

type Tokens = Record<string, EvmTokensRecord>;

const defaultTokens = (): Tokens => ({
  [Blockchain.ETH]: {},
  [Blockchain.OPTIMISM]: {},
  [Blockchain.POLYGON_POS]: {}
});

export const useBlockchainTokensStore = defineStore('blockchain/tokens', () => {
  const tokensState: Ref<Tokens> = ref(defaultTokens());

  const shouldRefreshBalances: Ref<boolean> = ref(true);

  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { t } = useI18n();
  const { ethAddresses } = storeToRefs(useEthAccountsStore());
  const { optimismAddresses, polygonAddresses } = storeToRefs(
    useChainsAccountsStore()
  );
  const {
    fetchDetectedTokensTask,
    fetchDetectedTokens: fetchDetectedTokensCaller
  } = useBlockchainBalancesApi();
  const { supportsTransactions } = useSupportedChains();

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

  /**
   * Temporary function to update detected token count on balance refresh
   *
   * @param {Blockchain} chain
   * @param {BlockchainAssetBalances} chainValues
   */
  const updateDetectedTokens = (
    chain: Blockchain,
    chainValues: BlockchainAssetBalances
  ) => {
    const lastUpdateTimestamp = Date.now() / 1000;
    const data: EvmTokensRecord = {};
    for (const address in chainValues) {
      const { assets } = chainValues[address];
      const tokens = Object.keys(assets).filter(
        asset => asset !== Blockchain.ETH.toUpperCase()
      );
      data[address] = { tokens, lastUpdateTimestamp };
    }

    setState(chain, data);
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

  const getEthDetectedTokensInfo = (
    chain: MaybeRef<Blockchain>,
    address: MaybeRef<string | null>
  ): ComputedRef<EthDetectedTokensInfo> =>
    computed(() => {
      const blockchain = get(chain);
      if (!supportsTransactions(blockchain)) {
        return noTokens();
      }
      const detected = get(tokensState)[blockchain];
      const addr = get(address);
      const info = (addr && detected?.[addr]) || null;
      if (!info) {
        return noTokens();
      }

      const tokens = info.tokens
        ? info.tokens.filter(item => !get(isAssetIgnored(item)))
        : [];
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

  const { isTaskRunning } = useTaskStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { balances: ethBalances } = storeToRefs(useEthBalancesStore());
  const { balances: chainBalances } = storeToRefs(useChainBalancesStore());

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

  // todo: this is temporary, to update the detected tokens count
  // todo: remove when BE updates the endpoint for fetching detected tokens
  watch(ethBalances, (balances, oldBalances) => {
    const chain = Blockchain.ETH;
    const chainValues = get(balances)[chain];
    // we're only interested on the eth chain changes
    if (!isEqual(chainValues, get(oldBalances)[chain])) {
      updateDetectedTokens(chain, chainValues);
    }
  });

  // todo: this is temporary, to update the detected tokens count
  // todo: remove when BE updates the endpoint for fetching detected tokens
  watch(chainBalances, (balances, oldBalances) => {
    // did this with a loop and it caused update errors
    const optimism = Blockchain.OPTIMISM;
    const optimismValues = get(balances)[optimism];
    // we're only interested on the optimism chain changes
    if (!isEqual(optimismValues, get(oldBalances)[optimism])) {
      updateDetectedTokens(optimism, optimismValues);
    }

    const polygon = Blockchain.POLYGON_POS;
    const polygonValues = get(balances)[polygon];
    // we're only interested on the polygon chain changes
    if (!isEqual(polygonValues, get(oldBalances)[polygon])) {
      updateDetectedTokens(polygon, polygonValues);
    }
  });

  return {
    shouldRefreshBalances,
    updateDetectedTokens,
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
