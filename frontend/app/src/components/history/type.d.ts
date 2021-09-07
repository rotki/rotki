import { VueConstructor } from 'vue';
import { TradeLocation } from '@/services/history/types';

export type TradeLocationData = {
  readonly identifier: TradeLocation;
  readonly name: string;
  readonly icon: string;
  readonly imageIcon: boolean;
  readonly component?: VueConstructor;
  readonly exchange: boolean;
};
