import { Currency } from '@/model/currency';

export const currencies: Currency[] = [
  new Currency('United States Dollar', 'fa-usd', 'USD', '$'),
  new Currency('Euro', 'fa-eur', 'EUR', '€'),
  new Currency('British Pound', 'fa-gbp', 'GBP', '£'),
  new Currency('Japanese Yen', 'fa-jpy', 'JPY', '¥'),
  new Currency('Chinese Yuan', 'fa-jpy', 'CNY', '¥'),
  new Currency('Korean Won', 'fa-krw', 'KRW', '₩'),
  new Currency('Canadian Dollar', 'fa-cad', 'CAD', '$'),
  new Currency('Russian Ruble', 'fa-rub', 'RUB', '‎₽')
];
