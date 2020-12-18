import { SupportedCurrency } from '@/data/currencies';

export class Currency {
  constructor(
    readonly name: string,
    readonly ticker_symbol: SupportedCurrency,
    readonly unicode_symbol: string
  ) {}
}
