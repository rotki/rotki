import { TIME_UNITS, TIMEFRAME_PERIOD } from '@/components/dashboard/const';

export interface Timeframe {
  readonly text: TimeFramePeriod;
  readonly startingDate: () => number;
  readonly xAxisTimeUnit: TimeUnit;
  readonly xAxisStepSize: number;
  readonly xAxisLabelDisplayFormat: string;
  readonly tooltipTimeFormat: string;
}

export type TimeUnit = typeof TIME_UNITS[number];

export type Timeframes = {
  readonly [timeframe in TimeFramePeriod]: Timeframe;
};

export type TimeFramePeriod = typeof TIMEFRAME_PERIOD[number];
