import type { BackgroundTaskStatusData } from './background-task-types';
import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';

/** Accepts the backend's task manager status messages, which nothing shows yet. */
export function createBackgroundTaskStatusHandler(): StateHandler<BackgroundTaskStatusData> {
  return createStateHandler<BackgroundTaskStatusData>(() => {});
}
