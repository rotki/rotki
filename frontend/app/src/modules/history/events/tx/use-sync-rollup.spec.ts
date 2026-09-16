import { submitRefresh } from '@test/utils/history-refresh';
import { beforeEach, describe, expect, it } from 'vitest';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';
import { useSyncRollup } from './use-sync-rollup';

describe('useSyncRollup', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    // The orchestrator is a shared singleton, so its records outlive a test without this.
    useTaskOrchestrator().reset();
  });

  describe('liveness', () => {
    it('should be neither working nor settled before any refresh', () => {
      const { isSettled, isWorking } = useSyncRollup();

      expect(get(isWorking)).toBe(false);
      expect(get(isSettled)).toBe(false);
    });

    it('should be working while any part of the refresh is still in flight', async () => {
      await submitRefresh({ eth: { '0x123': 'running' } });

      const { isSettled, isWorking } = useSyncRollup();
      expect(get(isWorking)).toBe(true);
      expect(get(isSettled)).toBe(false);
    });

    /** A failure is a settled outcome, so it must not leave the refresh reading as still working. */
    it('should settle when an account failed rather than sitting short of the end', async () => {
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'failed' } });

      const { isSettled, isWorking, progress } = useSyncRollup();
      expect(get(isWorking)).toBe(false);
      expect(get(isSettled)).toBe(true);
      expect(get(progress)).toBe(100);
    });
  });

  describe('progress', () => {
    it('should be 0 before any refresh', () => {
      expect(get(useSyncRollup().progress)).toBe(0);
    });

    it('should count settled leaves over declared leaves', async () => {
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'running' } });

      const { declaredLeaves, progress, settledLeaves } = useSyncRollup();
      expect(get(progress)).toBe(50);
      expect(get(settledLeaves)).toBe(1);
      expect(get(declaredLeaves)).toBe(2);
    });

    /**
     * The unit is the leaf, not the chain. Weighting whole chains equally would make one settled
     * account worth more on a two-account chain than on a ten-account one.
     */
    it('should weight every account equally, whichever chain it sits on', async () => {
      await submitRefresh({
        eth: { '0x1': 'complete', '0x2': 'running', '0x3': 'running' },
        gnosis: { '0xa': 'complete' },
      });

      expect(get(useSyncRollup().progress)).toBe(50);
    });

    /** A chain settles when its accounts do, so counting it too would double-count that work. */
    it('should not count the chain and umbrella rows as units of work', async () => {
      await submitRefresh({ eth: { '0x123': 'complete' } });

      expect(get(useSyncRollup().progress)).toBe(100);
    });

    it('should treat a cancelled leaf as settled, since nothing more will happen to it', async () => {
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'cancelled' } });

      expect(get(useSyncRollup().progress)).toBe(100);
    });
  });
});
