import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus } from '@/modules/core/messaging/types';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { bankEventsActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { useLiveActivityEntries } from '@/modules/task-center/use-live-activity-entries';

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
  const { banks } = storeToRefs(useLocationStore());
  const tracking = useLiveActivityEntries<ExchangeQueryTracking>();

  /** A bank streams the same frames as an exchange, but its query is an activity of its own kind. */
  function activityOf(location: string): typeof exchangeEventsActivity {
    return get(banks).includes(location) ? bankEventsActivity : exchangeEventsActivity;
  }

  return createStateHandler((data) => {
    const subject = { location: data.location, name: data.name };
    const activity = activityOf(data.location);
    const address = { kind: activity.kind, parts: activity.partsOf(subject) };
    if (!tracking.isLive(address))
      return;

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
