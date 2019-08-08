import { MutationTree } from 'vuex';
import { createState, TaskMap, TaskState } from '@/store/tasks/state';
import { Task } from '@/model/task';
import { BalanceStatus } from '@/enums/BalanceStatus';

export const mutations: MutationTree<TaskState> = {
  add(state: TaskState, task: Task) {
    const update: TaskMap = {};
    update[task.id] = task;
    state.tasks = { ...state.tasks, ...update };
  },

  addBalanceTask(state: TaskState, task: Task) {
    const update: TaskMap = {};
    update[task.id] = task;
    state.tasks = { ...state.tasks, ...update };
    state.queryStatus = BalanceStatus.requested;
  },
  remove(state: TaskState, taskId: number) {},
  clear(state: TaskState) {
    state = createState();
  }
};
