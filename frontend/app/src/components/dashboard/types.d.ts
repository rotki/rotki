import { TIME_UNITS } from '@/components/dashboard/const';
import { TimeFramePeriod } from '@/store/settings/types';

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
