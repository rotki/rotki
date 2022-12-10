import {
  TimeFramePeriod,
  type TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';

export function isPeriodAllowed(period: TimeFrameSetting): boolean {
  return (
    period === TimeFramePeriod.WEEK || period === TimeFramePeriod.TWO_WEEKS
  );
}
