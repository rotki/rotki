import { type Ref } from 'vue';
import { type PendingTask, type TaskMeta } from '@/types/task';
import { type TaskType } from '@/types/task-type';
import { type Section } from '@/types/status';
import { type Module } from '@/types/modules';

export interface OnError {
  readonly title: string;
  readonly error: (message: string) => string;
}

export interface FetchData<T extends TaskMeta, R> {
  task: {
    type: TaskType;
    meta: T;
    section: Section;
    query: () => Promise<PendingTask>;
    parser?: (result: any) => R;
    onError: OnError;
    checkLoading?: Record<string, any>;
  };
  state: {
    isPremium: Ref<boolean>;
    activeModules: Ref<string[]>;
  };
  requires: {
    premium: boolean;
    module: Module;
  };
  refresh: boolean;
}
