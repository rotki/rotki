import { Task, TaskMeta } from '@/model/task';

export interface TaskState {
  tasks: TaskMap<TaskMeta>;
  processingTasks: number[];
}

export interface TaskMap<T extends TaskMeta> {
  [taskId: number]: Task<T>;
}

export const defaultState: () => TaskState = () => ({
  tasks: {},
  processingTasks: []
});

export const state: TaskState = defaultState();
