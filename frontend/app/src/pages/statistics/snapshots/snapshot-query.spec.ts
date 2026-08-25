import { describe, expect, it } from 'vitest';
import { parseSnapshotFilters, toSnapshotQuery } from './snapshot-query';

const DEFAULT_LIMIT = 10;

describe('pages/statistics/snapshots/parseSnapshotFilters', () => {
  it('should read both bounds as numbers', () => {
    expect(parseSnapshotFilters({ from: '100', to: '200' })).toEqual({
      fromTimestamp: 100,
      toTimestamp: 200,
    });
  });

  it('should read an absent bound as no bound', () => {
    expect(parseSnapshotFilters({})).toEqual({
      fromTimestamp: undefined,
      toTimestamp: undefined,
    });
  });

  it('should read one bound without the other', () => {
    expect(parseSnapshotFilters({ from: '100' })).toEqual({
      fromTimestamp: 100,
      toTimestamp: undefined,
    });
  });

  it('should reject a bound that is not a number rather than passing NaN on', () => {
    // NaN would compare false against every timestamp and read as an empty account.
    expect(parseSnapshotFilters({ from: 'yesterday' })).toEqual({
      fromTimestamp: undefined,
      toTimestamp: undefined,
    });
  });

  it('should reject an empty bound, which Number() would otherwise read as zero', () => {
    expect(parseSnapshotFilters({ from: '' }).fromTimestamp).toBeUndefined();
  });

  it('should keep a zero bound that was actually asked for', () => {
    expect(parseSnapshotFilters({ from: '0' }).fromTimestamp).toBe(0);
  });
});

describe('pages/statistics/snapshots/toSnapshotQuery', () => {
  const firstPage = { limit: DEFAULT_LIMIT, page: 1, total: 100 };

  it('should be empty when nothing differs from the defaults', () => {
    expect(toSnapshotQuery({}, firstPage, DEFAULT_LIMIT)).toEqual({});
  });

  it('should carry both bounds when they are set', () => {
    expect(toSnapshotQuery({ fromTimestamp: 100, toTimestamp: 200 }, firstPage, DEFAULT_LIMIT)).toEqual({
      from: 100,
      to: 200,
    });
  });

  it('should carry a zero bound, which is a real bound', () => {
    expect(toSnapshotQuery({ fromTimestamp: 0 }, firstPage, DEFAULT_LIMIT)).toEqual({ from: 0 });
  });

  it('should leave the first page out', () => {
    expect(toSnapshotQuery({}, { ...firstPage, page: 1 }, DEFAULT_LIMIT)).toEqual({});
  });

  it('should carry any later page', () => {
    expect(toSnapshotQuery({}, { ...firstPage, page: 3 }, DEFAULT_LIMIT)).toEqual({ page: 3 });
  });

  it('should leave the default page size out', () => {
    expect(toSnapshotQuery({}, { ...firstPage, limit: DEFAULT_LIMIT }, DEFAULT_LIMIT)).toEqual({});
  });

  it('should carry a page size that differs from the default', () => {
    expect(toSnapshotQuery({}, { ...firstPage, limit: 25 }, DEFAULT_LIMIT)).toEqual({ limit: 25 });
  });

  it('should carry everything at once', () => {
    expect(toSnapshotQuery(
      { fromTimestamp: 100, toTimestamp: 200 },
      { limit: 25, page: 3, total: 100 },
      DEFAULT_LIMIT,
    )).toEqual({ from: 100, limit: 25, page: 3, to: 200 });
  });

  it('should round-trip a query back through the filter parser', () => {
    const filters = { fromTimestamp: 100, toTimestamp: 200 };

    const query = toSnapshotQuery(filters, firstPage, DEFAULT_LIMIT);

    expect(parseSnapshotFilters({ from: String(query.from), to: String(query.to) })).toEqual(filters);
  });
});
