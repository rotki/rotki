import { NetValue } from '@/services/types-api';

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
