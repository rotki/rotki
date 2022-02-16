import { NetValue } from '@rotki/common/lib/statistics';

export interface StatisticsState {
  netValue: NetValue;
}

export interface OverallPerformance {
  readonly period: string;
  readonly currency: string;
  readonly percentage: string;
  readonly netWorth: string;
  readonly delta: string;
  readonly up?: boolean;
}
