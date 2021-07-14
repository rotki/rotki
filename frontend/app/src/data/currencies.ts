import i18n from '@/i18n';
import { Currency } from '@/model/currency';

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
  CURRENCY_INR
] as const;

export type SupportedCurrency = typeof SUPPORTED_CURRENCIES[number];

export const currencies: Currency[] = [
  new Currency(i18n.t('currencies.usd').toString(), CURRENCY_USD, '$'),
  new Currency(i18n.t('currencies.eur').toString(), CURRENCY_EUR, '€'),
  new Currency(i18n.t('currencies.gbp').toString(), CURRENCY_GBP, '£'),
  new Currency(i18n.t('currencies.jpy').toString(), CURRENCY_JPY, '¥'),
  new Currency(i18n.t('currencies.cny').toString(), CURRENCY_CNY, '¥'),
  new Currency(i18n.t('currencies.krw').toString(), CURRENCY_KRW, '₩'),
  new Currency(i18n.t('currencies.cad').toString(), CURRENCY_CAD, '$'),
  new Currency(i18n.t('currencies.aud').toString(), CURRENCY_AUD, '$'),
  new Currency(i18n.t('currencies.nzd').toString(), CURRENCY_NZD, '$'),
  new Currency(i18n.t('currencies.brl').toString(), CURRENCY_BRL, 'R$'),
  new Currency(i18n.t('currencies.rub').toString(), CURRENCY_RUB, '₽'),
  new Currency(i18n.t('currencies.zar').toString(), CURRENCY_ZAR, 'R'),
  new Currency(i18n.t('currencies.try').toString(), CURRENCY_TRY, '₺'),
  new Currency(i18n.t('currencies.chf').toString(), CURRENCY_CHF, 'Fr.'),
  new Currency(i18n.t('currencies.sgd').toString(), CURRENCY_SGD, 'S$'),
  new Currency(i18n.t('currencies.sek').toString(), CURRENCY_SEK, 'kr'),
  new Currency(i18n.t('currencies.twd').toString(), CURRENCY_TWD, 'NT$'),
  new Currency(i18n.t('currencies.nok').toString(), CURRENCY_NOK, 'kr'),
  new Currency(i18n.t('currencies.inr').toString(), CURRENCY_INR, '₹'),
  new Currency('Bitcoin', CURRENCY_BTC, '₿'),
  new Currency('Ether', CURRENCY_ETH, 'Ξ')
];
