import moment from 'moment';
import { Timeframes } from '@/components/dashboard/types';

export const TIMEFRAME_ALL = 'All';
export const TIMEFRAME_MONTH = '1M';
export const TIMEFRAME_WEEK = '1W';
export const TIMEFRAME_DAY = '1D';

export const TIMEFRAME_PERIOD = [
  TIMEFRAME_ALL,
  TIMEFRAME_MONTH,
  TIMEFRAME_WEEK,
  TIMEFRAME_DAY
] as const;

function startingDate(unit: 'day' | 'month' | 'week'): number {
  return moment().subtract(1, unit).startOf('day').unix();
}

export const timeframes: Timeframes = {
  [TIMEFRAME_ALL]: {
    text: TIMEFRAME_ALL,
    startingDate: () => 0,
    xAxisTimeUnit: 'month',
    xAxisStepSize: 1,
    xAxisLabelDisplayFormat: 'MMMM YYYY',
    tooltipTimeFormat: 'MMMM D, YYYY'
  },
  [TIMEFRAME_MONTH]: {
    text: TIMEFRAME_MONTH,
    startingDate: () => startingDate('month'),
    xAxisTimeUnit: 'week',
    xAxisStepSize: 1,
    xAxisLabelDisplayFormat: 'MMM D',
    tooltipTimeFormat: 'MMM D'
  },
  [TIMEFRAME_WEEK]: {
    text: TIMEFRAME_WEEK,
    startingDate: () => startingDate('week'),
    xAxisTimeUnit: 'day',
    xAxisStepSize: 1,
    xAxisLabelDisplayFormat: 'ddd',
    tooltipTimeFormat: 'ddd'
  },
  [TIMEFRAME_DAY]: {
    text: TIMEFRAME_DAY,
    startingDate: () => startingDate('day'),
    xAxisTimeUnit: 'hour',
    xAxisStepSize: 4,
    xAxisLabelDisplayFormat: 'HH:mm',
    tooltipTimeFormat: 'HH:mm'
  }
};
