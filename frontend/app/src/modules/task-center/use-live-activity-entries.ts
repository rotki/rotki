import type { ActivityKind } from './core/types';
import { useTaskOrchestrator } from './use-task-orchestrator';

/** An activity, named the way `statusOf` addresses it: a descriptor's `kind` and `partsOf(subject)`. */
export interface ActivityAddress {
  readonly kind: ActivityKind;
  readonly parts: readonly (string | number)[];
}

interface UseLiveActivityEntriesReturn<T> {
  /** Whether the activity is running or queued. A message for one that is not has nothing left to update. */
  isLive: (address: ActivityAddress) => boolean;
  read: (address: ActivityAddress) => T | undefined;
  write: (address: ActivityAddress, value: T) => void;
}

/**
 * State kept per activity for exactly as long as that activity is active.
 *
 * @remarks
 * For readers that fold a stream of messages into one value per activity, such as a query's range
 * carried from frame to frame. An entry is dropped as soon as its activity settles, so the next run
 * starts from nothing, and a message that arrives after a cancel finds no live activity to revive.
 *
 * Pruned on every orchestrator change. That stays cheap because only active activities keep an
 * entry, and it stops with the scope that created it.
 */
export function useLiveActivityEntries<T>(): UseLiveActivityEntriesReturn<T> {
  const { onChange, statusOf } = useTaskOrchestrator();
  const entries = new Map<string, { address: ActivityAddress; value: T }>();

  const keyOf = ({ kind, parts }: ActivityAddress): string => JSON.stringify([kind, ...parts]);

  function isLive({ kind, parts }: ActivityAddress): boolean {
    return statusOf(kind, ...parts).active;
  }

  function prune(): void {
    for (const [key, entry] of entries) {
      if (!isLive(entry.address))
        entries.delete(key);
    }
  }

  tryOnScopeDispose(onChange(prune));

  return {
    isLive,
    read: address => entries.get(keyOf(address))?.value,
    write: (address, value): void => {
      entries.set(keyOf(address), { address, value });
    },
  };
}
