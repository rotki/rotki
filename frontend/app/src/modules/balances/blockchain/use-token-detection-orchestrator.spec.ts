import { runSpecWith } from '@test/utils/mocks/native-task';
import { ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { type Activity, ActivityKind, ActivityStatus, makeActivityId } from '@/modules/task-center/core/types';

const mockDetectTokensForAddress = vi.fn().mockResolvedValue(ok(undefined));
const mockFetchCachedDetectedTokens = vi.fn().mockResolvedValue(ok(undefined));
vi.mock('@/modules/balances/blockchain/use-token-detection-api', () => ({
  useTokenDetectionApi: vi.fn().mockReturnValue({
    detectTokensForAddress: mockDetectTokensForAddress,
    fetchCachedDetectedTokens: mockFetchCachedDetectedTokens,
  }),
}));

vi.mock('@/modules/balances/blockchain/use-token-detection-store', () => ({
  useTokenDetectionStore: vi.fn().mockReturnValue({
    massDetecting: ref<string>(),
    setMassDetecting: vi.fn(),
  }),
}));

const mockAddresses = ref<Record<string, string[]>>({});
vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn().mockReturnValue({
    addresses: mockAddresses,
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    getChainName: (chain: string): string => chain,
    supportsTransactions: (chain: string): boolean => chain !== 'btc',
    txEvmChains: computed(() => [
      { id: 'eth' },
      { id: 'optimism' },
    ]),
  }),
}));

const mockHydrate = vi.fn().mockResolvedValue(undefined);
vi.mock('@/modules/balances/use-balance-hydration', () => ({
  useBalanceHydration: vi.fn().mockReturnValue({
    hydrate: mockHydrate,
  }),
}));

// submitTask runs the spec body so the detection call is reached, mirroring an immediate run.
const mockRunTask = vi.fn();
const mockSubmitTask = vi.fn(runSpecWith(mockRunTask));
vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn().mockReturnValue({
    reportProgress: vi.fn(),
    submitTask: mockSubmitTask,
  }),
}));

const mockActivities = ref<Activity[]>([]);
vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn().mockReturnValue({
    activities: mockActivities,
  }),
}));

function detectionActivity(chain: string, address: string, status: ActivityStatus = ActivityStatus.RUNNING): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.TOKEN_DETECTION, chain, address),
    kind: ActivityKind.TOKEN_DETECTION,
    percentage: -1,
    rerunnable: true,
    source: { type: 'native' },
    status,
    title: 'Token detection',
  };
}

// Must use dynamic import + resetModules because createSharedComposable caches the instance
async function loadOrchestrator(): Promise<typeof import('./use-token-detection-orchestrator')> {
  vi.resetModules();
  return import('./use-token-detection-orchestrator');
}

describe('useTokenDetectionOrchestrator', () => {
  /** `useDisabledChains` reads the settings repo, so detection needs a live pinia. */
  function setDisabled(value: Record<string, string[]>): void {
    const repo = useSettingsRepo();
    repo.updateGeneral({ ...repo.general, disabledChainQueries: value });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(mockAddresses, {});
    set(mockActivities, []);
  });

  describe('detectForChain', () => {
    /**
     * Detection must not share `BALANCES_LANE` with the chain job that awaits it. That job
     * holds a balances slot for its whole body, and the cap is 2 — so children queued on the same
     * lane could never get one, and two chain jobs would sit waiting on addresses that cannot
     * start. A hang, not a slowdown, and no unit test that stubs `submitTask` can see it: the lane
     * is only honoured by the real scheduler. Assert the lane itself.
     */
    it('should queue detection on the per-chain lane, never the balances lane', async () => {
      set(mockAddresses, { eth: ['0xaddr1', '0xaddr2'] });
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();

      await useTokenDetectionOrchestrator().detectForChain('eth', makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'));

      expect(mockSubmitTask).toHaveBeenCalledTimes(2);
      for (const [spec] of mockSubmitTask.mock.calls) {
        expect(spec.lane).toBe('detect:eth');
        expect(spec.parent).toBe(makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'));
      }
    });

    it('should do nothing for a chain with no addresses', async () => {
      set(mockAddresses, { eth: [] });
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();

      await useTokenDetectionOrchestrator().detectForChain('eth', makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'));

      expect(mockSubmitTask).not.toHaveBeenCalled();
    });

    /**
     * Every detection path queues through `queueDetectionForChain`, so filtering there covers
     * `detectTokens` and `detectAllTokens` too — automated detection was still firing
     * `POST /blockchains/<chain>/tokens/detect` for chains the user had switched off.
     */
    it('should not detect an address excluded by disabledChainQueries', async () => {
      set(mockAddresses, { eth: ['0xaddr1', '0xaddr2'] });
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      setDisabled({ eth: ['0xADDR1'] });

      await useTokenDetectionOrchestrator().detectForChain('eth', makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'));

      expect(mockSubmitTask).toHaveBeenCalledTimes(1);
      const [spec] = mockSubmitTask.mock.calls[0];
      expect(spec.id).toBe(makeActivityId(ActivityKind.TOKEN_DETECTION, 'eth', '0xaddr2'));
    });

    it('should detect nothing on a fully excluded chain', async () => {
      set(mockAddresses, { eth: ['0xaddr1', '0xaddr2'] });
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      setDisabled({ eth: [] });

      await useTokenDetectionOrchestrator().detectForChain('eth', makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'));

      expect(mockSubmitTask).not.toHaveBeenCalled();
    });

    /** The chain job's own query follows immediately and reads the same rows. */
    it('should not hydrate, unlike the standalone detection flow', async () => {
      set(mockAddresses, { eth: ['0xaddr1'] });
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();

      await useTokenDetectionOrchestrator().detectForChain('eth', makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'eth'));

      expect(mockHydrate).not.toHaveBeenCalled();
    });
  });

  describe('detectTokens', () => {
    it('should submit a native detection activity per address and reload cached balances', async () => {
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectTokens } = useTokenDetectionOrchestrator();

      await detectTokens('eth', ['0xaddr1', '0xaddr2']);

      expect(mockSubmitTask).toHaveBeenCalledTimes(2);
      expect(mockSubmitTask.mock.calls[0][0]).toMatchObject({
        id: makeActivityId(ActivityKind.TOKEN_DETECTION, 'eth', '0xaddr1'),
        kind: ActivityKind.TOKEN_DETECTION,
        rerunnable: true,
      });
      expect(mockDetectTokensForAddress).toHaveBeenCalledWith(mockRunTask, 'eth', '0xaddr1');
      expect(mockDetectTokensForAddress).toHaveBeenCalledWith(mockRunTask, 'eth', '0xaddr2');
      expect(mockHydrate).toHaveBeenCalledWith({
        blockchain: ['eth'],
      });
    });

    it('should submit detection for multiple chains', async () => {
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectTokens } = useTokenDetectionOrchestrator();

      await detectTokens(['eth', 'optimism'], ['0xaddr1']);

      expect(mockSubmitTask).toHaveBeenCalledTimes(2);
      // One hydration for the whole set, not one per chain: `hydrate` takes the chains and applies
      // its own bound.
      expect(mockHydrate).toHaveBeenCalledWith({ blockchain: ['eth', 'optimism'] });
    });
  });

  describe('detectAllTokens', () => {
    it('should detect tokens for all tx evm chains when no chain specified', async () => {
      set(mockAddresses, {
        eth: ['0xaddr1'],
        optimism: ['0xaddr2'],
      });

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectAllTokens } = useTokenDetectionOrchestrator();

      await detectAllTokens();

      expect(mockSubmitTask).toHaveBeenCalledTimes(2);
      expect(mockHydrate).toHaveBeenCalledWith({ blockchain: ['eth', 'optimism'] });
    });

    it('should detect tokens only for specified chains', async () => {
      set(mockAddresses, {
        eth: ['0xaddr1'],
        optimism: ['0xaddr2'],
      });

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectAllTokens } = useTokenDetectionOrchestrator();

      await detectAllTokens('eth');

      expect(mockSubmitTask).toHaveBeenCalledOnce();
      expect(mockDetectTokensForAddress).toHaveBeenCalledWith(mockRunTask, 'eth', '0xaddr1');
    });

    it('should skip chains without addresses', async () => {
      set(mockAddresses, {
        eth: ['0xaddr1'],
        // optimism has no addresses
      });

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectAllTokens } = useTokenDetectionOrchestrator();

      await detectAllTokens();

      expect(mockSubmitTask).toHaveBeenCalledOnce();
    });

    it('should skip chains that do not support transactions', async () => {
      set(mockAddresses, {
        btc: ['bc1qaddr1'],
        eth: ['0xaddr1'],
      });

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { detectAllTokens } = useTokenDetectionOrchestrator();

      await detectAllTokens(['btc', 'eth']);

      // Only eth should be submitted — btc does not support transactions
      expect(mockSubmitTask).toHaveBeenCalledOnce();
      expect(mockDetectTokensForAddress).toHaveBeenCalledWith(mockRunTask, 'eth', '0xaddr1');
    });
  });

  describe('isDetecting / useIsDetecting', () => {
    it('should return false when no detection is running', async () => {
      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { useIsDetecting } = useTokenDetectionOrchestrator();

      const detecting = useIsDetecting('eth');
      expect(get(detecting)).toBe(false);
    });

    it('should return true when a detection activity is running for the chain', async () => {
      set(mockActivities, [detectionActivity('eth', '0xaddr1')]);

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { useIsDetecting } = useTokenDetectionOrchestrator();

      expect(get(useIsDetecting('eth'))).toBe(true);
    });

    it('should ignore terminal detection activities', async () => {
      set(mockActivities, [detectionActivity('eth', '0xaddr1', ActivityStatus.COMPLETE)]);

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { useIsDetecting } = useTokenDetectionOrchestrator();

      expect(get(useIsDetecting('eth'))).toBe(false);
    });

    it('should check a specific address when provided', async () => {
      set(mockActivities, [detectionActivity('eth', '0xaddr1')]);

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { isDetecting, useIsDetecting } = useTokenDetectionOrchestrator();

      expect(get(useIsDetecting('eth', '0xaddr1'))).toBe(true);
      expect(get(useIsDetecting('eth', '0xaddr2'))).toBe(false);
      expect(isDetecting('eth', '0xaddr1')).toBe(true);
      expect(isDetecting('eth', '0xaddr2')).toBe(false);
    });

    it('should check across multiple chains', async () => {
      set(mockActivities, [detectionActivity('optimism', '0xaddr1')]);

      const { useTokenDetectionOrchestrator } = await loadOrchestrator();
      const { useIsDetecting } = useTokenDetectionOrchestrator();

      expect(get(useIsDetecting(['eth', 'optimism']))).toBe(true);
    });
  });
});
