import { splitSearch } from '@/utils/search';
import { describe, expect, it } from 'vitest';

describe('utils/search', () => {
  it('splitSearch return correct result', () => {
    expect(splitSearch(null)).toStrictEqual({ key: '', value: '', exclude: undefined });
    expect(splitSearch('base:ETH')).toStrictEqual({ key: 'base', value: 'ETH', exclude: false });
    expect(splitSearch('base=ETH')).toStrictEqual({ key: 'base', value: 'ETH', exclude: false });
    expect(splitSearch('action:settlement buy')).toStrictEqual({
      key: 'action',
      value: 'settlement buy',
      exclude: false,
    });
    expect(splitSearch('action=settlement buy')).toStrictEqual({
      key: 'action',
      value: 'settlement buy',
      exclude: false,
    });
    expect(splitSearch('start:30/12/2023 12:12:12')).toStrictEqual({
      key: 'start',
      value: '30/12/2023 12:12:12',
      exclude: false,
    });
    expect(splitSearch('start=30/12/2023 12:12:12')).toStrictEqual({
      key: 'start',
      value: '30/12/2023 12:12:12',
      exclude: false,
    });
    expect(splitSearch('keyword=abcde=fghi: jkl')).toStrictEqual({
      key: 'keyword',
      value: 'abcde=fghi: jkl',
      exclude: false,
    });
    expect(splitSearch('keyword!=exclude')).toStrictEqual({ key: 'keyword', value: 'exclude', exclude: true });
  });
});
