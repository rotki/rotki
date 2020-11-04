import { TIMEFRAME_PERIOD } from '@/components/dashboard/const';

export interface Timeframe {
  readonly text: TimeFramePeriod;
  readonly startingDate: () => number;
  readonly xAxisTimeUnit: 'hour' | 'day' | 'week' | 'month';
  readonly xAxisStepSize: number;
  readonly xAxisLabelDisplayFormat: string;
  readonly tooltipTimeFormat: string;
}

export type Timeframes = {
  readonly [timeframe in TimeFramePeriod]: Timeframe;
};

export type TimeFramePeriod = typeof TIMEFRAME_PERIOD[number];
