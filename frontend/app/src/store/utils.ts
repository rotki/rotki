import { inject } from '@vue/composition-api';
import * as logger from 'loglevel';
import { ActionContext, Commit, Store } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { Section, Status } from '@/store/const';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import store from '@/store/store';
import { Message, RotkehlchenState, StatusPayload } from '@/store/types';
import { FetchPayload } from '@/store/typing';
import { assert } from '@/utils/assertions';

export async function fetchAsync<S, T extends TaskMeta, R>(
  {
    commit,
    rootGetters: { status },
    rootState: { session }
  }: ActionContext<S, RotkehlchenState>,
  payload: FetchPayload<T, R>
): Promise<void> {
  const { activeModules } = session!.generalSettings;
  if (
    !activeModules.includes(payload.module) ||
    (payload.checkPremium && !session!.premium)
  ) {
    return;
  }

  const section = payload.section;
  const currentStatus = status(section);

  if (
    isLoading(currentStatus) ||
    (currentStatus === Status.LOADED && !payload.refresh)
  ) {
    return;
  }

  const newStatus = payload.refresh ? Status.REFRESHING : Status.LOADING;
  setStatus(newStatus, section, status, commit);

  try {
    const { taskId } = await payload.query();
    const task = createTask(taskId, payload.taskType, payload.meta);
    commit('tasks/add', task, { root: true });
    const { result } = await taskCompletion<R, T>(payload.taskType);
    commit(payload.mutation, payload.parser ? payload.parser(result) : result);
  } catch (e: any) {
    logger.error(`action failure for task ${TaskType[payload.taskType]}:`, e);
    notify(
      payload.onError.error(e.message),
      payload.onError.title,
      Severity.ERROR,
      true
    );
  }
  setStatus(Status.LOADED, section, status, commit);
}

export function showError(description: string, title?: string) {
  const message = {
    title: title ?? i18n.t('message.error.title').toString(),
    description: description || '',
    success: false
  };
  store.commit('setMessage', message);
}

export function showMessage(description: string, title?: string): void {
  const message: Message = {
    title: title ?? i18n.t('message.success.title').toString(),
    description,
    success: true
  };
  store.commit('setMessage', message);
}

export const setStatus: (
  newStatus: Status,
  section: Section,
  status: (section: Section) => Status,
  commit: Commit
) => void = (newStatus, section, status, commit) => {
  if (status(section) === newStatus) {
    return;
  }
  const payload: StatusPayload = {
    section: section,
    status: newStatus
  };
  commit('setStatus', payload, { root: true });
};

export const getStatusUpdater = (
  commit: Commit,
  section: Section,
  getStatus: (section: Section) => Status
) => {
  const setStatus = (status: Status) => {
    if (getStatus(section) === status) {
      return;
    }
    const payload: StatusPayload = {
      section: section,
      status: status
    };
    commit('setStatus', payload, { root: true });
  };

  const loading = () => isLoading(getStatus(section));
  const isFirstLoad = () => getStatus(section) === Status.NONE;
  return {
    loading,
    isFirstLoad,
    setStatus
  };
};

export function isLoading(status: Status): boolean {
  return (
    status === Status.LOADING ||
    status === Status.PARTIALLY_LOADED ||
    status === Status.REFRESHING
  );
}

export interface AddressEntries<T> {
  readonly [address: string]: T;
}

export function filterAddresses<T>(
  entries: AddressEntries<T>,
  addresses: string[],
  item: (item: T) => void
) {
  for (const address in entries) {
    if (addresses.length > 0 && !addresses.includes(address)) {
      continue;
    }
    item(entries[address]);
  }
}

export function useStore(): Store<RotkehlchenState> {
  const store = inject<Store<RotkehlchenState>>('vuex-store');
  assert(store);
  return store;
}
