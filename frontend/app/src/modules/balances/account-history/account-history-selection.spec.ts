import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';
import {
  accountHistoryLink,
  AccountHistoryRange,
  parseSelection,
  rangeStart,
  toSelectionQuery,
} from './account-history-selection';

describe('parseSelection', () => {
  it('should read the account, asset, location and range from the query', () => {
    expect(parseSelection({ account: '0xA', asset: 'ETH', location: 'optimism', range: '3m' })).toEqual({
      account: '0xA',
      asset: 'ETH',
      location: 'optimism',
      range: AccountHistoryRange.QUARTER,
    });
  });

  it('should read missing or empty values as unset and an unknown range as all time', () => {
    expect(parseSelection({ account: '', range: '2y' })).toEqual({
      account: undefined,
      asset: undefined,
      location: undefined,
      range: AccountHistoryRange.ALL,
    });
  });

  it('should keep the first value of a repeated key', () => {
    expect(parseSelection({ asset: ['ETH', 'DAI'] }).asset).toBe('ETH');
  });
});

describe('toSelectionQuery', () => {
  it('should leave out unset values and the default range', () => {
    expect(toSelectionQuery({ account: '0xA', asset: undefined, location: undefined, range: AccountHistoryRange.ALL }))
      .toEqual({ account: '0xA' });
  });

  it('should round-trip through parseSelection', () => {
    const selection = { account: '0xA', asset: 'ETH', location: 'ethereum', range: AccountHistoryRange.YEAR };

    expect(parseSelection(toSelectionQuery(selection))).toEqual(selection);
  });
});

describe('accountHistoryLink', () => {
  it('should link to the page with the account, asset and location picked', () => {
    expect(accountHistoryLink('0xA', 'ETH', 'ethereum')).toEqual({
      name: '/balances/history/',
      query: { account: '0xA', asset: 'ETH', location: 'ethereum' },
    });
  });
});

describe('rangeStart', () => {
  const now = dayjs('2026-11-13T12:00:00Z').unix();

  it('should start all time at zero', () => {
    expect(rangeStart(AccountHistoryRange.ALL, now)).toBe(0);
  });

  it('should go back whole calendar months', () => {
    expect(rangeStart(AccountHistoryRange.MONTH, now)).toBe(dayjs('2026-10-13T12:00:00Z').unix());
    expect(rangeStart(AccountHistoryRange.YEAR, now)).toBe(dayjs('2025-11-13T12:00:00Z').unix());
  });
});
