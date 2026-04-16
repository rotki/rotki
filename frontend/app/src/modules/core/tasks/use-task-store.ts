import type { Task, TaskMap, TaskMeta } from '@/modules/core/tasks/types';
import { assert } from '@rotki/common';
import dayjs from 'dayjs';
import { toArray } from 'es-toolkit/compat';
import { removeKey } from '@/modules/core/common/data/data';
import { TaskType } from '@/modules/core/tasks/task-type';

export const useTaskStore = defineStore('tasks', () => {
  const tasks = shallowRef<TaskMap<TaskMeta>>({});
  const locked = shallowRef<Set<number>>(new Set());
  const unknownTasks = shallowRef<Record<number, number>>({});
  const timeouts = shallowRef<Record<number, number>>({});

  const tasksByType = computed<Map<TaskType, Task<TaskMeta>[]>>(() => {
    const map = new Map<TaskType, Task<TaskMeta>[]>();
    for (const task of Object.values(get(tasks))) {
      const list = map.get(task.type);
      if (list)
        list.push(task);
      else
        map.set(task.type, [task]);
    }
    return map;
  });

  const hasRunningTasks = computed<boolean>(() => Object.keys(get(tasks)).length > 0);
  const hasUnknownTasks = computed<boolean>(() => Object.keys(get(unknownTasks)).length > 0);
  const taskList = computed<Task<TaskMeta>[]>(() => toArray(get(tasks)));

  function checkIfTaskIsRunning(
    groupedTasks: Map<TaskType, Task<TaskMeta>[]>,
    type: TaskType,
    meta: Record<string, any> = {},
  ): boolean {
    const typeTasks = groupedTasks.get(type);
    if (!typeTasks)
      return false;

    const keys = Object.keys(meta);
    if (keys.length === 0)
      return true;

    return typeTasks.some(item =>
      keys.every(
        key =>
        // @ts-expect-error meta key has any type
          key in item.meta && item.meta[key] === meta[key],
      ),
    );
  }

  function isTaskRunning(
    type: TaskType,
    meta: Record<string, any> = {},
  ): boolean {
    return checkIfTaskIsRunning(get(tasksByType), type, meta);
  }

  function useIsTaskRunning(
    type: TaskType,
    meta: MaybeRef<Record<string, any>> = {},
  ): ComputedRef<boolean> {
    return computed<boolean>(() => checkIfTaskIsRunning(get(tasksByType), type, get(meta)));
  }

  function add(task: Task<TaskMeta>): void {
    const update: TaskMap<TaskMeta> = {};
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

  function addTask<M extends TaskMeta>(id: number, type: TaskType, meta: M): void {
    assert(!(id === null || id === undefined), `missing id for ${TaskType[type]} with ${JSON.stringify(meta)}`);
    add({
      id,
      meta,
      time: dayjs().valueOf(),
      type,
    });
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
    isTaskRunning,
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
    useIsTaskRunning,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTaskStore, import.meta.hot));
