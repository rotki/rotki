import type { ActionDataEntry } from '@/types/action';

export type AllLocation = Record<
  string,
  Omit<ActionDataEntry, 'identifier'> & {
    isExchange?: boolean;
    exchangeDetails?: {
      isExchangeWithPassphrase?: boolean;
      isExchangeWithKey?: boolean;
      isExchangeWithoutApiSecret?: boolean;
      experimental?: boolean;
    };
  }
>;

export interface AllLocationResponse {
  locations: AllLocation;
}
