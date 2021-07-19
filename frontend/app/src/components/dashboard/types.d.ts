import { TimeUnit } from '@rotki/common/lib/settings';
import { TimeFramePeriod } from '@/store/settings/types';

export interface Timeframe {
  readonly text: TimeFramePeriod;
  readonly startingDate: () => number;
  readonly xAxisTimeUnit: TimeUnit;
  readonly xAxisStepSize: number;
  readonly xAxisLabelDisplayFormat: string;
  readonly tooltipTimeFormat: string;
}

export type Timeframes = {
  readonly [timeframe in TimeFramePeriod]: Timeframe;
};
