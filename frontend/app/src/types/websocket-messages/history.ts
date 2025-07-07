import { z } from 'zod/v4';

export const HistoryEventsQueryStatus = {
  QUERYING_EVENTS_FINISHED: 'querying_events_finished',
  QUERYING_EVENTS_STARTED: 'querying_events_started',
  QUERYING_EVENTS_STATUS_UPDATE: 'querying_events_status_update',
} as const;

export type HistoryEventsQueryStatus = (typeof HistoryEventsQueryStatus)[keyof typeof HistoryEventsQueryStatus];

export const HistoryEventsQueryData = z.object({
  eventType: z.string(),
  location: z.string(),
  name: z.string(),
  period: z.tuple([z.number(), z.number()]).optional(),
  status: z.enum(HistoryEventsQueryStatus),
});

export type HistoryEventsQueryData = z.infer<typeof HistoryEventsQueryData>;
