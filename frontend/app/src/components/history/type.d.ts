import { TradeLocation } from '@/services/history/types';

export type TradeLocationData = {
  readonly identifier: TradeLocation;
  readonly name: string;
  readonly icon?: string;
};
