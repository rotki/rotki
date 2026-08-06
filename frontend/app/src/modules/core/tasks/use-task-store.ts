import type { Task, TaskMap } from '@/modules/core/tasks/types';
import { assert } from '@rotki/common';
import { toArray } from 'es-toolkit/compat';
import { removeKey } from '@/modules/core/common/data/data';

export const useTaskStore = defineStore('tasks', () => {
  const tasks = shallowRef<TaskMap>({});
  const locked = shallowRef<Set<number>>(new Set());
  const unknownTasks = shallowRef<Record<number, number>>({});
  const timeouts = shallowRef<Record<number, number>>({});

  const hasRunningTasks = computed<boolean>(() => Object.keys(get(tasks)).length > 0);
  const hasUnknownTasks = computed<boolean>(() => Object.keys(get(unknownTasks)).length > 0);
  const taskList = computed<Task[]>(() => toArray(get(tasks)));

  function add(task: Task): void {
    const update: TaskMap = {};
    update[task.id] = task;
    set(tasks, { ...get(tasks), ...update });
  }

  function lock(taskId: number): void {
    const next = new Set(get(locked));
    next.add(taskId);
    set(locked, next);
  }

  function unlock(taskId: number): void {
    const next = new Set(get(locked));
    next.delete(taskId);
    set(locked, next);
  }

  function remove(taskId: number): void {
    set(tasks, removeKey(get(tasks), taskId));
    set(timeouts, removeKey(get(timeouts), taskId));
    unlock(taskId);
  }

  function addTask(id: number, label: string): void {
    assert(!(id === null || id === undefined), `missing id for task ${label}`);
    add({ id, label });
  }

  function removeFromUnknownTasks(taskId: number): void {
    const unknown = { ...get(unknownTasks) };
    if (!unknown[taskId])
      return;

    delete unknown[taskId];
    set(unknownTasks, unknown);
  }

  function setTimeoutCount(taskId: number, count: number): void {
    set(timeouts, { ...get(timeouts), [taskId]: count });
  }

  function getTimeoutCount(taskId: number): number {
    return get(timeouts)[taskId] ?? 0;
  }

  function setUnknownTasks(updated: Record<number, number>): void {
    set(unknownTasks, updated);
  }

  function filterTasks(taskIds: number[]): { ready: number[]; unknown: number[] } {
    const lockedSet = get(locked);
    const pendingTasks = get(tasks);
    return {
      ready: taskIds.filter(id => !lockedSet.has(id) && pendingTasks[id] && pendingTasks[id].id !== null),
      unknown: taskIds.filter(id => !lockedSet.has(id) && !pendingTasks[id]),
    };
  }

  return {
    add,
    addTask,
    filterTasks,
    getTimeoutCount,
    hasRunningTasks,
    hasUnknownTasks,
    lock,
    locked,
    remove,
    removeFromUnknownTasks,
    setTimeoutCount,
    setUnknownTasks,
    taskById: tasks,
    tasks: taskList,
    unknownTasks,
    unlock,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTaskStore, import.meta.hot));
