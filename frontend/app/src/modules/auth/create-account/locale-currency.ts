import { CURRENCY_USD, type SupportedCurrency } from '@/modules/assets/amount-display/currencies';

/** Countries and territories using the euro, including those outside the euro area that adopted it. */
const EURO_REGIONS = [
  'AD',
  'AT',
  'BE',
  'BG',
  'CY',
  'DE',
  'EE',
  'ES',
  'FI',
  'FR',
  'GR',
  'HR',
  'IE',
  'IT',
  'LT',
  'LU',
  'LV',
  'MC',
  'ME',
  'MT',
  'NL',
  'PT',
  'SI',
  'SK',
  'SM',
  'VA',
  'XK',
] as const;

const REGION_CURRENCIES = new Map<string, SupportedCurrency>([
  ...EURO_REGIONS.map((region): [string, SupportedCurrency] => [region, 'EUR']),
  ['AE', 'AED'],
  ['AU', 'AUD'],
  ['BR', 'BRL'],
  ['CA', 'CAD'],
  ['CH', 'CHF'],
  ['CN', 'CNY'],
  ['CZ', 'CZK'],
  ['DK', 'DKK'],
  ['GB', 'GBP'],
  ['IL', 'ILS'],
  ['IN', 'INR'],
  ['JP', 'JPY'],
  ['KR', 'KRW'],
  ['LI', 'CHF'],
  ['MX', 'MXN'],
  ['NG', 'NGN'],
  ['NO', 'NOK'],
  ['NZ', 'NZD'],
  ['PH', 'PHP'],
  ['PL', 'PLN'],
  ['RU', 'RUB'],
  ['SE', 'SEK'],
  ['SG', 'SGD'],
  ['TR', 'TRY'],
  ['TW', 'TWD'],
  ['ZA', 'ZAR'],
]);

/**
 * Suggests a main currency from a BCP 47 locale such as `navigator.language`.
 *
 * @remarks
 * The locale names a language, not where someone files taxes, so this is only a starting point the
 * user sees and can change. A locale without a country takes its likeliest one (`de` is Germany).
 * Anything unrecognised, or a country whose currency rotki does not support, falls back to USD.
 */
export function suggestCurrency(locale: string): SupportedCurrency {
  try {
    const region = new Intl.Locale(locale).maximize().region;
    return (region ? REGION_CURRENCIES.get(region) : undefined) ?? CURRENCY_USD;
  }
  catch (error: unknown) {
    if (error instanceof RangeError)
      return CURRENCY_USD;
    throw error;
  }
}
