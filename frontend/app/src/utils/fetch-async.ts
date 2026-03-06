import type { Ref } from 'vue';
import type { TaskMeta } from '@/modules/tasks/types';
import type { FetchData } from '@/types/fetch';
import { useStatusUpdater } from '@/composables/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { Section, Status } from '@/types/status';
import { logger } from '@/utils/logging';

export async function fetchDataAsync<T extends TaskMeta, R>(data: FetchData<T, R>, state: Ref<R>): Promise<void> {
  if (
    !get(data.state.activeModules).includes(data.requires.module)
    || (data.requires.premium && !get(data.state.isPremium))
  ) {
    logger.debug(`module ${data.requires.module} inactive or not premium`);
    return;
  }
  const { isTaskRunning } = useTaskStore();
  const { runTask } = useTaskHandler();

  const task = data.task;
  const { getStatus, setStatus } = useStatusUpdater(task.section);

  if (isTaskRunning(task.type, data.task.checkLoading) || (getStatus() === Status.LOADED && !data.refresh)) {
    logger.debug(`${Section[data.task.section]} is already loading`);
    return;
  }

  setStatus(data.refresh ? Status.REFRESHING : Status.LOADING);

  const outcome = await runTask<R, T>(
    async () => task.query(),
    { type: task.type, meta: task.meta, guard: false },
  );

  if (outcome.success) {
    set(state, task.parser ? task.parser(outcome.result) : outcome.result);
  }
  else if (isActionableFailure(outcome)) {
    logger.error(`action failure for task ${TaskType[task.type]}:`, outcome.error);
    const { notifyError } = useNotifications();
    notifyError(task.onError.title, task.onError.error(outcome.message));
  }
  setStatus(Status.LOADED);
}
