export class Currency {
  constructor(
    readonly name: string,
    readonly tickerSymbol: SupportedCurrency,
    readonly unicodeSymbol: string,
    readonly crypto: boolean = false,
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
const CURRENCY_NGN = 'NGN';

// eslint-disable-next-line unused-imports/no-unused-vars
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
  CURRENCY_PLN,
  CURRENCY_NGN,
] as const;

export type SupportedCurrency = (typeof SUPPORTED_CURRENCIES)[number];

export const useCurrencies = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const currencies = computed<Currency[]>(() => [
    new Currency(t('currencies.usd'), CURRENCY_USD, '$'),
    new Currency(t('currencies.eur'), CURRENCY_EUR, '€'),
    new Currency(t('currencies.gbp'), CURRENCY_GBP, '£'),
    new Currency(t('currencies.jpy'), CURRENCY_JPY, '¥'),
    new Currency(t('currencies.cny'), CURRENCY_CNY, '¥'),
    new Currency(t('currencies.krw'), CURRENCY_KRW, '₩'),
    new Currency(t('currencies.cad'), CURRENCY_CAD, 'C$'),
    new Currency(t('currencies.aud'), CURRENCY_AUD, 'A$'),
    new Currency(t('currencies.nzd'), CURRENCY_NZD, '$NZ'),
    new Currency(t('currencies.brl'), CURRENCY_BRL, 'R$'),
    new Currency(t('currencies.rub'), CURRENCY_RUB, '₽'),
    new Currency(t('currencies.zar'), CURRENCY_ZAR, 'R'),
    new Currency(t('currencies.try'), CURRENCY_TRY, '₺'),
    new Currency(t('currencies.chf'), CURRENCY_CHF, 'CHF'),
    new Currency(t('currencies.sgd'), CURRENCY_SGD, 'S$'),
    new Currency(t('currencies.sek'), CURRENCY_SEK, 'kr'),
    new Currency(t('currencies.twd'), CURRENCY_TWD, 'NT$'),
    new Currency(t('currencies.nok'), CURRENCY_NOK, 'kr'),
    new Currency(t('currencies.inr'), CURRENCY_INR, '₹'),
    new Currency(t('currencies.dkk'), CURRENCY_DKK, 'kr'),
    new Currency(t('currencies.pln'), CURRENCY_PLN, 'zł'),
    new Currency(t('currencies.ngn'), CURRENCY_NGN, '₦'),
    new Currency('Bitcoin', CURRENCY_BTC, '₿', true),
    new Currency('Ether', CURRENCY_ETH, 'Ξ', true),
  ]);

  const defaultCurrency = computed<Currency>(() => get(currencies)[0]);

  const findCurrency = (currencySymbol: string): Currency => {
    const currency: Currency | undefined = get(currencies).find(currency => currency.tickerSymbol === currencySymbol);
    if (!currency)
      throw new Error(`Could not find ${currencySymbol}`);

    return currency;
  };

  return {
    currencies,
    defaultCurrency,
    findCurrency,
  };
});

export type ShownCurrency = 'none' | 'ticker' | 'symbol' | 'name';
