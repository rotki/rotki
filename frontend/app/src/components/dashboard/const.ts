import dayjs from 'dayjs';
import { Timeframe, Timeframes, TimeUnit } from '@/components/dashboard/types';
import {
  TIMEFRAME_ALL,
  TIMEFRAME_MONTH,
  TIMEFRAME_THREE_MONTHS,
  TIMEFRAME_TWO_WEEKS,
  TIMEFRAME_WEEK,
  TIMEFRAME_YEAR
} from '@/store/settings/consts';
import { TimeFramePeriod } from '@/store/settings/types';

const TIME_UNIT_YEAR = 'year';
const TIME_UNIT_MONTH = 'month';
const TIME_UNIT_WEEK = 'week';
export const TIME_UNIT_DAY = 'day';

export const TIME_UNITS = [
  TIME_UNIT_YEAR,
  TIME_UNIT_MONTH,
  TIME_UNIT_WEEK,
  TIME_UNIT_DAY
] as const;

function startingDate(unit: TimeUnit, amount: number = 1): number {
  return dayjs().subtract(amount, unit).startOf(TIME_UNIT_DAY).unix();
}

type TimeframeDefaults = Pick<
  Timeframe,
  'xAxisLabelDisplayFormat' | 'tooltipTimeFormat' | 'xAxisTimeUnit'
>;

function unitDefaults(timeUnit: TimeUnit): TimeframeDefaults {
  if (timeUnit === TIME_UNIT_DAY) {
    return {
      xAxisTimeUnit: timeUnit,
      xAxisLabelDisplayFormat: 'ddd',
      tooltipTimeFormat: 'ddd'
    };
  } else if (timeUnit === TIME_UNIT_WEEK) {
    return {
      xAxisTimeUnit: timeUnit,
      xAxisLabelDisplayFormat: 'MMM D',
      tooltipTimeFormat: 'MMM D'
    };
  } else if (timeUnit === TIME_UNIT_MONTH) {
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
      startUnit = TIME_UNIT_YEAR;
    } else if ([TIMEFRAME_MONTH, TIMEFRAME_THREE_MONTHS].includes(frame)) {
      startUnit = TIME_UNIT_MONTH;
    } else if ([TIMEFRAME_WEEK, TIMEFRAME_TWO_WEEKS].includes(frame)) {
      startUnit = TIME_UNIT_WEEK;
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
  [TIMEFRAME_ALL]: createTimeframe(TIMEFRAME_ALL, TIME_UNIT_MONTH),
  [TIMEFRAME_YEAR]: createTimeframe(TIMEFRAME_YEAR, TIME_UNIT_MONTH),
  [TIMEFRAME_THREE_MONTHS]: createTimeframe(
    TIMEFRAME_THREE_MONTHS,
    TIME_UNIT_WEEK,
    3
  ),
  [TIMEFRAME_MONTH]: createTimeframe(TIMEFRAME_MONTH, TIME_UNIT_WEEK),
  [TIMEFRAME_TWO_WEEKS]: createTimeframe(TIMEFRAME_TWO_WEEKS, TIME_UNIT_DAY, 2),
  [TIMEFRAME_WEEK]: createTimeframe(TIMEFRAME_WEEK, TIME_UNIT_DAY)
};
