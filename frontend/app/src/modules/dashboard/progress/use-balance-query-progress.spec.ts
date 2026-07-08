import type { BalanceQueryQueueItem } from '@/modules/dashboard/progress/types';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useBalanceQueryProgress } from './use-balance-query-progress';

const completedItems = ref<number>(0);
const totalItems = ref<number>(0);
const runningItems = ref<number>(0);
const progress = ref<number>(0);
const queueItems = ref<BalanceQueryQueueItem[]>([]);
const runningTasks = ref<Set<TaskType>>(new Set());

vi.mock('@/modules/balances/use-balance-queue', () => ({
  useBalanceQueue: (): object => ({ completedItems, progress, queueItems, runningItems, totalItems }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChainName: (chain: string) => `Chain(${chain})` }),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: (): object => ({
    useIsTaskRunning: (type: TaskType) => computed<boolean>(() => get(runningTasks).has(type)),
  }),
}));

function item(overrides: Partial<BalanceQueryQueueItem>): BalanceQueryQueueItem {
  return {
    id: '1',
    type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
    chain: 'ethereum',
    status: 'pending',
    addedAt: 0,
    ...overrides,
  };
}

describe('useBalanceQueryProgress', () => {
  beforeEach(() => {
    set(completedItems, 0);
    set(totalItems, 0);
    set(runningItems, 0);
    set(progress, 0);
    set(queueItems, []);
    set(runningTasks, new Set());
  });

  describe('balanceProgress', () => {
    it('should be undefined when there are no items', () => {
      const { balanceProgress } = useBalanceQueryProgress();
      expect(get(balanceProgress)).toBeUndefined();
    });

    it('should describe a running blockchain balance query', () => {
      set(totalItems, 2);
      set(completedItems, 1);
      set(progress, 50);
      set(queueItems, [item({ status: 'running', chain: 'optimism' })]);
      const { balanceProgress } = useBalanceQueryProgress();
      const result = get(balanceProgress);
      expect(result?.currentStep).toBe(2);
      expect(result?.totalSteps).toBe(2);
      expect(result?.percentage).toBe(50);
      expect(result?.currentOperationData).toMatchObject({
        chain: 'optimism',
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
      });
    });

    it('should describe a running token detection', () => {
      set(totalItems, 1);
      set(completedItems, 0);
      set(queueItems, [item({ status: 'running', type: TaskType.FETCH_DETECTED_TOKENS, address: '0xabc' })]);
      const { balanceProgress } = useBalanceQueryProgress();
      const result = get(balanceProgress);
      expect(result?.currentStep).toBe(1);
      expect(result?.currentOperationData).toMatchObject({
        address: '0xabc',
        type: TaskType.FETCH_DETECTED_TOKENS,
      });
    });

    it('should describe the first pending item when nothing is running', () => {
      set(totalItems, 3);
      set(completedItems, 1);
      set(queueItems, [item({ status: 'pending', chain: 'base' })]);
      const { balanceProgress } = useBalanceQueryProgress();
      const result = get(balanceProgress);
      expect(result?.currentStep).toBe(1);
      expect(result?.currentOperationData).toMatchObject({ chain: 'base', status: 'pending' });
    });

    it('should be undefined when items exist but none are running or pending', () => {
      set(totalItems, 1);
      set(queueItems, [item({ status: 'completed' })]);
      const { balanceProgress } = useBalanceQueryProgress();
      expect(get(balanceProgress)).toBeUndefined();
    });
  });

  describe('isBalanceQuerying', () => {
    it('should be false when nothing is running', () => {
      const { isBalanceQuerying } = useBalanceQueryProgress();
      expect(get(isBalanceQuerying)).toBe(false);
    });

    it('should be true when a blockchain balance task runs', () => {
      set(runningTasks, new Set([TaskType.QUERY_BLOCKCHAIN_BALANCES]));
      const { isBalanceQuerying } = useBalanceQueryProgress();
      expect(get(isBalanceQuerying)).toBe(true);
    });

    it('should be true when the queue has running items', () => {
      set(runningItems, 1);
      const { isBalanceQuerying } = useBalanceQueryProgress();
      expect(get(isBalanceQuerying)).toBe(true);
    });
  });
});
