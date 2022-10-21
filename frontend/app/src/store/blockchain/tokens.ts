import { MaybeRef } from '@vueuse/core';
import isEqual from 'lodash/isEqual';
import { ComputedRef, Ref } from 'vue';
import {
  EthDetectedTokensInfo,
  EthDetectedTokensRecord
} from '@/services/balances/types';
import { api } from '@/services/rotkehlchen-api';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useEthBalancesStore } from '@/store/blockchain/balances/eth';
import { useTasks } from '@/store/tasks';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

export const useBlockchainTokensStore = defineStore('blockchain/tokens', () => {
  const ethTokens: Ref<EthDetectedTokensRecord> = ref({});

  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { tc } = useI18n();
  const { ethAddresses } = storeToRefs(useEthBalancesStore());

  const fetchDetected = async (addresses: string[]): Promise<void> => {
    await Promise.allSettled(
      addresses.map(address => fetchDetectedTokens(address))
    );
  };

  const fetchDetectedTokens = async (address: string | null = null) => {
    try {
      if (address) {
        const { awaitTask } = useTasks();
        const taskType = TaskType.FETCH_DETECTED_TOKENS;

        const { taskId } = await api.balances.fetchDetectedTokensTask([
          address
        ]);

        const taskMeta = {
          title: tc('actions.balances.detect_tokens.task.title'),
          description: tc(
            'actions.balances.detect_tokens.task.description',
            0,
            {
              address
            }
          ),
          numericKeys: [],
          address
        };

        await awaitTask<EthDetectedTokensRecord, TaskMeta>(
          taskId,
          taskType,
          taskMeta,
          true
        );

        await fetchDetectedTokens();
      } else {
        set(
          ethTokens,
          await api.balances.fetchDetectedTokens(get(ethAddresses))
        );
      }
    } catch (e) {
      logger.error(e);
    }
  };

  const getEthDetectedTokensInfo = (
    address: MaybeRef<string | null>
  ): ComputedRef<EthDetectedTokensInfo> =>
    computed(() => {
      const detected = get(ethTokens);
      const addr = get(address);
      const info = (addr && detected?.[addr]) || null;
      if (!info) {
        return {
          tokens: [],
          total: 0,
          timestamp: null
        };
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
    await fetchDetectedTokens();
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
