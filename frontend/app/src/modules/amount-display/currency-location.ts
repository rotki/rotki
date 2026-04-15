import { z } from 'zod/v4';

export enum CurrencyLocation {
  BEFORE = 'before',
  AFTER = 'after',
}

export const CurrencyLocationEnum = z.enum(CurrencyLocation);
