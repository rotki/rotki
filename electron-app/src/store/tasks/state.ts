import { Task } from '@/model/task';
import { BalanceStatus } from '@/enums/BalanceStatus';

export interface TaskState {
  balanceTasks: number[];
  tasks: TaskMap;
  queryStatus: BalanceStatus;
}

export interface TaskMap {
  [taskId: number]: Task;
}

export const defaultState: () => TaskState = () => ({
  balanceTasks: [],
  tasks: {},
  queryStatus: BalanceStatus.start
});

export const state: TaskState = defaultState();
