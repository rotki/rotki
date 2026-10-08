import type { EvmTokensRecord } from '@/modules/balances/types/balances';
import type { RunBackendTask } from '@/modules/task-center/use-native-task';
import { err, isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
import { Cancelled, isActionable, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';

interface UseTokenDetectionApiReturn {
  /**
   * Task-backed detection for one address. Runs inside a TOKEN_DETECTION activity, so it takes
   * that activity's bound runner rather than reaching for the unbound one.
   */
  detectTokensForAddress: (runTask: RunBackendTask, chain: string, address: string) => Promise<Result<void, TaskError>>;
  /** Cached read for a whole chain. No backend task, so nothing to bind to an activity. */
  fetchCachedDetectedTokens: (chain: string) => Promise<Result<void, TaskError>>;
}

export function useTokenDetectionApi(): UseTokenDetectionApiReturn {
  const { setState } = useTokenDetectionStore();
  const { fetchDetectedTokens: fetchCachedTokens, fetchDetectedTokensTask } = useBlockchainBalancesApi();

  const detectTokensForAddress = async (
    runTask: RunBackendTask,
    chain: string,
    address: string,
  ): Promise<Result<void, TaskError>> => {
    const result = await runTask<EvmTokensRecord>(
      async () => fetchDetectedTokensTask(chain, [address]),
    );

    if (isErr(result)) {
      if (isActionable(result.error))
        logger.error(`token detection failed for ${address} on ${chain}: ${result.error.message}`);
    }
    else {
      setState(chain, result.value);
    }

    return mapResult(result, () => {});
  };

  const fetchCachedDetectedTokens = async (chain: string): Promise<Result<void, TaskError>> => {
    try {
      const result = await fetchCachedTokens(chain, null);
      setState(chain, result);
      return ok(undefined);
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);

      if (isRequestCancellation(error))
        return err(Cancelled({ message }));

      logger.error(`reading the detected tokens of ${chain} failed: ${message}`);
      return err(TaskFailed({ message }));
    }
  };

  return {
    detectTokensForAddress,
    fetchCachedDetectedTokens,
  };
}
