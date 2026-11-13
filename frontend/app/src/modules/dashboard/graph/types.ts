import type { NetValue } from '@rotki/common';

export interface NetValueChartData extends NetValue {
  snapshotCount: number;
  /** Per point, whether its value rests on a stand-in rate; absent means none does. */
  estimated?: readonly boolean[];
  /**
   * Per estimated point, when the rate it was converted at was quoted, unix seconds; undefined
   * when it used today's rate.
   */
  rateTimes?: readonly (number | undefined)[];
}
