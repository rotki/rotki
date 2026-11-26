import { get } from '@vueuse/shared';
import { useRoute } from 'vue-router';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';

/**
 * Returns a reader for the events table that runs one read at a time and folds callers that
 * arrive together into one.
 *
 * @remarks
 * `useTableData.refetch` opens with `api.cancelByTag`, so overlapping reads cancel each other
 * onto one shared `useAsyncState` and the table can end up holding the loser's result, which
 * empties the table when it is empty. So reads never overlap.
 *
 * A caller arriving while a read runs gets a follow-up read, since the running one may predate
 * what it wants to see. Callers arriving while that follow-up waits join it: it starts after they
 * called, so it shows what each of them wants. At most one read runs and one waits, however many
 * watchers fire at the end of a run. A rejected read does not block the next.
 *
 * Each read also reloads the customized event duplicates when the route asks for event groups.
 */
export function useHistoryEventsTableRead(fetchEventsData: () => Promise<void>): () => Promise<void> {
  const route = useRoute();
  const { fetchCustomizedEventDuplicates } = useCustomizedEventDuplicates();

  async function readTable(): Promise<void> {
    await fetchEventsData();
    if (get(route).query.groupIdentifiers)
      await fetchCustomizedEventDuplicates();
  }

  let running: Promise<void> | undefined;
  let waiting: Promise<void> | undefined;

  async function startRead(): Promise<void> {
    const read = readTable().finally(() => {
      if (running === read)
        running = undefined;
    });
    running = read;
    return read;
  }

  return async function fetchData(): Promise<void> {
    if (waiting)
      return waiting;

    if (!running)
      return startRead();

    const next = running.catch(() => {}).then(async () => {
      waiting = undefined;
      return startRead();
    });
    waiting = next;
    return next;
  };
}
