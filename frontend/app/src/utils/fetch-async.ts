import { Severity } from '@rotki/common/lib/messages';
import * as logger from 'loglevel';
import { Ref } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { FetchData } from '@/store/typing';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export async function fetchDataAsync<T extends TaskMeta, R>(
  data: FetchData<T, R>,
  state: Ref<R>
): Promise<void> {
  if (
    !get(data.state.activeModules).includes(data.requires.module) ||
    (data.requires.premium && !get(data.state.isPremium))
  ) {
    logger.debug('module inactive or not premium');
    return;
  }
  const { awaitTask, isTaskRunning } = useTasks();

  const task = data.task;
  const { getStatus, setStatus } = useStatusUpdater(task.section);

  if (
    get(isTaskRunning(task.type, data.task.checkLoading)) ||
    (getStatus() === Status.LOADED && !data.refresh)
  ) {
    logger.debug(`${Section[data.task.section]} is already loading`);
    return;
  }

  setStatus(data.refresh ? Status.REFRESHING : Status.LOADING);

  try {
    const { taskId } = await task.query();
    const { result } = await awaitTask<R, T>(taskId, task.type, task.meta);
    set(state, task.parser ? task.parser(result) : result);
  } catch (e: any) {
    logger.error(`action failure for task ${TaskType[task.type]}:`, e);
    const { notify } = useNotifications();
    notify({
      title: task.onError.title,
      message: task.onError.error(e.message),
      severity: Severity.ERROR,
      display: true
    });
  }
  setStatus(Status.LOADED);
}
