import { z } from 'zod';

const BackgroundTaskStatus = {
  CANCELLED: 'cancelled',
  FAILED: 'failed',
  FINISHED: 'finished',
  STARTED: 'started',
} as const;

/** One running task manager task, as the periodic data lists it. `startedAt` is in seconds. */
export const BackgroundTask = z.object({
  name: z.string(),
  startedAt: z.number(),
});

/** A task manager task starting or ending. */
export const BackgroundTaskStatusData = BackgroundTask.extend({
  status: z.enum([
    BackgroundTaskStatus.CANCELLED,
    BackgroundTaskStatus.FAILED,
    BackgroundTaskStatus.FINISHED,
    BackgroundTaskStatus.STARTED,
  ]),
});

export type BackgroundTaskStatusData = z.infer<typeof BackgroundTaskStatusData>;
