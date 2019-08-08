import { Task } from '@/model/task';
import { BalanceStatus } from '@/enums/BalanceStatus';

export const createState: () => TaskState = () => ({
  balanceTasks: [],
  tasks: {},
  queryStatus: BalanceStatus.start
});

export const state: TaskState = createState();

export interface TaskState {
  balanceTasks: number[];
  tasks: TaskMap;
  queryStatus: BalanceStatus;
}

export interface TaskMap {
  [taskId: number]: Task;
}
