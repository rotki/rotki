import { TimeUnit } from "./index";

export enum TimeFramePeriod  {
  ALL = 'All',
  YEAR = '1Y',
  THREE_MONTHS = '3M',
  MONTH = '1M',
  TWO_WEEKS = '2W',
  WEEK = '1W'
}

export enum TimeFramePersist {
  REMEMBER = 'REMEMBER'
}

export type TimeFrameSetting = TimeFramePeriod | TimeFramePersist;

export interface Timeframe {
  readonly text: TimeFramePeriod | typeof TIMEFRAME_CUSTOM
  readonly startingDate: () => number;
  readonly xAxisTimeUnit: TimeUnit;
  readonly xAxisStepSize: number;
  readonly xAxisLabelDisplayFormat: string;
  readonly tooltipTimeFormat: string;
}

export type Timeframes = {
  readonly [timeframe in TimeFramePeriod]: Timeframe;
};


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
  startingDate: StartingDateCalculator,
  frame: TimeFramePeriod,
  displayUnit: TimeUnit,
  amount = 1
): Timeframe {
  let start: () => number;
  if (frame === TimeFramePeriod.ALL) {
    start = () => 0;
  } else {
    let startUnit: TimeUnit;
    if (frame === TimeFramePeriod.YEAR) {
      startUnit = TimeUnit.YEAR;
    } else if ([TimeFramePeriod.MONTH, TimeFramePeriod.THREE_MONTHS].includes(frame)) {
      startUnit = TimeUnit.MONTH;
    } else if ([TimeFramePeriod.WEEK, TimeFramePeriod.TWO_WEEKS].includes(frame)) {
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

type StartingDateCalculator = (unit: TimeUnit, amount: number) => number

export const timeframes: (startingDate: StartingDateCalculator) => Timeframes = (startingDate) => {
  return {
    [TimeFramePeriod.ALL]: createTimeframe(startingDate, TimeFramePeriod.ALL, TimeUnit.MONTH),
    [TimeFramePeriod.YEAR]: createTimeframe(startingDate, TimeFramePeriod.YEAR, TimeUnit.MONTH),
    [TimeFramePeriod.THREE_MONTHS]: createTimeframe(
      startingDate,
      TimeFramePeriod.THREE_MONTHS,
      TimeUnit.WEEK,
      3
    ),
    [TimeFramePeriod.MONTH]: createTimeframe(startingDate, TimeFramePeriod.MONTH, TimeUnit.WEEK),
    [TimeFramePeriod.TWO_WEEKS]: createTimeframe(startingDate, TimeFramePeriod.TWO_WEEKS, TimeUnit.DAY, 2),
    [TimeFramePeriod.WEEK]: createTimeframe(startingDate, TimeFramePeriod.WEEK, TimeUnit.DAY)
  }
};

export const TIMEFRAME_CUSTOM = "CUSTOM" as const
export type CustomizableTimeframe = TimeFramePeriod | typeof TIMEFRAME_CUSTOM;
export const customTimeframe: Timeframe = {
  text: TIMEFRAME_CUSTOM,
  startingDate: () => -1,
  ...unitDefaults(TimeUnit.MONTH),
  xAxisStepSize: 1
};