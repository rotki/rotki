import type { EvmTokensRecord } from '@/modules/balances/types/balances';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';

interface UseTokenDetectionApiReturn {
  fetchDetectedTokens: (chain: string, address?: string | null) => Promise<void>;
}

export function useTokenDetectionApi(): UseTokenDetectionApiReturn {
  const { setState } = useTokenDetectionStore();
  const { fetchDetectedTokens: fetchCachedTokens, fetchDetectedTokensTask } = useBlockchainBalancesApi();
  const { getChainName } = useSupportedChains();
  const { notifyError } = useNotifications();
  const { runTask } = useTaskHandler();
  const { t } = useI18n({ useScope: 'global' });

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
        const result = await fetchCachedTokens(chain, null);
        setState(chain, result);
      }
      catch (error: unknown) {
        logger.error(error);
        notifyError(
          t('actions.balances.detect_tokens.task.title'),
          t('actions.balances.detect_tokens.error.message', {
            address: '',
            chain: getChainName(chain),
            error: getErrorMessage(error),
          }),
        );
      }
    }
  };

  return {
    fetchDetectedTokens,
  };
}
