import { SupportedCurrency } from '@/data/currencies';

export class Currency {
  constructor(
    readonly name: string,
    readonly tickerSymbol: SupportedCurrency,
    readonly unicodeSymbol: string
  ) {}
}
