import find from 'lodash/find';
import toArray from 'lodash/toArray';
import { GetterTree } from 'vuex';
import { Task, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { RotkehlchenState } from '@/store/store';
import { TaskState } from '@/store/tasks/state';

export type TaskGetters = {
  isTaskRunning: (type: TaskType) => boolean;
  metadata: (type: TaskType) => TaskMeta | undefined;
  hasRunningTasks: boolean;
  tasks: Task<TaskMeta>[];
};

type GettersDefinition<S = TaskState, G = TaskGetters> = {
  [P in keyof G]: (state: S, getters: G) => G[P];
};

export const getters: GetterTree<TaskState, RotkehlchenState> &
  GettersDefinition = {
  isTaskRunning: (state: TaskState) => (type: TaskType): boolean => {
    return !!find(state.tasks, item => item.type === type);
  },

  metadata: (state: TaskState) => (type: TaskType): TaskMeta | undefined => {
    const task = find(state.tasks, item => item.type === type);
    if (task) {
      return task.meta;
    }
    return undefined;
  },

  hasRunningTasks: (state: TaskState): boolean => {
    return Object.keys(state.tasks).length > 0;
  },

  tasks: (state: TaskState): Task<TaskMeta>[] => {
    return toArray(state.tasks);
  }
};
