import { Severity } from '@rotki/common/lib/messages';
import * as logger from 'loglevel';
import { Section, Status } from '@/types/status';
import { type TaskMeta, UserCancelledTaskError } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type FetchData } from '@/types/fetch';

export async function fetchDataAsync<T extends TaskMeta, R>(
  data: FetchData<T, R>,
  state: Ref<R>
): Promise<void> {
  if (
    !get(data.state.activeModules).includes(data.requires.module) ||
    (data.requires.premium && !get(data.state.isPremium))
  ) {
    logger.debug(`module ${data.requires.module} inactive or not premium`);
    return;
  }
  const { awaitTask, isTaskRunning } = useTaskStore();

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
    if (e instanceof UserCancelledTaskError) {
      logger.debug(e);
    } else {
      logger.error(`action failure for task ${TaskType[task.type]}:`, e);
      const { notify } = useNotificationsStore();
      notify({
        title: task.onError.title,
        message: task.onError.error(e.message),
        severity: Severity.ERROR,
        display: true
      });
    }
  }
  setStatus(Status.LOADED);
}
