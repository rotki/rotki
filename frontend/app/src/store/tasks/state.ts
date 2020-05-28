import { Task, TaskMeta } from '@/model/task';

export interface TaskState {
  tasks: TaskMap<TaskMeta>;
  locked: number[];
}

export interface TaskMap<T extends TaskMeta> {
  [taskId: number]: Task<T>;
}

export const defaultState: () => TaskState = () => ({
  tasks: {},
  locked: []
});

export const state: TaskState = defaultState();
