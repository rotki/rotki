import type { BackgroundTaskStatusData } from './background-task-types';
import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useBackgroundTasks } from './use-background-tasks';

/** Shows each backend task manager task as a dock row while it runs. */
export function createBackgroundTaskStatusHandler(): StateHandler<BackgroundTaskStatusData> {
  const { onStatus } = useBackgroundTasks();
  return createStateHandler<BackgroundTaskStatusData>(onStatus);
}
