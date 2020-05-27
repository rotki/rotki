import { Currency } from '@/model/currency';

export const currencies: Currency[] = [
  new Currency('United States Dollar', 'USD', '$'),
  new Currency('Euro', 'EUR', '€'),
  new Currency('British Pound', 'GBP', '£'),
  new Currency('Japanese Yen', 'JPY', '¥'),
  new Currency('Chinese Yuan', 'CNY', '¥'),
  new Currency('Korean Won', 'KRW', '₩'),
  new Currency('Canadian Dollar', 'CAD', '$'),
  new Currency('Russian Ruble', 'RUB', '₽'),
  new Currency('South African Rand', 'ZAR', 'R'),
  new Currency('Turkish Lira', 'TRY', '₺')
];
