import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';

export function createEventsStatusHandler(): StateHandler {
  // Capture store method at handler creation time (in setup context)
  const { setQueryStatus } = useEventsQueryStatusStore();

  return createStateHandler((data) => {
    setQueryStatus(data);
  });
}
