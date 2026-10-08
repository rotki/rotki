import { get } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, nextTick } from 'vue';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { ProcessingState, useHistoricalBalancesProcessing } from './use-historical-balances-processing';

const triggerProcessing = vi.fn<() => Promise<boolean>>();

vi.mock('@/modules/history/balances/use-historical-balances', () => ({
  useHistoricalBalances: (): { triggerHistoricalBalancesProcessing: typeof triggerProcessing } => ({
    triggerHistoricalBalancesProcessing: triggerProcessing,
  }),
}));

describe('useHistoricalBalancesProcessing', () => {
  let scope: EffectScope;

  function setup(): ReturnType<typeof useHistoricalBalancesProcessing> {
    const result = scope.run(() => useHistoricalBalancesProcessing());
    if (!result)
      throw new Error('scope did not run');
    return result;
  }

  async function completeProcessing(): Promise<void> {
    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await nextTick();
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    triggerProcessing.mockReset().mockResolvedValue(true);
  });

  afterEach(() => {
    scope.stop();
  });

  it('should stay running after the trigger returns until processing completes', async () => {
    const { processNow, state } = setup();

    await processNow();
    expect(get(state)).toBe(ProcessingState.RUNNING);

    await completeProcessing();
    expect(get(state)).toBe(ProcessingState.DONE);
  });

  it('should stop running when the backend could not start processing', async () => {
    triggerProcessing.mockResolvedValue(false);
    const { processNow, state } = setup();

    await processNow();

    expect(get(state)).toBe(ProcessingState.NOT_STARTED);
  });

  it('should keep the reason when starting processing fails', async () => {
    triggerProcessing.mockRejectedValue(new Error('backend down'));
    const { failure, processNow, state } = setup();

    await processNow();

    expect(get(state)).toBe(ProcessingState.FAILED);
    expect(get(failure)).toBe('backend down');
  });

  it('should clear an earlier failure when processing is started again', async () => {
    triggerProcessing.mockRejectedValueOnce(new Error('backend down'));
    const { failure, processNow, state } = setup();
    await processNow();

    await processNow();

    expect(get(state)).toBe(ProcessingState.RUNNING);
    expect(get(failure)).toBeUndefined();
  });

  it('should count a run the page did not start as done', async () => {
    const { state } = setup();

    await completeProcessing();

    expect(get(state)).toBe(ProcessingState.DONE);
  });

  it('should not undo a completion that arrives before the trigger returns', async () => {
    let resolveTrigger: (started: boolean) => void = () => {};
    triggerProcessing.mockReturnValue(new Promise((resolve) => {
      resolveTrigger = resolve;
    }));
    const { processNow, state } = setup();

    const processing = processNow();
    await completeProcessing();
    resolveTrigger(true);
    await processing;

    expect(get(state)).toBe(ProcessingState.DONE);
  });
});
