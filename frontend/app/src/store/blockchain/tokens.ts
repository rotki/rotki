import type { MaybeRefOrGetter } from 'vue';
import type { TaskMeta } from '@/modules/tasks/types';
import type { EthDetectedTokensInfo, EvmTokensRecord } from '@/types/balances';
import type { BlockchainAssetBalances } from '@/types/blockchain/balances';
import { isEqual } from 'es-toolkit';
import { useBlockchainBalancesApi } from '@/composables/api/balances/blockchain';
import { useBalanceQueue } from '@/composables/balances/use-balance-queue';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { logger } from '@/utils/logging';

function noTokens(): EthDetectedTokensInfo {
  return {
    timestamp: null,
    tokens: [],
    total: 0,
  };
}

type Tokens = Record<string, EvmTokensRecord>;

export const useBlockchainTokensStore = defineStore('blockchain/tokens', () => {
  const tokensState = shallowRef<Tokens>({});

  const massDetecting = ref<string>();

  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { t } = useI18n({ useScope: 'global' });
  const { balances } = storeToRefs(useBalancesStore());
  const { addresses } = useAccountAddresses();
  const { fetchDetectedTokens: fetchDetectedTokensCaller, fetchDetectedTokensTask } = useBlockchainBalancesApi();
  const { getChainName, supportsTransactions, txEvmChains } = useSupportedChains();
  const { notifyError } = useNotifications();

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

  const { runTask } = useTaskHandler();

  const fetchDetectedTokens = async (chain: string, address: string | null = null): Promise<void> => {
    if (address) {
      const taskMeta = {
        address,
        chain,
        description: t('actions.balances.detect_tokens.task.description', {
          address,
          chain: getChainName(chain),
        }),
        title: t('actions.balances.detect_tokens.task.title'),
      };

      const outcome = await runTask<EvmTokensRecord, TaskMeta>(
        async () => fetchDetectedTokensTask(chain, [address]),
        { type: TaskType.FETCH_DETECTED_TOKENS, meta: taskMeta, unique: false },
      );

      if (outcome.success) {
        setState(chain, outcome.result);
      }
      else if (isActionableFailure(outcome)) {
        logger.error(outcome.error);
        notifyError(
          t('actions.balances.detect_tokens.task.title'),
          t('actions.balances.detect_tokens.error.message', {
            address,
            chain: getChainName(chain),
            error: outcome.message,
          }),
        );
      }
    }
    else {
      try {
        const result = await fetchDetectedTokensCaller(chain, null);
        setState(chain, result);
      }
      catch (error: unknown) {
        logger.error(error);
        notifyError(
          t('actions.balances.detect_tokens.task.title'),
          t('actions.balances.detect_tokens.error.message', {
            address,
            chain: getChainName(chain),
            error: getErrorMessage(error),
          }),
        );
      }
    }
  };

  const fetchDetected = async (chain: string, addresses: string[]): Promise<void> => {
    const { queueTokenDetection } = useBalanceQueue();
    await queueTokenDetection(chain, addresses, async address => fetchDetectedTokens(chain, address));
  };

  const getTokens = (balances: BlockchainAssetBalances, address: string): string[] => {
    const assets = balances?.[address]?.assets ?? [];
    return Object.keys(assets).filter(id => !isAssetIgnored(id));
  };

  function findEthDetectedTokensInfo(blockchain: string, addr: string | null): EthDetectedTokensInfo {
    if (!supportsTransactions(blockchain))
      return noTokens();

    const state = get(tokensState);
    const detected: EvmTokensRecord | undefined = state[blockchain];

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
  }

  const getEthDetectedTokensInfo = (
    chain: MaybeRefOrGetter<string>,
    address: MaybeRefOrGetter<string | null>,
  ): ComputedRef<EthDetectedTokensInfo> => computed<EthDetectedTokensInfo>(() =>
    findEthDetectedTokensInfo(toValue(chain), toValue(address)),
  );

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

  const detectionStatus = computed<Record<string, boolean>>(() => {
    const isDetecting: Record<string, boolean> = {};
    get(txEvmChains).forEach(({ id }) => {
      isDetecting[id] = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, { chain: id });
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
    findEthDetectedTokensInfo,
    getEthDetectedTokensInfo,
    massDetecting,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainTokensStore, import.meta.hot));
