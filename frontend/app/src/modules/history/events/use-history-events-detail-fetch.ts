import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { startPromise } from '@shared/utils';
import { watchImmediate } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { computed, type MaybeRefOrGetter, readonly, type Ref, ref, shallowReadonly, shallowRef, toValue, watch } from 'vue';
import { isRequestFailure, type RequestFailure } from '@/modules/core/api/request-result';
import { api } from '@/modules/core/api/rotki-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

interface UseHistoryEventsDetailFetchOptions {
  /** The groups on the current page; their group identifiers scope the fetch and any change retriggers it. */
  data: MaybeRefOrGetter<HistoryEventRow[]>;
  /** Current filter payload, reused as the base of the event fetch so the detail query matches the group query. */
  requestPayload: MaybeRefOrGetter<HistoryEventRequestPayload | undefined>;
  /** Restricts the event fetch to these identifiers; undefined loads every event belonging to the groups on the current page. */
  identifiers?: MaybeRefOrGetter<string[] | undefined>;
  /** Whether the caller is fetching groups; turning true cancels the in-flight event fetch. */
  groupLoading: MaybeRefOrGetter<boolean>;
}

interface UseHistoryEventsDetailFetchReturn {
  events: Readonly<Ref<HistoryEventRow[]>>;
  eventsLoading: Readonly<Ref<boolean>>;
  /** Why the events of the groups on screen failed to load; the groups stay, their events are cleared. */
  eventsError: Readonly<Ref<RequestFailure | undefined>>;
  fetchEvents: () => Promise<void>;
}

const EVENTS_CANCEL_TAG = 'history-events-detail';

/**
 * Loads the events of the groups on the current page, refetching whenever the groups change and
 * cancelling the in-flight request as soon as a new groups fetch starts.
 */
export function useHistoryEventsDetailFetch(options: UseHistoryEventsDetailFetchOptions): UseHistoryEventsDetailFetchReturn {
  const { data, groupLoading, identifiers, requestPayload } = options;

  const eventsLoading = shallowRef<boolean>(false);
  const eventsError = shallowRef<RequestFailure>();
  const events = ref<HistoryEventRow[]>([]);
  let fetchVersion = 0;

  const { fetchHistoryEvents } = useHistoryEvents();

  const groupIdentifiers = computed<string[]>(() =>
    toValue(data).flatMap(item => Array.isArray(item) ? item.map(i => i.groupIdentifier) : item.groupIdentifier),
  );

  /**
   * Fetches every event belonging to the groups currently on screen.
   *
   * @remarks
   * `limit: -1` lifts the page bound, which stays safe because `groupIdentifiers` already narrows
   * the request to the groups the visible page holds. A later call supersedes an in-flight one:
   * the response is discarded unless its version is still the current one.
   */
  async function fetchEvents(): Promise<void> {
    const groupIds = get(groupIdentifiers);
    if (groupIds.length === 0) {
      set(events, []);
      return;
    }

    const currentVersion = ++fetchVersion;
    set(eventsLoading, true);
    set(eventsError, undefined);
    api.cancelByTag(EVENTS_CANCEL_TAG);

    const response = await fetchHistoryEvents({
      ...toValue(requestPayload),
      aggregateByGroupIds: false,
      excludeIgnoredAssets: false,
      groupIdentifiers: groupIds,
      identifiers: toValue(identifiers),
      limit: -1,
      offset: 0,
    }, { tags: [EVENTS_CANCEL_TAG] });

    if (currentVersion !== fetchVersion)
      return;

    set(eventsLoading, false);

    if (response.ok) {
      set(events, response.value.data);
    }
    else if (isRequestFailure(response.error)) {
      logger.error(response.error.cause);
      set(events, []);
      set(eventsError, response.error);
    }
  }

  // Cancel stale events fetch as soon as new groups fetch starts
  watch(() => toValue(groupLoading), (loading) => {
    if (loading)
      api.cancelByTag(EVENTS_CANCEL_TAG);
  });

  // Trigger events fetch when groups change (tied to fetchData completion in pagination filter)
  watchImmediate(() => toValue(data), () => {
    startPromise(fetchEvents());
  });

  return {
    events: shallowReadonly(events),
    eventsError: shallowReadonly(eventsError),
    eventsLoading: readonly(eventsLoading),
    fetchEvents,
  };
}
