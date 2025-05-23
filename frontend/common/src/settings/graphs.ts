import { z } from 'zod';
import { assert } from '../assertions';
import { TimeUnit } from './frontend';

export enum TimeFramePeriod {
  ALL = 'All',
  TWO_YEARS = '2Y',
  YEAR = '1Y',
  SIX_MONTHS = '6M',
  THREE_MONTHS = '3M',
  MONTH = '1M',
  TWO_WEEKS = '2W',
  WEEK = '1W',
}

export enum TimeFramePersist {
  REMEMBER = 'REMEMBER',
}

export const TimeFramePeriodEnum = z.nativeEnum(TimeFramePeriod);

export type TimeFramePeriodEnum = z.infer<typeof TimeFramePeriodEnum>;

const TimeFramePersistEnum = z.nativeEnum(TimeFramePersist);

export const TimeFrameSetting = z.union([TimeFramePeriodEnum, TimeFramePersistEnum]);

export type TimeFrameSetting = z.infer<typeof TimeFrameSetting>;

export interface Timeframe {
  readonly text: TimeFramePeriod | typeof TIMEFRAME_CUSTOM;
  readonly startingDate: () => number;
  readonly xAxisTimeUnit: TimeUnit;
  readonly xAxisStepSize: number;
  readonly xAxisLabelDisplayFormat: string;
  readonly timestampRange: number;
}

export type Timeframes = Record<TimeFramePeriod, Timeframe>;

type TimeframeDefaults = Pick<Timeframe, 'xAxisLabelDisplayFormat' | 'xAxisTimeUnit'>;

function unitDefaults(timeUnit: TimeUnit): TimeframeDefaults {
  if (timeUnit === TimeUnit.DAY) {
    return {
      xAxisLabelDisplayFormat: 'ddd',
      xAxisTimeUnit: timeUnit,
    };
  }
  if (timeUnit === TimeUnit.WEEK) {
    return {
      xAxisLabelDisplayFormat: 'MMM D',
      xAxisTimeUnit: timeUnit,
    };
  }
  if (timeUnit === TimeUnit.MONTH) {
    return {
      xAxisLabelDisplayFormat: 'MMM YYYY',
      xAxisTimeUnit: timeUnit,
    };
  }
  throw new Error(`Invalid time unit selected: ${timeUnit}`);
}

const dayTimestamp = 24 * 60 * 60 * 1000;

function createTimeframe(
  startingDate: StartingDateCalculator,
  frame: TimeFramePeriod,
  displayUnit: TimeUnit,
  amount = 1,
): Timeframe {
  let start: () => number;
  let timestampRange = 0;

  if (frame === TimeFramePeriod.ALL) {
    start = (): number => 0;
    timestampRange = Number.POSITIVE_INFINITY;
  }
  else {
    let startUnit: TimeUnit;
    if ([TimeFramePeriod.TWO_YEARS, TimeFramePeriod.YEAR].includes(frame)) {
      startUnit = TimeUnit.YEAR;
      timestampRange = 365 * dayTimestamp * amount;
    }
    else if ([TimeFramePeriod.MONTH, TimeFramePeriod.THREE_MONTHS, TimeFramePeriod.SIX_MONTHS].includes(frame)) {
      startUnit = TimeUnit.MONTH;
      timestampRange = 30 * dayTimestamp * amount;
    }
    else if ([TimeFramePeriod.WEEK, TimeFramePeriod.TWO_WEEKS].includes(frame)) {
      startUnit = TimeUnit.WEEK;
      timestampRange = 7 * dayTimestamp * amount;
    }
    else {
      throw new Error(`unsupported timeframe: ${frame}`);
    }
    start = (): number => startingDate(startUnit, amount);
  }
  return {
    startingDate: start,
    text: frame,
    ...unitDefaults(displayUnit),
    timestampRange,
    xAxisStepSize: 1,
  };
}

type StartingDateCalculator = (unit: TimeUnit, amount: number) => number;

const timeframePeriods = [
  TimeFramePeriod.ALL,
  TimeFramePeriod.TWO_YEARS,
  TimeFramePeriod.YEAR,
  TimeFramePeriod.SIX_MONTHS,
  TimeFramePeriod.THREE_MONTHS,
  TimeFramePeriod.MONTH,
  TimeFramePeriod.TWO_WEEKS,
  TimeFramePeriod.WEEK,
] as const;

const timeframeMap: Record<TimeFramePeriod, [TimeUnit, number?]> = {
  [TimeFramePeriod.ALL]: [TimeUnit.MONTH],
  [TimeFramePeriod.MONTH]: [TimeUnit.WEEK],
  [TimeFramePeriod.SIX_MONTHS]: [TimeUnit.MONTH, 6],
  [TimeFramePeriod.THREE_MONTHS]: [TimeUnit.WEEK, 3],
  [TimeFramePeriod.TWO_WEEKS]: [TimeUnit.DAY, 2],
  [TimeFramePeriod.TWO_YEARS]: [TimeUnit.MONTH, 2],
  [TimeFramePeriod.WEEK]: [TimeUnit.DAY],
  [TimeFramePeriod.YEAR]: [TimeUnit.MONTH],
};

function isComplete(timeframes: Partial<Record<TimeFramePeriod, Timeframe>>): timeframes is Timeframes {
  const hasAllRequiredKeys = timeframePeriods.every(period => period in timeframes);
  const hasNoExtraKeys = Object.keys(timeframes).every(key =>
    timeframePeriods.includes(key as TimeFramePeriod),
  );

  return hasAllRequiredKeys && hasNoExtraKeys;
}

export const timeframes: (startingDate: StartingDateCalculator) => Timeframes = (startingDate) => {
  const timeframes: Partial<Record<TimeFramePeriod, Timeframe>> = {};

  timeframePeriods.forEach((period) => {
    const periodData = timeframeMap[period];
    if (!periodData) {
      return;
    }
    timeframes[period] = createTimeframe(startingDate, period, periodData[0], periodData[1]);
  });

  assert(isComplete(timeframes));

  return timeframes;
};

export const TIMEFRAME_CUSTOM = 'CUSTOM';

export type CustomizableTimeframe = TimeFramePeriod | typeof TIMEFRAME_CUSTOM;

export const customTimeframe: Timeframe = {
  startingDate: () => -1,
  text: TIMEFRAME_CUSTOM,
  ...unitDefaults(TimeUnit.MONTH),
  timestampRange: -1,
  xAxisStepSize: 1,
};

const definedTimeframes = timeframes(() => 0);
const sortedByRange = Object.values(definedTimeframes).sort((a, b) => a.timestampRange - b.timestampRange);

export function getTimeframeByRange(startDate: number, endDate: number): Timeframe {
  const range = endDate - startDate;
  const current = Math.abs(endDate - Date.now()) < dayTimestamp;

  let usedTimeframe: Timeframe = sortedByRange[0];
  let skip = false;

  sortedByRange.forEach((timeframe) => {
    if (skip)
      return;

    if (timeframe.timestampRange >= range) {
      usedTimeframe = timeframe;
      skip = true;
    }
  });

  if (range < dayTimestamp) {
    return {
      ...usedTimeframe,
    };
  }

  if (usedTimeframe.xAxisTimeUnit === TimeUnit.DAY && !current) {
    return {
      ...usedTimeframe,
      xAxisLabelDisplayFormat: 'MMM D',
    };
  }

  return usedTimeframe;
}

export interface TooltipDisplayOption {
  visible: boolean;
  id: string;
  left: number;
  top: number;
  xAlign: string;
  yAlign: string;
}
