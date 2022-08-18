import { Ref } from '@vue/composition-api';
import { PendingTask } from '@/services/types-api';
import { Section } from '@/store/const';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

type GettersDefinition<S, G, RS, RG> = {
  [P in keyof G]: (
    state: S,
    getters: G,
    rootState: RS,
    rootGetters: RG
  ) => G[P];
};

export type Getters<S, G, RS, RG> = GettersDefinition<S, G, RS, RG>;

export type OnError = {
  readonly title: string;
  readonly error: (message: string) => string;
};

export type FetchData<T extends TaskMeta, R> = {
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
};

export interface FetchPayload<T extends TaskMeta, R> {
  readonly module: Module;
  readonly section: Section;
  readonly refresh: boolean;
  readonly query: () => Promise<PendingTask>;
  readonly taskType: TaskType;
  readonly meta: T;
  readonly checkPremium: boolean;
  readonly onError: OnError;
  readonly parser?: (result: any) => R;
  readonly mutation: string;
}
