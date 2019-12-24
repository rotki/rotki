import { Task, TaskMeta } from '@/model/task';

export interface TaskState {
  tasks: TaskMap<TaskMeta>;
}

export interface TaskMap<T extends TaskMeta> {
  [taskId: number]: Task<T>;
}

export const defaultState: () => TaskState = () => ({
  tasks: {}
});

export const state: TaskState = defaultState();
