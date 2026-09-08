import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';

export function createEventsStatusHandler(): StateHandler {
  const { setQueryStatus } = useEventsQueryStatusStore();

  return createStateHandler((data) => {
    setQueryStatus(data);
  });
}
