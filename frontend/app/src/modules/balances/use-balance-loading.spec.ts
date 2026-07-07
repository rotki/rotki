import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskType as Task, type TaskType } from '@/modules/core/tasks/task-type';
import { useBalancesLoading } from './use-balance-loading';

const running = ref<Set<TaskType>>(new Set());

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: (): object => ({
    useIsTaskRunning: (type: TaskType) => computed<boolean>(() => get(running).has(type)),
  }),
}));

describe('useBalancesLoading', () => {
  beforeEach(() => {
    set(running, new Set());
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should not be loading when no relevant task runs', () => {
    const { loadingBalances, loadingBalancesAndDetection } = useBalancesLoading();
    expect(get(loadingBalances)).toBe(false);
    expect(get(loadingBalancesAndDetection)).toBe(false);
  });

  it.each([
    Task.QUERY_BALANCES,
    Task.QUERY_BLOCKCHAIN_BALANCES,
    Task.QUERY_EXCHANGE_BALANCES,
    Task.MANUAL_BALANCES,
  ])('should flag loading when %s runs', (task) => {
    const { loadingBalances, loadingBalancesAndDetection } = useBalancesLoading();
    set(running, new Set([task]));
    expect(get(loadingBalances)).toBe(true);
    expect(get(loadingBalancesAndDetection)).toBe(true);
  });

  it('should include token detection only in the detection flag', () => {
    const { loadingBalances, loadingBalancesAndDetection } = useBalancesLoading();
    set(running, new Set([Task.FETCH_DETECTED_TOKENS]));
    expect(get(loadingBalances)).toBe(false);
    expect(get(loadingBalancesAndDetection)).toBe(true);
  });
});
