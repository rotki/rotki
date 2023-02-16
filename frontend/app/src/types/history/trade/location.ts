import { z } from 'zod';
import { SUPPORTED_TRADE_LOCATIONS } from '@/data/defaults';
import { SUPPORTED_EXCHANGES } from '@/types/exchanges';
// @ts-ignore
export const TradeLocation = z.enum([
  ...SUPPORTED_EXCHANGES,
  ...SUPPORTED_TRADE_LOCATIONS,
  'gitcoin'
]);
export type TradeLocation = z.infer<typeof TradeLocation>;

export interface TradeLocationData {
  readonly identifier: TradeLocation;
  readonly name: string;
  readonly icon: string;
  readonly imageIcon: boolean;
  readonly component?: any;
  readonly exchange: boolean;
  readonly detailPath?: string;
}
