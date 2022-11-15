import { Ref } from 'vue';
import { PendingTask } from '@/services/types-api';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

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
