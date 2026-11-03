import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/modules/core/messaging/types';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { bankEventsActivity, exchangeEventsActivity, type ExchangeEventsSubject } from '@/modules/history/events/tx/sync.activity';
import { publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { type ActivityAddress, useLiveActivityEntries } from '@/modules/task-center/use-live-activity-entries';

/** One exchange's query, as the frames of its run have described it so far. */
type ExchangeQueryTracking = Pick<HistoryEventsQueryData, 'eventType' | 'period' | 'status'>;

/**
 * Turns the backend's exchange and bank query frames into detail on each location's activity.
 *
 * @remarks
 * A frame only updates a location whose query activity is live, so one that lands after the query
 * ended, or after the user cancelled it, leaves the detail where the query had reached. A range an
 * earlier frame established is kept when a later frame omits it, for as long as the activity is live;
 * see `useLiveActivityEntries`.
 *
 * Detail only. The activity's status is its own, and an exchange query streams no cursor to report
 * as progress; `ExchangeEventsDetail` carries why the range it does stream is not one.
 */
export function createEventsStatusHandler(): StateHandler {
  const tracking = useLiveActivityEntries<ExchangeQueryTracking>();

  /**
   * The live query a frame belongs to, a bank's or an exchange's.
   *
   * @remarks
   * A bank streams the same frames as an exchange, naming its connector as the location, but its
   * query is an activity of its own kind. Which one is live tells them apart, so no list of
   * connectors has to be loaded first.
   */
  function liveQueryOf(subject: ExchangeEventsSubject): { activity: typeof exchangeEventsActivity; address: ActivityAddress } | undefined {
    for (const activity of [bankEventsActivity, exchangeEventsActivity]) {
      const address = { kind: activity.kind, parts: activity.partsOf(subject) };
      if (tracking.isLive(address))
        return { activity, address };
    }
    return undefined;
  }

  return createStateHandler((data) => {
    const subject = { location: data.location, name: data.name };
    const query = liveQueryOf(subject);
    if (!query)
      return;
    const { activity, address } = query;

    const entry: ExchangeQueryTracking = {
      eventType: data.eventType,
      period: data.period ?? tracking.read(address)?.period,
      status: data.status,
    };
    tracking.write(address, entry);

    if (entry.status === HistoryEventsQueryStatus.CANCELLED)
      return;

    publishActivityDetail(activity, subject, { eventType: entry.eventType, period: entry.period });
  });
}
