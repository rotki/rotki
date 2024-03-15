import { Blockchain } from '@rotki/common/lib/blockchain';
import { isEqual } from 'lodash-es';
import { TaskType } from '@/types/task-type';
import { isRestChain } from '@/types/blockchain/chains';
import type { MaybeRef } from '@vueuse/core';
import type { TaskMeta } from '@/types/task';
import type {
  EthDetectedTokensInfo,
  EvmTokensRecord,
} from '@/types/balances';
import type { BlockchainAssetBalances } from '@/types/blockchain/balances';

function noTokens(): EthDetectedTokensInfo {
  return {
    tokens: [],
    total: 0,
    timestamp: null,
  };
}

type Tokens = Record<string, EvmTokensRecord>;

function defaultTokens(): Tokens {
  return {
    [Blockchain.ETH]: {},
    [Blockchain.OPTIMISM]: {},
    [Blockchain.POLYGON_POS]: {},
    [Blockchain.ARBITRUM_ONE]: {},
    [Blockchain.BASE]: {},
    [Blockchain.GNOSIS]: {},
    [Blockchain.SCROLL]: {},
  };
}

export const useBlockchainTokensStore = defineStore('blockchain/tokens', () => {
  const tokensState: Ref<Tokens> = ref(defaultTokens());

  const massDetecting: Ref<Blockchain | 'all' | undefined> = ref();

  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { t } = useI18n();
  const { ethAddresses } = storeToRefs(useEthAccountsStore());
  const {
    optimismAddresses,
    polygonAddresses,
    arbitrumAddresses,
    baseAddresses,
    gnosisAddresses,
    scrollAddresses,
  } = storeToRefs(useChainsAccountsStore());
  const {
    fetchDetectedTokensTask,
    fetchDetectedTokens: fetchDetectedTokensCaller,
  } = useBlockchainBalancesApi();
  const { getChainName, supportsTransactions } = useSupportedChains();

  const { balances: ethBalances } = storeToRefs(useEthBalancesStore());
  const { balances: chainBalances } = storeToRefs(useChainBalancesStore());

  const fetchDetected = async (
    chain: Blockchain,
    addresses: string[],
  ): Promise<void> => {
    await Promise.allSettled(
      addresses.map(address => fetchDetectedTokens(chain, address)),
    );
  };

  const setState = (chain: Blockchain, data: EvmTokensRecord) => {
    const tokensVal = { ...get(tokensState) };
    set(tokensState, {
      ...tokensVal,
      [chain]: {
        ...tokensVal[chain],
        ...data,
      },
    });
  };

  const { notify } = useNotificationsStore();

  const fetchDetectedTokens = async (
    chain: Blockchain,
    address: string | null = null,
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
            chain: get(getChainName(chain)),
          }),
          address,
          chain,
        };

        const { result } = await awaitTask<EvmTokensRecord, TaskMeta>(
          taskId,
          taskType,
          taskMeta,
          true,
        );

        setState(chain, result);
      }
      else {
        const result = await fetchDetectedTokensCaller(chain, null);
        setState(chain, result);
      }
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);

        notify({
          title: t('actions.balances.detect_tokens.task.title'),
          message: t('actions.balances.detect_tokens.error.message', {
            address,
            chain: get(getChainName(chain)),
            error: error.message,
          }),
          display: true,
        });
      }
    }
  };

  const getTokens = (balances: BlockchainAssetBalances, address: string) => {
    const assets = balances[address]?.assets ?? [];
    return Object.keys(assets).filter(id => !get(isAssetIgnored(id)));
  };

  const getEthDetectedTokensInfo = (
    chain: MaybeRef<Blockchain>,
    address: MaybeRef<string | null>,
  ): ComputedRef<EthDetectedTokensInfo> =>
    computed(() => {
      const blockchain = get(chain);
      if (!supportsTransactions(blockchain))
        return noTokens();

      const state = get(tokensState);
      const detected: EvmTokensRecord | undefined = state[blockchain];
      const addr = get(address);

      if (!addr)
        return noTokens();

      const info = detected?.[addr];
      if (!info)
        return noTokens();

      let tokens: string[];
      if (blockchain === Blockchain.ETH)
        tokens = getTokens(get(ethBalances)[blockchain], addr);
      else if (isRestChain(blockchain))
        tokens = getTokens(get(chainBalances)[blockchain], addr);
      else
        tokens = info.tokens?.filter(id => !get(isAssetIgnored(id))) ?? [];

      return {
        tokens,
        total: tokens.length,
        timestamp: info.lastUpdateTimestamp || null,
      };
    });

  watch(ethAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev))
      return;

    await fetchDetectedTokens(Blockchain.ETH);
  });

  watch(optimismAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev))
      return;

    await fetchDetectedTokens(Blockchain.OPTIMISM);
  });

  watch(polygonAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev))
      return;

    await fetchDetectedTokens(Blockchain.POLYGON_POS);
  });

  watch(arbitrumAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev))
      return;

    await fetchDetectedTokens(Blockchain.ARBITRUM_ONE);
  });

  watch(baseAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev))
      return;

    await fetchDetectedTokens(Blockchain.BASE);
  });

  watch(gnosisAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev))
      return;

    await fetchDetectedTokens(Blockchain.GNOSIS);
  });

  watch(scrollAddresses, async (curr, prev) => {
    if (curr.length === 0 || isEqual(curr, prev))
      return;

    await fetchDetectedTokens(Blockchain.SCROLL);
  });

  const { isTaskRunning } = useTaskStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();

  const isMassDetecting = (chain: Blockchain) => {
    const massDetectingVal = get(massDetecting);
    if (!massDetectingVal)
      return false;

    return [chain, 'all'].includes(massDetectingVal);
  };

  [
    Blockchain.ETH,
    Blockchain.OPTIMISM,
    Blockchain.POLYGON_POS,
    Blockchain.ARBITRUM_ONE,
    Blockchain.BASE,
    Blockchain.GNOSIS,
  ].forEach((chain) => {
    const isChainDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
      chain,
    });

    watch(isChainDetecting, async (isDetecting, wasDetecting) => {
      if (!isMassDetecting(chain) && wasDetecting && !isDetecting) {
        await fetchBlockchainBalances({
          blockchain: chain,
          ignoreCache: true,
        });
      }
    });
  });

  return {
    massDetecting,
    fetchDetected,
    fetchDetectedTokens,
    getEthDetectedTokensInfo,
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBlockchainTokensStore, import.meta.hot),
  );
}
