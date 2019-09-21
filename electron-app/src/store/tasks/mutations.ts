import { MutationTree } from 'vuex';
import { defaultState, TaskMap, TaskState } from '@/store/tasks/state';
import { Task } from '@/model/task';
import { BalanceStatus } from '@/enums/BalanceStatus';

export const mutations: MutationTree<TaskState> = {
  add: (state: TaskState, task: Task) => {
    const update: TaskMap = {};
    update[task.id] = task;
    state.tasks = { ...state.tasks, ...update };
  },
  addBalanceTask: (state: TaskState, task: Task) => {
    const update: TaskMap = {};
    update[task.id] = task;
    state.tasks = { ...state.tasks, ...update };
    state.balanceTasks.push(task.id);
    state.queryStatus = BalanceStatus.requested;
  },
  remove: (state: TaskState, taskId: number) => {
    const tasks = { ...state.tasks };
    delete tasks[taskId];
    state.tasks = tasks;
  },
  removeBalanceTask: (state: TaskState, taskId: number) => {
    const balanceTasks = [...state.balanceTasks];
    const taskIndex = balanceTasks.indexOf(taskId);
    if (taskIndex > -1) {
      balanceTasks.splice(taskIndex, 1);
    }
    state.balanceTasks = balanceTasks;
  },
  reset: (state: TaskState) => {
    state = Object.assign(state, defaultState());
  },
  status: (state: TaskState, status: BalanceStatus) => {
    state.queryStatus = status;
  }
};
