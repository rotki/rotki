import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { DEFAULT_OPERATORS, defaultOp, isDefaultOp, operatorsFor } from '@/modules/core/table/pill/core/operators';

function field(partial: Partial<FieldDef>): FieldDef {
  return {
    allowExclusion: false,
    binding: { kind: 'filter' },
    key: 'k',
    label: 'K',
    multiple: false,
    operators: [],
    valueType: 'enum',
    ...partial,
  };
}

describe('pill operators', () => {
  it('should define a non-empty operator set for every value type', () => {
    for (const ops of Object.values(DEFAULT_OPERATORS))
      expect(ops.length).toBeGreaterThan(0);
  });

  it('should prefer the field operators when provided', () => {
    expect(operatorsFor(field({ operators: ['gt', 'lt'] }))).toStrictEqual(['gt', 'lt']);
  });

  it('should fall back to the value-type defaults when the field lists none', () => {
    expect(operatorsFor(field({ operators: [], valueType: 'range' }))).toStrictEqual(DEFAULT_OPERATORS.range);
  });

  it('should treat the first allowed operator as the default', () => {
    expect(defaultOp(field({ valueType: 'range' }))).toBe('between');
    expect(defaultOp(field({ operators: ['is_not', 'is'] }))).toBe('is_not');
  });

  it('should flag only the default operator as default', () => {
    const f = field({ valueType: 'enum' });
    expect(isDefaultOp(f, 'is')).toBe(true);
    expect(isDefaultOp(f, 'is_not')).toBe(false);
  });
});
