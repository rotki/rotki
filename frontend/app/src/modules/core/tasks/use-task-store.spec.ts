import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

describe('useTaskStore', () => {
  let store: ReturnType<typeof useTaskStore>;

  beforeEach((): void => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    store = useTaskStore();
    vi.clearAllMocks();
  });

  it('should remove a task', () => {
    store.addTask(1, 'Test task');
    expect(get(store.taskById)[1]).toBeDefined();
    store.remove(1);
    expect(get(store.taskById)[1]).toBeUndefined();
  });

  it('should lock and unlock a task', () => {
    store.addTask(1, 'Test task');
    store.lock(1);
    expect(get(store.locked).has(1)).toBe(true);
    store.unlock(1);
    expect(get(store.locked).has(1)).toBe(false);
  });

  it('should filter tasks into ready and unknown', () => {
    store.addTask(1, 'Test task');
    store.addTask(2, 'Test task');
    store.lock(2);

    const result = store.filterTasks([1, 2, 3]);
    expect(result.ready).toEqual([1]);
    expect(result.unknown).toEqual([3]);
  });

  it('should report hasRunningTasks correctly', () => {
    expect(get(store.hasRunningTasks)).toBe(false);
    store.addTask(1, 'Test task');
    expect(get(store.hasRunningTasks)).toBe(true);
    store.remove(1);
    expect(get(store.hasRunningTasks)).toBe(false);
  });

  it('should return task list', () => {
    store.addTask(1, 'Test task');
    store.addTask(2, 'Test task');
    const tasks = get(store.tasks);
    expect(tasks).toHaveLength(2);
    expect(tasks.map(t => t.id)).toEqual(expect.arrayContaining([1, 2]));
  });
});
