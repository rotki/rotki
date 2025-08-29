import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/messaging/utils';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';

export function createEventsStatusHandler(): StateHandler {
  // Capture store method at handler creation time (in setup context)
  const { setQueryStatus } = useEventsQueryStatusStore();

  return createStateHandler((data) => {
    setQueryStatus(data);
  });
}
