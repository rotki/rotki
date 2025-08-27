import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/messaging/utils';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';

export function createEventsStatusHandler(): StateHandler {
  return createStateHandler((data) => {
    const { setQueryStatus } = useEventsQueryStatusStore();
    setQueryStatus(data);
  });
}
