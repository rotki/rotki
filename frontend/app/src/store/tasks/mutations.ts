import { MutationTree } from 'vuex';
import { Task, TaskMeta } from '@/model/task';
import { defaultState, TaskMap, TaskState } from '@/store/tasks/state';

const unlockTask = (state: TaskState, taskId: number) => {
  const locked = [...state.locked];
  const idIndex = locked.findIndex(value => value === taskId);
  locked.splice(idIndex, 1);
  return locked;
};

export const mutations: MutationTree<TaskState> = {
  add: (state: TaskState, task: Task<TaskMeta>) => {
    const update: TaskMap<TaskMeta> = {};
    update[task.id] = task;
    state.tasks = { ...state.tasks, ...update };
  },
  lock: (state: TaskState, taskId: number) => {
    state.locked = [...state.locked, taskId];
  },
  unlock: (state: TaskState, taskId: number) => {
    state.locked = unlockTask(state, taskId);
  },
  remove: (state: TaskState, taskId: number) => {
    const tasks = { ...state.tasks };
    delete tasks[taskId];
    state.tasks = tasks;
    state.locked = unlockTask(state, taskId);
  },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  reset: (state: TaskState) => {
    state = Object.assign(state, defaultState());
  }
};
