import { z } from 'zod';

export enum CurrencyLocation {
  BEFORE = 'before',
  AFTER = 'after'
}

export const CurrencyLocationEnum = z.nativeEnum(CurrencyLocation);
