import { Currency } from '@/model/currency';

export const currencies: Currency[] = [
  new Currency('United States Dollar', 'fa-usd', 'USD', '$'),
  new Currency('Euro', 'fa-eur', 'EUR', '€'),
  new Currency('British Pound', 'fa-gbp', 'GBP', '£'),
  new Currency('Japanese Yen', 'fa-jpy', 'JPY', '¥'),
  new Currency('Chinese Yuan', 'fa-jpy', 'CNY', '¥')
];
