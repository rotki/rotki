import type { TaskMeta } from '@/modules/core/tasks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

function getMeta(opts?: Partial<TaskMeta>): TaskMeta {
  return {
    title: '',
    ...opts,
  };
}

describe('useTaskStore', () => {
  let store: ReturnType<typeof useTaskStore>;

  beforeEach((): void => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    store = useTaskStore();
    vi.clearAllMocks();
  });

  it('should report task as not running', () => {
    store.addTask(1, TaskType.TX, getMeta());
    const importRunning = store.useIsTaskRunning(TaskType.IMPORT_CSV);
    expect(get(importRunning)).toBe(false);
  });

  it('should report task as running', () => {
    store.addTask(1, TaskType.TX, getMeta());
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    const manualBalancesRunning = store.useIsTaskRunning(TaskType.MANUAL_BALANCES_ADD);
    expect(get(manualBalancesRunning)).toBe(true);
  });

  it('should report task as running with strict meta check', () => {
    const meta = getMeta({
      title: 'test',
      description: 'test',
    });
    store.addTask(1, TaskType.TX, meta);
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    const txDefaultMeta = store.useIsTaskRunning(TaskType.TX, getMeta());
    const txSpecificMeta = store.useIsTaskRunning(TaskType.TX, meta);
    expect(get(txDefaultMeta)).toBe(false);
    expect(get(txSpecificMeta)).toBe(true);
  });

  it('should remove a task', () => {
    store.addTask(1, TaskType.TX, getMeta());
    expect(store.isTaskRunning(TaskType.TX)).toBe(true);
    store.remove(1);
    expect(store.isTaskRunning(TaskType.TX)).toBe(false);
  });

  it('should lock and unlock a task', () => {
    store.addTask(1, TaskType.TX, getMeta());
    store.lock(1);
    expect(get(store.locked).has(1)).toBe(true);
    store.unlock(1);
    expect(get(store.locked).has(1)).toBe(false);
  });

  it('should filter tasks into ready and unknown', () => {
    store.addTask(1, TaskType.TX, getMeta());
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    store.lock(2);

    const result = store.filterTasks([1, 2, 3]);
    expect(result.ready).toEqual([1]);
    expect(result.unknown).toEqual([3]);
  });

  it('should report hasRunningTasks correctly', () => {
    expect(get(store.hasRunningTasks)).toBe(false);
    store.addTask(1, TaskType.TX, getMeta());
    expect(get(store.hasRunningTasks)).toBe(true);
    store.remove(1);
    expect(get(store.hasRunningTasks)).toBe(false);
  });

  it('should return task list', () => {
    store.addTask(1, TaskType.TX, getMeta());
    store.addTask(2, TaskType.MANUAL_BALANCES_ADD, getMeta());
    const tasks = get(store.tasks);
    expect(tasks).toHaveLength(2);
    expect(tasks.map(t => t.id)).toEqual(expect.arrayContaining([1, 2]));
  });
});
