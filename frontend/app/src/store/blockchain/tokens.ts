import type { EthDetectedTokensInfo, EvmTokensRecord } from '@/types/balances';
import type { BlockchainAssetBalances } from '@/types/blockchain/balances';
import type { TaskMeta } from '@/types/task';
import type { MaybeRef } from '@vueuse/core';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useBlockchainBalances } from '@/composables/blockchain/balances';
import { useSupportedChains } from '@/composables/info/chains';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useBlockchainStore } from '@/store/blockchain/index';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { logger } from '@/utils/logging';
import { isEqual } from 'es-toolkit';

function noTokens(): EthDetectedTokensInfo {
  return {
    timestamp: null,
    tokens: [],
    total: 0,
  };
}

type Tokens = Record<string, EvmTokensRecord>;

export const useBlockchainTokensStore = defineStore('blockchain/tokens', () => {
  const tokensState = ref<Tokens>({});

  const massDetecting = ref<string>();

  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { t } = useI18n();
  const { addresses, balances } = storeToRefs(useBlockchainStore());
  const { fetchDetectedTokens: fetchDetectedTokensCaller, fetchDetectedTokensTask } = useBlockchainBalancesApi();
  const { getChainName, supportsTransactions, txEvmChains } = useSupportedChains();
  const { notify } = useNotificationsStore();

  const monitoredAddresses = computed<Record<string, string[]>>(() => {
    const addressesPerChain = get(addresses);
    return Object.fromEntries(get(txEvmChains).map(chain => [chain.id, addressesPerChain[chain.id] ?? []]));
  });

  const setState = (chain: string, data: EvmTokensRecord): void => {
    const tokensVal = { ...get(tokensState) };
    set(tokensState, {
      ...tokensVal,
      [chain]: {
        ...tokensVal[chain],
        ...data,
      },
    });
  };

  const fetchDetectedTokens = async (chain: string, address: string | null = null): Promise<void> => {
    try {
      if (address) {
        const { awaitTask } = useTaskStore();
        const taskType = TaskType.FETCH_DETECTED_TOKENS;

        const { taskId } = await fetchDetectedTokensTask(chain, [address]);

        const taskMeta = {
          address,
          chain,
          description: t('actions.balances.detect_tokens.task.description', {
            address,
            chain: get(getChainName(chain)),
          }),
          title: t('actions.balances.detect_tokens.task.title'),
        };

        const { result } = await awaitTask<EvmTokensRecord, TaskMeta>(taskId, taskType, taskMeta, true);

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
          display: true,
          message: t('actions.balances.detect_tokens.error.message', {
            address,
            chain: get(getChainName(chain)),
            error: error.message,
          }),
          title: t('actions.balances.detect_tokens.task.title'),
        });
      }
    }
  };

  const fetchDetected = async (chain: string, addresses: string[]): Promise<void> => {
    await awaitParallelExecution(
      addresses,
      address => address,
      async address => fetchDetectedTokens(chain, address),
      2,
    );
  };

  const getTokens = (balances: BlockchainAssetBalances, address: string): string[] => {
    const assets = balances?.[address]?.assets ?? [];
    return Object.keys(assets).filter(id => !get(isAssetIgnored(id)));
  };

  const getEthDetectedTokensInfo = (
    chain: MaybeRef<string>,
    address: MaybeRef<string | null>,
  ): ComputedRef<EthDetectedTokensInfo> => computed<EthDetectedTokensInfo>(() => {
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

    const tokens: string[] = getTokens(get(balances)[blockchain], addr);
    return {
      timestamp: info.lastUpdateTimestamp || null,
      tokens,
      total: tokens.length,
    };
  });

  watch(monitoredAddresses, async (curr, prev) => {
    for (const chain in curr) {
      const addresses = curr[chain];
      if (!addresses || addresses.length === 0 || isEqual(addresses, prev[chain]))
        continue;

      await fetchDetectedTokens(chain);
    }
  });

  const { isTaskRunning } = useTaskStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();

  const detectionStatus = computed(() => {
    const isDetecting: Record<string, boolean> = {};
    get(txEvmChains).forEach(({ id }) => {
      isDetecting[id] = get(
        isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
          chain: id,
        }),
      );
    });

    return isDetecting;
  });

  watch(detectionStatus, async (isDetecting, wasDetecting) => {
    if (isEqual(isDetecting, wasDetecting))
      return;

    const pendingRefresh: string[] = [];
    for (const chain in isDetecting) {
      if (!isDetecting[chain] && wasDetecting[chain])
        pendingRefresh.push(chain);
    }

    await awaitParallelExecution(
      pendingRefresh,
      chain => chain,
      async chain =>
        fetchBlockchainBalances({
          blockchain: chain,
          ignoreCache: true,
        }),
      2,
    );
  });

  return {
    fetchDetected,
    fetchDetectedTokens,
    getEthDetectedTokensInfo,
    massDetecting,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainTokensStore, import.meta.hot));
