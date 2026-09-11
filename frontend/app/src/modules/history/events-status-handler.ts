import type { StateHandler } from '@/modules/core/messaging/interfaces';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { HistoryEventsQueryStatus } from '@/modules/core/messaging/types';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { bankEventsActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { publishActivityDetail } from '@/modules/task-center/use-activity-detail';

export function createEventsStatusHandler(): StateHandler {
  const { getQueryStatus, setQueryStatus } = useEventsQueryStatusStore();
  const { banks } = storeToRefs(useLocationStore());

  /**
   * Mirror one exchange's stored entry onto its activity.
   *
   * Read back from the store rather than taken from the frame, so what is published is the merged
   * entry: the range an earlier message established and a later one omitted, and nothing at all for
   * a message that arrived while no sync was running.
   *
   * A cancelled exchange is left frozen at its last real detail. The store refuses the update but
   * keeps the entry, so mirroring it anyway would re-publish the seeded range over what the query
   * had actually reached — an activity that stopped would start reading as one that never began.
   *
   * Detail only. The activity's status is its own, and an exchange query streams no cursor to
   * report as progress — `ExchangeEventsDetail` carries why the range it does stream is not one.
   */
  function mirrorToActivity(subject: { location: string; name: string }): void {
    const entry = getQueryStatus(subject);
    if (entry === undefined || entry.status === HistoryEventsQueryStatus.CANCELLED)
      return;

    // a bank streams the same frames as an exchange, but its activity is its own kind
    const activity = get(banks).includes(entry.location) ? bankEventsActivity : exchangeEventsActivity;
    publishActivityDetail(activity, { location: entry.location, name: entry.name }, {
      eventType: entry.eventType,
      period: entry.period,
    });
  }

  return createStateHandler((data) => {
    setQueryStatus(data);
    mirrorToActivity({ location: data.location, name: data.name });
  });
}
