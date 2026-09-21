import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/modules/core/messaging/types';
import { createEventsStatusHandler } from '@/modules/history/events-status-handler';
import { bankEventsActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { type ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { readActivityDetail, useActivityDetail } from '@/modules/task-center/use-activity-detail';

/** The activities the stub orchestrator reports as active, by id. */
const live = new Set<string>();
const changeListeners: (() => void)[] = [];

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn(() => ({
    onChange: (listener: () => void): (() => void) => {
      changeListeners.push(listener);
      return (): void => {};
    },
    statusOf: (kind: ActivityKind, ...parts: (string | number)[]): { active: boolean } => ({
      active: live.has(makeActivityId(kind, ...parts)),
    }),
  })),
}));

const kraken = { location: 'kraken', name: 'my kraken' };

/**
 * A parsed frame. `period` is spread in only when present, because that is what the schema does
 * with an absent optional, and it is the absent key a later frame's merge has to survive.
 */
function frame(status: HistoryEventsQueryStatus, period?: [number, number], subject = kraken): HistoryEventsQueryData {
  return { eventType: 'history_query', ...subject, ...(period && { period }), status };
}

/** Settles an exchange's query as far as the handler can tell, and lets it prune. */
function settle(subject = kraken): void {
  live.delete(exchangeEventsActivity.id(subject));
  changeListeners.forEach(listener => listener());
}

describe('createEventsStatusHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useActivityDetail().resetDetails();
    live.clear();
    changeListeners.length = 0;
    live.add(exchangeEventsActivity.id(kraken));
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

    expect(get(readActivityDetail(exchangeEventsActivity, kraken))?.period).toStrictEqual([100, 200]);
  });

  it('should key detail by name, so two accounts on one exchange stay apart', async () => {
    const second = { location: 'kraken', name: 'other kraken' };
    live.add(exchangeEventsActivity.id(second));
    const handler = createEventsStatusHandler();

    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200]));

    expect(get(readActivityDetail(exchangeEventsActivity, kraken))?.period).toStrictEqual([100, 200]);
    expect(get(readActivityDetail(exchangeEventsActivity, second))).toBeUndefined();
  });

  it('should freeze a cancelled exchange at the range it reached', async () => {
    const handler = createEventsStatusHandler();
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200]));

    settle();
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [200, 300]));

    expect(get(readActivityDetail(exchangeEventsActivity, kraken))?.period).toStrictEqual([100, 200]);
  });

  it('should publish nothing for an exchange whose query is not running', async () => {
    const idle = { location: 'binance', name: 'my binance' };
    const handler = createEventsStatusHandler();

    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200], idle));

    expect(get(readActivityDetail(exchangeEventsActivity, idle))).toBeUndefined();
  });

  it('should not carry the last run\'s range into a new run', async () => {
    const handler = createEventsStatusHandler();
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200]));

    settle();
    live.add(exchangeEventsActivity.id(kraken));
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED));

    expect(get(readActivityDetail(exchangeEventsActivity, kraken))?.period).toBeUndefined();
  });

  it('should leave the detail alone for a frame that itself reports the query cancelled', async () => {
    const handler = createEventsStatusHandler();
    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200]));

    await handler.handle(frame(HistoryEventsQueryStatus.CANCELLED, [0, 0]));

    expect(get(readActivityDetail(exchangeEventsActivity, kraken))?.period).toStrictEqual([100, 200]);
  });

  it('should publish a bank location frame on the bank activity, not the exchange one', async () => {
    const qonto = { location: 'qonto', name: 'rotki Solutions GmbH' };
    useLocationStore().$patch({ allLocations: { qonto: { image: 'qonto.svg', isBank: true } } });
    live.add(bankEventsActivity.id(qonto));
    const handler = createEventsStatusHandler();

    await handler.handle(frame(HistoryEventsQueryStatus.QUERYING_EVENTS_STATUS_UPDATE, [100, 200], qonto));

    expect(get(readActivityDetail(bankEventsActivity, qonto))?.period).toStrictEqual([100, 200]);
    expect(get(readActivityDetail(exchangeEventsActivity, qonto))).toBeUndefined();
  });
});
