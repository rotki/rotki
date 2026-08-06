import type { ComputedRef } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { type Activity, ActivityKind, ActivitySourceType, ActivityStatus, makeActivityId, type WorkStatus } from '@/modules/task-center/core/types';

const mockAddRunning = ref<boolean>(false);
const mockRemoveRunning = ref<boolean>(false);

// Balance fetching is read off the live orchestrator activities now, not the task store.
const mockActivities = ref<Activity[]>([]);

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: (): Record<string, unknown> => ({ activities: mockActivities }),
}));

function fetchingActivity(chain: string): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain),
    kind: ActivityKind.BLOCKCHAIN_BALANCES,
    percentage: -1,
    rerunnable: true,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.RUNNING,
    title: 'balances',
  };
}

function activeFor(part?: string): boolean {
  if (part === 'add')
    return get(mockAddRunning);
  if (part === 'remove')
    return get(mockRemoveRunning);
  return false;
}

vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({
    useIsActivePrefix: (_kind: string, part?: string): ComputedRef<boolean> => computed<boolean>(() => activeFor(part)),
    useWorkStatusPrefix: (_kind: string, part?: string): ComputedRef<WorkStatus> => computed<WorkStatus>(() => {
      const active = activeFor(part);
      return { active, everCompleted: false, pending: false, running: active };
    }),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const vue = await import('vue');
  return {
    useSupportedChains: vi.fn(() => ({
      supportedChains: vue.ref([
        { id: 'eth', type: 'evm' },
        { id: 'optimism', type: 'evm' },
      ]),
    })),
  };
});

describe('useBlockchainAccountLoading', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(mockActivities, []);
    set(mockAddRunning, false);
    set(mockRemoveRunning, false);
  });

  async function importModule(): Promise<typeof import('./use-blockchain-account-loading')> {
    return import('./use-blockchain-account-loading');
  }

  it('should report every flag as idle when nothing is happening', async () => {
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    expect(get(loading.isSectionLoading)).toBe(false);
    expect(get(loading.operationRunning)).toBe(false);
    expect(get(loading.isDetectingTokens)).toBe(false);
    expect(get(loading.refreshDisabled)).toBe(false);
    expect(get(loading.deleteDisabled)).toBe(false);
    expect(get(loading.isLoadingActive)).toBe(false);
  });

  it('should be section loading while any chain is fetching balances', async () => {
    set(mockActivities, [fetchingActivity('eth')]);
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    expect(get(loading.isSectionLoading)).toBe(true);
    expect(get(loading.refreshDisabled)).toBe(true);
    expect(get(loading.isLoadingActive)).toBe(true);
  });

  it('should be section loading when a chain is refreshing', async () => {
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    useBalanceRefreshState().start('eth');
    expect(get(loading.isSectionLoading)).toBe(true);
  });

  it('should flag a running add/remove operation', async () => {
    set(mockAddRunning, true);
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    expect(get(loading.operationRunning)).toBe(true);
    expect(get(loading.deleteDisabled)).toBe(true);
    expect(get(loading.isLoadingActive)).toBe(true);
  });

  it('should disable delete while balances are fetching', async () => {
    set(mockActivities, [fetchingActivity('eth')]);
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading();
    expect(get(loading.deleteDisabled)).toBe(true);
  });

  it('should detect tokens for an evm category when mass detection runs', async () => {
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading('evm');
    useTokenDetectionStore().setMassDetecting('eth');
    expect(get(loading.isDetectingTokens)).toBe(true);
    expect(get(loading.refreshDisabled)).toBe(true);
  });

  it('should not detect tokens for a non-evm category', async () => {
    const { useBlockchainAccountLoading } = await importModule();
    const loading = useBlockchainAccountLoading('bitcoin');
    useTokenDetectionStore().setMassDetecting('eth');
    expect(get(loading.isDetectingTokens)).toBe(false);
  });
});
