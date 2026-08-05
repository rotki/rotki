import type { QueuedRequest } from './types';
import { isBackgroundPriority } from './request-priority';

/**
 * The first queued request allowed to start right now, which is not always the head: once
 * background work holds its share of the slots, the queue is scanned past it for work that still
 * may run. Returns -1 when only capped background requests are waiting.
 *
 * This is what priority alone cannot do. Priority orders the queue, and a queue cannot reorder
 * slots that are already occupied - six advisory lookups that hang take every slot and stop the
 * app, user actions included.
 */
export function findEligibleIndex(
  queue: readonly QueuedRequest[],
  active: Iterable<QueuedRequest>,
  maxBackgroundConcurrent: number,
): number {
  let background = 0;
  for (const request of active) {
    if (isBackgroundPriority(request.priority))
      background++;
  }

  if (background < maxBackgroundConcurrent)
    return queue.length > 0 ? 0 : -1;

  return queue.findIndex(request => !isBackgroundPriority(request.priority));
}
