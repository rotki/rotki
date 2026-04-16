import type { StateHandler } from '../interfaces';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { createStateHandler } from '@/modules/messaging/utils';

export function createEventsStatusHandler(): StateHandler {
  // Capture store method at handler creation time (in setup context)
  const { setQueryStatus } = useEventsQueryStatusStore();

  return createStateHandler((data) => {
    setQueryStatus(data);
  });
}
