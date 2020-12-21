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
  CURRENCY_BTC,
  CURRENCY_ETH
] as const;

export type SupportedCurrency = typeof SUPPORTED_CURRENCIES[number];

export const currencies: Currency[] = [
  new Currency('United States Dollar', CURRENCY_USD, '$'),
  new Currency('Euro', CURRENCY_EUR, '€'),
  new Currency('British Pound', CURRENCY_GBP, '£'),
  new Currency('Japanese Yen', CURRENCY_JPY, '¥'),
  new Currency('Chinese Yuan', CURRENCY_CNY, '¥'),
  new Currency('Korean Won', CURRENCY_KRW, '₩'),
  new Currency('Canadian Dollar', CURRENCY_CAD, '$'),
  new Currency('Australian Dollar', CURRENCY_AUD, '$'),
  new Currency('New Zealand Dollar', CURRENCY_NZD, '$'),
  new Currency('Brazilian Real', CURRENCY_BRL, 'R$'),
  new Currency('Russian Ruble', CURRENCY_RUB, '₽'),
  new Currency('South African Rand', CURRENCY_ZAR, 'R'),
  new Currency('Turkish Lira', CURRENCY_TRY, '₺'),
  new Currency('Swiss Franc', CURRENCY_CHF, 'Fr.'),
  new Currency('Bitcoin', CURRENCY_BTC, '₿'),
  new Currency('Ether', CURRENCY_ETH, 'Ξ')
];
