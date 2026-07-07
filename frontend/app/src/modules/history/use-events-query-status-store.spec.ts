import { beforeEach, describe, expect, it } from 'vitest';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/modules/core/messaging/types';
import { useEventsQueryStatusStore } from './use-events-query-status-store';

function data(
  location: string,
  name: string,
  status: HistoryEventsQueryStatus,
): HistoryEventsQueryData {
  return { eventType: '', location, name, period: [0, 100], status };
}

describe('useEventsQueryStatusStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should mark started/finished statuses correctly', () => {
    const store = useEventsQueryStatusStore();
    expect(store.isStatusFinished(data('eth', 'a', HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED))).toBe(false);
    expect(store.isStatusFinished(data('eth', 'a', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED))).toBe(true);
    expect(store.isStatusFinished(data('eth', 'a', HistoryEventsQueryStatus.CANCELLED))).toBe(true);
  });

  it('should initialize a started status for each location and begin syncing', () => {
    const store = useEventsQueryStatusStore();
    store.initializeQueryStatus([{ location: 'eth', name: 'a' }, { location: 'btc', name: 'b' }]);

    expect(get(store.syncing)).toBe(true);
    const status = get(store.queryStatus);
    expect(Object.keys(status)).toHaveLength(2);
    expect(status.etha.status).toBe(HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED);
    expect(store.isAllFinished).toBeDefined();
    expect(get(store.isAllFinished)).toBe(false);
  });

  it('should ignore status updates while not syncing', () => {
    const store = useEventsQueryStatusStore();
    store.setQueryStatus(data('eth', 'a', HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED));
    expect(get(store.queryStatus)).toEqual({});
  });

  it('should merge status updates while syncing', () => {
    const store = useEventsQueryStatusStore();
    store.initializeQueryStatus([{ location: 'eth', name: 'a' }]);
    store.setQueryStatus(data('eth', 'a', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED));
    expect(get(store.queryStatus).etha.status).toBe(HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED);
    expect(get(store.isAllFinished)).toBe(true);
  });

  it('should not overwrite a cancelled entry', () => {
    const store = useEventsQueryStatusStore();
    store.initializeQueryStatus([{ location: 'eth', name: 'a' }]);
    store.markLocationCancelled({ location: 'eth', name: 'a' });
    expect(get(store.queryStatus).etha.status).toBe(HistoryEventsQueryStatus.CANCELLED);

    store.setQueryStatus(data('eth', 'a', HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED));
    expect(get(store.queryStatus).etha.status).toBe(HistoryEventsQueryStatus.CANCELLED);
  });

  it('should reset the query status', () => {
    const store = useEventsQueryStatusStore();
    store.initializeQueryStatus([{ location: 'eth', name: 'a' }]);
    store.resetQueryStatus();
    expect(get(store.queryStatus)).toEqual({});
  });
});
