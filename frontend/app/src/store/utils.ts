import { inject } from '@vue/composition-api';
import * as logger from 'loglevel';
import { ActionContext, Commit, Store } from 'vuex';
import i18n from '@/i18n';
import { Section, Status } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { Severity } from '@/store/notifications/consts';
import store from '@/store/store';
import { useTasks } from '@/store/tasks';
import { Message, RotkehlchenState, StatusPayload } from '@/store/types';
import { FetchPayload } from '@/store/typing';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
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

  const { awaitTask } = useTasks();

  try {
    const { taskId } = await payload.query();
    const { result } = await awaitTask<R, T>(
      taskId,
      payload.taskType,
      payload.meta
    );
    commit(payload.mutation, payload.parser ? payload.parser(result) : result);
  } catch (e: any) {
    logger.error(`action failure for task ${TaskType[payload.taskType]}:`, e);
    const { notify } = useNotifications();
    notify({
      title: payload.onError.title,
      message: payload.onError.error(e.message),
      severity: Severity.ERROR,
      display: true
    });
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
  getStatus: (section: Section) => Status,
  ignore: boolean = false
) => {
  const setStatus = (status: Status, otherSection?: Section) => {
    if (getStatus(section) === status) {
      return;
    }
    const payload: StatusPayload = {
      section: otherSection ?? section,
      status: status
    };
    if (!ignore) {
      commit('setStatus', payload, { root: true });
    }
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
