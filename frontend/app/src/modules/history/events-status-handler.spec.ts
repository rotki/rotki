import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/modules/core/messaging/types';
import { createEventsStatusHandler } from '@/modules/history/events-status-handler';
import { exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { readActivityDetail, useActivityDetail } from '@/modules/task-center/use-activity-detail';

const kraken = { location: 'kraken', name: 'my kraken' };

/**
 * A parsed frame. `period` is spread in only when present, because that is what the schema does
 * with an absent optional — and the store merges by spreading, so an explicit `undefined` would
 * erase the range instead of leaving it, testing a frame the backend never sends.
 */
function frame(status: HistoryEventsQueryStatus, period?: [number, number]): HistoryEventsQueryData {
  return { eventType: 'history_query', ...kraken, ...(period && { period }), status };
}

describe('createEventsStatusHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useActivityDetail().resetDetails();
    useEventsQueryStatusStore().initializeQueryStatus([kraken]);
  });

  it('should publish the queried range as detail on the exchange activity', async () => {
    const handler = createEventsStatusHandler();
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200]));

    const detail = get(readActivityDetail(exchangeEventsActivity, kraken));
    expect(detail?.eventType).toBe('history_query');
    expect(detail?.period).toStrictEqual([100, 200]);
  });

  it('should keep the range a later period-less frame omits', async () => {
    const handler = createEventsStatusHandler();
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200]));
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED));

    // The store merges onto the stored entry, so reading it back survives what the frame drops.
    expect(get(readActivityDetail(exchangeEventsActivity, kraken))?.period).toStrictEqual([100, 200]);
  });

  it('should key detail by name, so two accounts on one exchange stay apart', async () => {
    const second = { location: 'kraken', name: 'other kraken' };
    useEventsQueryStatusStore().initializeQueryStatus([kraken, second], { extend: true });
    const handler = createEventsStatusHandler();

    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200]));

    expect(get(readActivityDetail(exchangeEventsActivity, kraken))?.period).toStrictEqual([100, 200]);
    expect(get(readActivityDetail(exchangeEventsActivity, second))).toBeUndefined();
  });

  it('should freeze a cancelled exchange at the range it reached', async () => {
    const handler = createEventsStatusHandler();
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200]));

    useEventsQueryStatusStore().markLocationCancelled(kraken);
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [200, 300]));

    // The store refuses the update but keeps the entry, whose seeded range would overwrite this.
    expect(get(readActivityDetail(exchangeEventsActivity, kraken))?.period).toStrictEqual([100, 200]);
  });
});
