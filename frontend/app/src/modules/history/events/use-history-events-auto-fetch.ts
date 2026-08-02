import { startPromise } from '@shared/utils';
import { type MaybeRefOrGetter, shallowRef } from 'vue';
import { ActivityKind, useTaskCenter } from '@/modules/task-center/use-task-center';

/**
 * How long decoding has to go quiet before the table reads. Short, because a pause usually means a
 * chain just finished and its events are ready to show.
 */
const SETTLE_QUIET = 2000;

/**
 * The longest the table will go without reading while decoding keeps reporting. Bounds the
 * sustained case: continuous progress must not become a continuous stream of reads, but the user
 * should still see the table filling rather than sitting still through a long run.
 */
const SUSTAINED_MAX_WAIT = 20_000;

/**
 * The activity kinds that can put rows in the events table. Deliberately not every kind: a balance
 * or price refresh finishing is not a reason to re-read the events.
 */
const EVENT_PRODUCING_KINDS: ReadonlySet<ActivityKind> = new Set([
  ActivityKind.TX_SYNC,
  ActivityKind.TX_DECODING,
  ActivityKind.REDECODE,
  ActivityKind.ETH_BLOCK_DECODING,
  ActivityKind.REPULLING,
  ActivityKind.EXCHANGE_EVENTS,
  ActivityKind.ONLINE_EVENTS,
]);

export interface HistoryEventsAutoFetchHandlers {
  /**
   * Runs on every progress tick. Reads the events only — the location set cannot change while a
   * decode is mid-flight, so pulling it here multiplied every tick by three requests.
   */
  onProgress: () => Promise<void>;
  /**
   * Runs once when the run ends. The location set CAN change across a flow boundary: a chain whose
   * transactions were pulled but never successfully decoded has no `history_events` rows, so its
   * first successful decode adds a location (`Location.from_chain_id`, decoding/base.py) — and a
   * decode that fails can leave a location's last event deleted (`delete_location_events`).
   */
  onSettle: () => Promise<void>;
}

export interface UseHistoryEventsAutoFetchReturn {
  /**
   * Report that something outside decoding changed the events (matching, an external write). Joins
   * the same debounce as decode progress so two signals arriving together read the table once.
   */
  markStale: () => void;
}

/**
 * Refetch the events table while history work is producing events.
 *
 * This was a blind 60-second interval that had no idea whether anything had been produced. It then
 * followed decode progress over the websocket, which turned out to be the wrong signal: the backend
 * emits it only every tenth transaction, bitcoin has no decoder emitting it at all, it is gated
 * behind a `send_ws_notifications` flag that defaults off, and the store it lands in is reset
 * part-way through a run — so the counter it was derived from both skipped work and went backwards.
 *
 * The reliable fact is that a unit of work *finished*. Every event-producing operation is an
 * activity, the orchestrator already tracks each one to completion, and a completion is exactly the
 * moment new rows exist and are worth showing. That covers bitcoin, exchanges and online events,
 * and chains too small to ever report progress.
 *
 * Still gated on `shouldFetch`: the caller passes "history work is in flight", so an idle session
 * fetches nothing.
 */
export function useHistoryEventsAutoFetch(
  shouldFetch: MaybeRefOrGetter<boolean>,
  handlers: HistoryEventsAutoFetchHandlers,
): UseHistoryEventsAutoFetchReturn {
  const isFetching = shallowRef<boolean>(false);
  const { active } = useTaskCenter();

  /** How many event-producing activities are still running; a fall means one of them finished. */
  const runningProducers = computed<number>(() =>
    get(active).filter(activity => EVENT_PRODUCING_KINDS.has(activity.kind)).length,
  );

  function read(): void {
    if (get(isFetching))
      return;

    set(isFetching, true);
    startPromise(handlers.onProgress().finally(() => {
      set(isFetching, false);
    }));
  }

  // One reader behind one debounce, shared by every staleness signal.
  //
  // Debounced, not throttled: a throttle reads on a fixed cadence for as long as work continues,
  // which is the polling this replaced wearing a different hat. Debouncing reads when the signals
  // *pause* — normally a chain finishing — and `maxWait` keeps a long uninterrupted run from
  // starving the table entirely. Idle signals nothing, so idle reads nothing.
  //
  // Sharing matters: decode progress and event modifications used to own separate debounces and
  // landed on the same instant, so the table read the identical page twice. Measured on a
  // redecode-all, every read had a partner within the same second, 23 times over.
  const scheduleRead = useDebounceFn(read, SETTLE_QUIET, { maxWait: SUSTAINED_MAX_WAIT });

  watch(runningProducers, (current, previous) => {
    // Only on a fall: work starting produces nothing, work finishing does. Gated here rather than
    // inside the reader, because other signals are live while nothing is running.
    if (current < (previous ?? 0) && toValue(shouldFetch))
      startPromise(scheduleRead());
  });

  // The run ending still needs one read: the last progress message can arrive while a read is in
  // flight, and would otherwise be dropped by the guard above. This is also the only point at
  // which the location set is re-read, so a chain that decoded for the first time shows up.
  watch(() => toValue(shouldFetch), (fetching, wasFetching) => {
    if (wasFetching && !fetching)
      startPromise(handlers.onSettle());
  });

  return {
    markStale: (): void => {
      startPromise(scheduleRead());
    },
  };
}
