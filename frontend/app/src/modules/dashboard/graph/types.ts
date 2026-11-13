import type { NetValue } from '@rotki/common';

export interface NetValueChartData extends NetValue {
  snapshotCount: number;
  /** Per point, whether its value rests on a stand-in rate; absent means none does. */
  estimated?: readonly boolean[];
}
