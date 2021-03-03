import { TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { SupportedModules } from '@/services/session/types';
import { PendingTask } from '@/services/types-api';
import { Section } from '@/store/const';

type GettersDefinition<S, G, RS, RG> = {
  [P in keyof G]: (
    state: S,
    getters: G,
    rootState: RS,
    rootGetters: RG
  ) => G[P];
};

export type Getters<S, G, RS, RG> = GettersDefinition<S, G, RS, RG>;

type OnError = {
  readonly title: string;
  readonly error: (message: string) => string;
};

export interface FetchPayload<T extends TaskMeta> {
  readonly module: SupportedModules;
  readonly section: Section;
  readonly refresh: boolean;
  readonly query: () => Promise<PendingTask>;
  readonly taskType: TaskType;
  readonly meta: T;
  readonly mutation: string;
  readonly checkPremium: boolean;
  readonly onError: OnError;
}
