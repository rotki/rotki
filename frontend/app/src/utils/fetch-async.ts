import type { FetchData } from '@/types/fetch';
import type { TaskMeta } from '@/types/task';
import type { Ref } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils/index';
import { logger } from '@/utils/logging';
import { Severity } from '@rotki/common';

export async function fetchDataAsync<T extends TaskMeta, R>(data: FetchData<T, R>, state: Ref<R>): Promise<void> {
  if (
    !get(data.state.activeModules).includes(data.requires.module)
    || (data.requires.premium && !get(data.state.isPremium))
  ) {
    logger.debug(`module ${data.requires.module} inactive or not premium`);
    return;
  }
  const { awaitTask, isTaskRunning } = useTaskStore();

  const task = data.task;
  const { getStatus, setStatus } = useStatusUpdater(task.section);

  if (get(isTaskRunning(task.type, data.task.checkLoading)) || (getStatus() === Status.LOADED && !data.refresh)) {
    logger.debug(`${Section[data.task.section]} is already loading`);
    return;
  }

  setStatus(data.refresh ? Status.REFRESHING : Status.LOADING);

  try {
    const { taskId } = await task.query();
    const { result } = await awaitTask<R, T>(taskId, task.type, task.meta);
    set(state, task.parser ? task.parser(result) : result);
  }
  catch (error: any) {
    if (!isTaskCancelled(error)) {
      logger.error(`action failure for task ${TaskType[task.type]}:`, error);
      const { notify } = useNotificationsStore();
      notify({
        display: true,
        message: task.onError.error(error.message),
        severity: Severity.ERROR,
        title: task.onError.title,
      });
    }
  }
  setStatus(Status.LOADED);
}
