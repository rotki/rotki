import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { toPeriodField } from '@/modules/core/table/filters/shared/period-field';

const resolvers = createMock<SharedFieldResolvers>({
  formatDate: (value: string): string => `formatted:${value}`,
  parseDate: (value: string): string | undefined => (value === '01/01/2024' ? '1704067200' : undefined),
});

const bounds = { lowerKey: 'fromTimestamp', upperKey: 'toTimestamp' };

describe('toPeriodField', () => {
  it('should route the two bounds to the wire keys the table names', () => {
    expect(toPeriodField('common.period', bounds, resolvers)).toMatchObject({
      binding: { kind: 'filter' },
      bounds: { lower: 'fromTimestamp', upper: 'toTimestamp' },
      key: 'period',
      label: 'common.period',
      multiple: false,
      valueType: FilterValueTypes.DATE,
    });
  });

  it('should show a stored bound in the user configured date format', () => {
    expect(toPeriodField('common.period', bounds, resolvers).formatBound?.('1700000000')).toBe('formatted:1700000000');
  });

  it('should offer a written date as a filter', () => {
    const field = toPeriodField('common.period', bounds, resolvers);

    expect(field.parseTyped?.('01/01/2024')).not.toStrictEqual([]);
    expect(field.parseTyped?.('unparsable')).toStrictEqual([]);
  });

  // Inclusive second bounds, so an equal pair is a filter for exactly that second.
  it('should let the two bounds name the same second by default', () => {
    expect(toPeriodField('common.period', bounds, resolvers).allowEqualBounds).toBe(true);
  });

  it('should keep the bounds apart for a millisecond backed table', () => {
    const field = toPeriodField('common.period', { ...bounds, allowEqual: false }, resolvers);

    expect(field.allowEqualBounds).toBe(false);
  });

  it('should not serialize the bounds, which are stored as they are sent', () => {
    const field = toPeriodField('common.period', bounds, resolvers);

    expect(field.serializer).toBeUndefined();
    expect(field.deserializer).toBeUndefined();
  });
});
