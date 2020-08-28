import { TradeLocation } from '@/services/trades/types';

export type TradeLocationData = {
  readonly identifier: TradeLocation;
  readonly name: string;
  readonly icon?: string;
};
