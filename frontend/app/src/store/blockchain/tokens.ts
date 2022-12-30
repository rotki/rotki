import { type MaybeRef } from '@vueuse/core';
import { Blockchain } from '@rotki/common/lib/blockchain';
import isEqual from 'lodash/isEqual';
import { type ComputedRef, type Ref } from 'vue';
import {
  type EthDetectedTokensInfo,
  type EvmTokensRecord
} from '@/services/balances/types';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useEthAccountsStore } from '@/store/blockchain/accounts/eth';
import { useBlockchainBalancesStore } from '@/store/blockchain/balances';
import { useTasks } from '@/store/tasks';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';
import { useBlockchainBalanceApi } from '@/services/balances/blockchain';
import { type TokenChains, isTokenChain } from '@/types/blockchain/chains';
import { useChainsAccountsStore } from '@/store/blockchain/accounts/chains';

const noTokens = (): EthDetectedTokensInfo => ({
  tokens: [],
  total: 0,
  timestamp: null
});

export const useBlockchainTokensStore = defineStore('blockchain/tokens', () => {
  const ethTokens: Ref<EvmTokensRecord> = ref({});
  const optimismTokens: Ref<EvmTokensRecord> = ref({});

  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { tc } = useI18n();
  const { ethAddresses } = storeToRefs(useEthAccountsStore());
  const { optimismAddresses } = storeToRefs(useChainsAccountsStore());
  const {
    fetchDetectedTokensTask,
    fetchDetectedTokens: fetchDetectedTokensCaller
  } = useBlockchainBalanceApi();

  const fetchDetected = async (
    chain: TokenChains,
    addresses: string[]
  ): Promise<void> => {
    await Promise.allSettled(
      addresses.map(address => fetchDetectedTokens(chain, address))
    );
  };

  const fetchDetectedTokens = async (
    chain: TokenChains,
    address: string | null = null
  ) => {
    try {
      if (address) {
        const { awaitTask } = useTasks();
        const taskType = TaskType.FETCH_DETECTED_TOKENS;

        const { taskId } = await fetchDetectedTokensTask(chain, [address]);

        const taskMeta = {
          title: tc('actions.balances.detect_tokens.task.title'),
          description: tc(
            'actions.balances.detect_tokens.task.description',
            0,
            {
              address
            }
          ),
          address
        };

        await awaitTask<EvmTokensRecord, TaskMeta>(
          taskId,
          taskType,
          taskMeta,
          true
        );

        await fetchDetectedTokens(chain);
      } else {
        const tokens = await fetchDetectedTokensCaller(chain, null);
        if (chain === Blockchain.ETH) {
          set(ethTokens, tokens);
        } else {
          set(optimismTokens, tokens);
        }
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
      if (!isTokenChain(blockchain)) {
        return noTokens();
      }
      const sourceTokens =
        blockchain === Blockchain.OPTIMISM ? optimismTokens : ethTokens;
      const detected = get(sourceTokens);
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

  const { isTaskRunning } = useTasks();
  const isDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS);

  const { fetchBlockchainBalances } = useBlockchainBalancesStore();

  watch(isDetecting, async (isDetecting, wasDetecting) => {
    if (wasDetecting && !isDetecting) {
      await fetchBlockchainBalances({
        blockchain: Blockchain.ETH,
        ignoreCache: true
      });
    }
  });

  return {
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
