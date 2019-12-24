import { MutationTree } from 'vuex';
import { defaultState, TaskMap, TaskState } from '@/store/tasks/state';
import { Task, TaskMeta } from '@/model/task';

export const mutations: MutationTree<TaskState> = {
  add: (state: TaskState, task: Task<TaskMeta>) => {
    const update: TaskMap<TaskMeta> = {};
    update[task.id] = task;
    state.tasks = { ...state.tasks, ...update };
  },
  remove: (state: TaskState, taskId: number) => {
    const tasks = { ...state.tasks };
    delete tasks[taskId];
    state.tasks = tasks;
  },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  reset: (state: TaskState) => {
    state = Object.assign(state, defaultState());
  }
};
