import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { type Activity, ActivityKind, ActivityPart, ActivityStatus, makeActivityId } from '@/modules/task-center/core/types';
import '@test/i18n';

const activities = ref<Activity[]>([]);
const blockchainStatus = ref<{ active: boolean }>({ active: false });
const tokenStatus = ref<{ active: boolean }>({ active: false });

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn().mockReturnValue({ activities }),
}));

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: vi.fn().mockReturnValue({
    useIsActive: vi.fn().mockImplementation((kind: string) => computed<boolean>(() =>
      get(kind === ActivityKind.BLOCKCHAIN_BALANCES ? blockchainStatus : tokenStatus).active,
    )),
    useWorkStatus: vi.fn().mockImplementation((kind: string) =>
      kind === ActivityKind.BLOCKCHAIN_BALANCES ? blockchainStatus : tokenStatus,
    ),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    getChainName: (chain: string): string => chain,
  }),
}));

function balanceActivity(chain: string, status: ActivityStatus): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    percentage: -1,
    rerunnable: true,
    source: { type: 'native' },
    status,
    title: 'Blockchain balances',
  };
}

function detectionActivity(chain: string, address: string, status: ActivityStatus): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.TOKEN_DETECTION, chain, address),
    kind: ActivityKind.TOKEN_DETECTION,
    parent: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain),
    percentage: -1,
    rerunnable: true,
    source: { type: 'native' },
    status,
    title: 'Token detection',
  };
}

/** The run umbrella: same kind as the chain jobs beneath it, but not a subject. */
function runUmbrella(status: ActivityStatus): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, ActivityPart.RUN, 'abc123', 'background'),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    percentage: -1,
    rerunnable: false,
    source: { type: 'native' },
    status,
    title: 'Blockchain balances',
  };
}

async function load(): Promise<typeof import('./use-balance-query-progress')> {
  vi.resetModules();
  return import('./use-balance-query-progress');
}

describe('useBalanceQueryProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(activities, []);
    set(blockchainStatus, { active: false });
    set(tokenStatus, { active: false });
  });

  it('should report isBalanceQuerying from the work status', async () => {
    const { useBalanceQueryProgress } = await load();
    const { isBalanceQuerying } = useBalanceQueryProgress();

    expect(get(isBalanceQuerying)).toBe(false);
    set(blockchainStatus, { active: true });
    expect(get(isBalanceQuerying)).toBe(true);
  });

  /**
   * Seen in the app as "(7/19) Querying Run balances...". The run umbrella carries the same
   * kind as its chain jobs, so it was counted as one of them — inflating the denominator, and
   * naming itself from its id's first part, which is the literal `run`.
   */
  it('should not count the run umbrella as a chain', async () => {
    set(activities, [
      runUmbrella(ActivityStatus.RUNNING),
      balanceActivity('eth', ActivityStatus.RUNNING),
      balanceActivity('optimism', ActivityStatus.PENDING),
    ]);

    const { useBalanceQueryProgress } = await load();
    const { balanceProgress } = useBalanceQueryProgress();
    await nextTick();

    const progress = get(balanceProgress);
    expect(progress?.totalSteps).toBe(2);
    expect(progress?.currentOperationData?.chain).toBe('eth');
    expect(progress?.currentOperation).not.toContain('run');
  });

  /**
   * Watched live climbing 35 → 53 → 62 → 65 → 73. A chain's addresses are only submitted once
   * its own job starts, so counting detections made the total grow through the run — the number
   * moved while the user watched it. The count is the run's scope, which is fixed up front.
   */
  it('should not grow the denominator as detections are submitted', async () => {
    set(activities, [
      balanceActivity('eth', ActivityStatus.RUNNING),
      balanceActivity('optimism', ActivityStatus.PENDING),
    ]);

    const { useBalanceQueryProgress } = await load();
    const { balanceProgress } = useBalanceQueryProgress();
    await nextTick();
    expect(get(balanceProgress)?.totalSteps).toBe(2);

    // eth's job starts and submits two addresses; optimism's follow later.
    set(activities, [
      balanceActivity('eth', ActivityStatus.RUNNING),
      balanceActivity('optimism', ActivityStatus.PENDING),
      detectionActivity('eth', '0xaaa', ActivityStatus.RUNNING),
      detectionActivity('eth', '0xbbb', ActivityStatus.PENDING),
    ]);
    await nextTick();

    const progress = get(balanceProgress);
    expect(progress?.totalSteps).toBe(2);
    // ...but the detection still names the operation, rather than being hidden entirely.
    expect(progress?.currentOperationData?.type).toBe(ActivityKind.TOKEN_DETECTION);
    expect(progress?.currentOperationData?.address).toBe('0xaaa');
  });

  it('should be undefined when no balance activities exist', async () => {
    const { useBalanceQueryProgress } = await load();
    const { balanceProgress } = useBalanceQueryProgress();
    await nextTick();

    expect(get(balanceProgress)).toBeUndefined();
  });

  it('should build per-batch progress from the running and pending activities', async () => {
    set(activities, [
      balanceActivity('eth', ActivityStatus.RUNNING),
      balanceActivity('optimism', ActivityStatus.PENDING),
    ]);

    const { useBalanceQueryProgress } = await load();
    const { balanceProgress } = useBalanceQueryProgress();
    await nextTick();

    const progress = get(balanceProgress);
    expect(progress?.totalSteps).toBe(2);
    expect(progress?.currentStep).toBe(1);
    expect(progress?.percentage).toBe(0);
    expect(progress?.currentOperationData?.type).toBe(ActivityKind.BLOCKCHAIN_BALANCES);
    expect(progress?.currentOperationData?.chain).toBe('eth');
  });

  it('should count terminal members toward completed without dropping the batch total', async () => {
    set(activities, [
      balanceActivity('eth', ActivityStatus.RUNNING),
      balanceActivity('optimism', ActivityStatus.PENDING),
    ]);

    const { useBalanceQueryProgress } = await load();
    const { balanceProgress } = useBalanceQueryProgress();
    await nextTick();

    set(activities, [
      balanceActivity('eth', ActivityStatus.COMPLETE),
      balanceActivity('optimism', ActivityStatus.RUNNING),
    ]);
    await nextTick();

    const progress = get(balanceProgress);
    expect(progress?.totalSteps).toBe(2);
    expect(progress?.currentStep).toBe(2);
    expect(progress?.percentage).toBe(50);
    expect(progress?.currentOperationData?.chain).toBe('optimism');
  });
});
