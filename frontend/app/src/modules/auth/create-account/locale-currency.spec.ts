import { describe, expect, it } from 'vitest';
import { suggestCurrency } from '@/modules/auth/create-account/locale-currency';

describe('suggestCurrency', () => {
  it.each([
    ['en-US', 'USD'],
    ['en-GB', 'GBP'],
    ['de-DE', 'EUR'],
    ['de-CH', 'CHF'],
    ['fr-CA', 'CAD'],
    ['es-MX', 'MXN'],
    ['ja-JP', 'JPY'],
    ['bg-BG', 'EUR'],
  ])('should suggest the currency of the locale\'s country for %s', (locale, expected) => {
    expect(suggestCurrency(locale)).toBe(expected);
  });

  it.each([
    ['de', 'EUR'],
    ['el', 'EUR'],
    ['ja', 'JPY'],
    ['pt', 'BRL'],
  ])('should take the likeliest country of a language without one, %s', (locale, expected) => {
    expect(suggestCurrency(locale)).toBe(expected);
  });

  it('should fall back to US dollars for a country rotki has no currency for', () => {
    expect(suggestCurrency('hu-HU')).toBe('USD');
  });

  it('should fall back to US dollars for a malformed locale', () => {
    expect(suggestCurrency('not a locale!')).toBe('USD');
  });

  it('should fall back to US dollars for an empty locale', () => {
    expect(suggestCurrency('')).toBe('USD');
  });
});
