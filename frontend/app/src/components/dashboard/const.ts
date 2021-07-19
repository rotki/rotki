import { TimeUnit } from '@rotki/common/lib/settings';
import dayjs from 'dayjs';
import { Timeframe, Timeframes } from '@/components/dashboard/types';
import {
  TIMEFRAME_ALL,
  TIMEFRAME_MONTH,
  TIMEFRAME_THREE_MONTHS,
  TIMEFRAME_TWO_WEEKS,
  TIMEFRAME_WEEK,
  TIMEFRAME_YEAR
} from '@/store/settings/consts';
import { TimeFramePeriod } from '@/store/settings/types';

function startingDate(unit: TimeUnit, amount: number = 1): number {
  return dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix();
}

type TimeframeDefaults = Pick<
  Timeframe,
  'xAxisLabelDisplayFormat' | 'tooltipTimeFormat' | 'xAxisTimeUnit'
>;

function unitDefaults(timeUnit: TimeUnit): TimeframeDefaults {
  if (timeUnit === TimeUnit.DAY) {
    return {
      xAxisTimeUnit: timeUnit,
      xAxisLabelDisplayFormat: 'ddd',
      tooltipTimeFormat: 'ddd'
    };
  } else if (timeUnit === TimeUnit.WEEK) {
    return {
      xAxisTimeUnit: timeUnit,
      xAxisLabelDisplayFormat: 'MMM D',
      tooltipTimeFormat: 'MMM D'
    };
  } else if (timeUnit === TimeUnit.MONTH) {
    return {
      xAxisTimeUnit: timeUnit,
      xAxisLabelDisplayFormat: 'MMMM YYYY',
      tooltipTimeFormat: 'MMMM D, YYYY'
    };
  }
  throw new Error(`Invalid time unit selected: ${timeUnit}`);
}

function createTimeframe(
  frame: TimeFramePeriod,
  displayUnit: TimeUnit,
  amount: number = 1
): Timeframe {
  let start: () => number;
  if (frame === TIMEFRAME_ALL) {
    start = () => 0;
  } else {
    let startUnit: TimeUnit;
    if (frame === TIMEFRAME_YEAR) {
      startUnit = TimeUnit.YEAR;
    } else if ([TIMEFRAME_MONTH, TIMEFRAME_THREE_MONTHS].includes(frame)) {
      startUnit = TimeUnit.MONTH;
    } else if ([TIMEFRAME_WEEK, TIMEFRAME_TWO_WEEKS].includes(frame)) {
      startUnit = TimeUnit.WEEK;
    } else {
      throw new Error(`unsupported timeframe: ${frame}`);
    }
    start = () => startingDate(startUnit, amount);
  }
  return {
    text: frame,
    startingDate: start,
    ...unitDefaults(displayUnit),
    xAxisStepSize: 1
  };
}

export const timeframes: Timeframes = {
  [TIMEFRAME_ALL]: createTimeframe(TIMEFRAME_ALL, TimeUnit.MONTH),
  [TIMEFRAME_YEAR]: createTimeframe(TIMEFRAME_YEAR, TimeUnit.MONTH),
  [TIMEFRAME_THREE_MONTHS]: createTimeframe(
    TIMEFRAME_THREE_MONTHS,
    TimeUnit.WEEK,
    3
  ),
  [TIMEFRAME_MONTH]: createTimeframe(TIMEFRAME_MONTH, TimeUnit.WEEK),
  [TIMEFRAME_TWO_WEEKS]: createTimeframe(TIMEFRAME_TWO_WEEKS, TimeUnit.DAY, 2),
  [TIMEFRAME_WEEK]: createTimeframe(TIMEFRAME_WEEK, TimeUnit.DAY)
};
