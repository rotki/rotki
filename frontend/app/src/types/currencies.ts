import { ComputedRef } from 'vue';

export class Currency {
  constructor(
    readonly name: string,
    readonly tickerSymbol: SupportedCurrency,
    readonly unicodeSymbol: string
  ) {}
}

export const CURRENCY_USD = 'USD';
const CURRENCY_EUR = 'EUR';
const CURRENCY_GBP = 'GBP';
const CURRENCY_JPY = 'JPY';
const CURRENCY_CNY = 'CNY';
const CURRENCY_KRW = 'KRW';
const CURRENCY_CAD = 'CAD';
const CURRENCY_AUD = 'AUD';
const CURRENCY_NZD = 'NZD';
const CURRENCY_BRL = 'BRL';
const CURRENCY_RUB = 'RUB';
const CURRENCY_ZAR = 'ZAR';
const CURRENCY_TRY = 'TRY';
const CURRENCY_BTC = 'BTC';
const CURRENCY_ETH = 'ETH';
const CURRENCY_CHF = 'CHF';
const CURRENCY_SGD = 'SGD';
const CURRENCY_SEK = 'SEK';
const CURRENCY_TWD = 'TWD';
const CURRENCY_NOK = 'NOK';
const CURRENCY_INR = 'INR';
const CURRENCY_DKK = 'DKK';
const CURRENCY_PLN = 'PLN';

const SUPPORTED_CURRENCIES = [
  CURRENCY_USD,
  CURRENCY_EUR,
  CURRENCY_GBP,
  CURRENCY_JPY,
  CURRENCY_CNY,
  CURRENCY_KRW,
  CURRENCY_CAD,
  CURRENCY_AUD,
  CURRENCY_NZD,
  CURRENCY_BRL,
  CURRENCY_RUB,
  CURRENCY_ZAR,
  CURRENCY_TRY,
  CURRENCY_CHF,
  CURRENCY_SGD,
  CURRENCY_SEK,
  CURRENCY_TWD,
  CURRENCY_NOK,
  CURRENCY_BTC,
  CURRENCY_ETH,
  CURRENCY_INR,
  CURRENCY_DKK,
  CURRENCY_PLN
] as const;

export type SupportedCurrency = typeof SUPPORTED_CURRENCIES[number];

export const useCurrencies = createSharedComposable(() => {
  const { tc } = useI18n();
  const currencies: ComputedRef<Currency[]> = computed(() => [
    new Currency(tc('currencies.usd'), CURRENCY_USD, '$'),
    new Currency(tc('currencies.eur'), CURRENCY_EUR, '€'),
    new Currency(tc('currencies.gbp'), CURRENCY_GBP, '£'),
    new Currency(tc('currencies.jpy'), CURRENCY_JPY, '¥'),
    new Currency(tc('currencies.cny'), CURRENCY_CNY, '¥'),
    new Currency(tc('currencies.krw'), CURRENCY_KRW, '₩'),
    new Currency(tc('currencies.cad'), CURRENCY_CAD, '$'),
    new Currency(tc('currencies.aud'), CURRENCY_AUD, '$'),
    new Currency(tc('currencies.nzd'), CURRENCY_NZD, '$'),
    new Currency(tc('currencies.brl'), CURRENCY_BRL, 'R$'),
    new Currency(tc('currencies.rub'), CURRENCY_RUB, '₽'),
    new Currency(tc('currencies.zar'), CURRENCY_ZAR, 'R'),
    new Currency(tc('currencies.try'), CURRENCY_TRY, '₺'),
    new Currency(tc('currencies.chf'), CURRENCY_CHF, 'Fr.'),
    new Currency(tc('currencies.sgd'), CURRENCY_SGD, 'S$'),
    new Currency(tc('currencies.sek'), CURRENCY_SEK, 'kr'),
    new Currency(tc('currencies.twd'), CURRENCY_TWD, 'NT$'),
    new Currency(tc('currencies.nok'), CURRENCY_NOK, 'kr'),
    new Currency(tc('currencies.inr'), CURRENCY_INR, '₹'),
    new Currency(tc('currencies.dkk'), CURRENCY_DKK, 'kr'),
    new Currency(tc('currencies.pln'), CURRENCY_PLN, 'zł'),
    new Currency('Bitcoin', CURRENCY_BTC, '₿'),
    new Currency('Ether', CURRENCY_ETH, 'Ξ')
  ]);

  const defaultCurrency: ComputedRef<Currency> = computed(() => {
    return get(currencies)[0];
  });

  const findCurrency = (currencySymbol: string) => {
    const currency: Currency | undefined = get(currencies).find(
      currency => currency.tickerSymbol === currencySymbol
    );
    if (!currency) {
      throw new Error(`Could not find ${currencySymbol}`);
    }
    return currency;
  };

  return {
    currencies,
    defaultCurrency,
    findCurrency
  };
});
