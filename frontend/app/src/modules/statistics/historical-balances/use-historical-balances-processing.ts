import type { DeepReadonly, Ref } from 'vue';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';

export const ProcessingState = {
  IDLE: 'idle',
  /** Started from the page; waiting for the backend to report it finished. */
  RUNNING: 'running',
  /** The backend could not start it, because a profit and loss report is gathering history. */
  NOT_STARTED: 'not-started',
  /** Starting it failed; `failure` holds why. */
  FAILED: 'failed',
  /** A run finished while the page was open, so an empty day is really empty. */
  DONE: 'done',
} as const;

export type ProcessingState = typeof ProcessingState[keyof typeof ProcessingState];

interface UseHistoricalBalancesProcessingReturn {
  state: DeepReadonly<Ref<ProcessingState>>;
  failure: DeepReadonly<Ref<string | undefined>>;
  processNow: () => Promise<void>;
}

/**
 * The historical balances page's "Process now" action and what became of it.
 *
 * @remarks
 * The trigger returns once processing is scheduled, long before it is done, so a started run stays
 * running until the completion message. Any completion counts, including a run the page did not
 * start, since after it every day's balances are current.
 */
export function useHistoricalBalancesProcessing(): UseHistoricalBalancesProcessingReturn {
  const state = shallowRef<ProcessingState>(ProcessingState.IDLE);
  const failure = shallowRef<string>();

  const { historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { triggerHistoricalBalancesProcessing } = useHistoricalBalances();

  async function processNow(): Promise<void> {
    set(failure, undefined);
    set(state, ProcessingState.RUNNING);
    try {
      if (!await triggerHistoricalBalancesProcessing())
        set(state, ProcessingState.NOT_STARTED);
    }
    catch (error: unknown) {
      set(failure, error instanceof Error ? error.message : String(error));
      set(state, ProcessingState.FAILED);
    }
  }

  watch(historicalBalanceProcessingCompleted, () => {
    set(state, ProcessingState.DONE);
  });

  return {
    failure: readonly(failure),
    processNow,
    state: readonly(state),
  };
}
