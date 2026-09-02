import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { fieldSuggestions, searchFieldsAndValues as search, syntaxExamples } from '@/modules/core/table/pill/core/narrowing';

const operatorLabels = {
  after: 'after',
  before: 'before',
  between: 'between',
  gt: 'greater than',
  is: 'is',
  is_not: 'is not',
  lt: 'less than',
} as const;

function searchFieldsAndValues(
  query: string,
  fields: Parameters<typeof search>[1],
  limits?: Parameters<typeof search>[3],
  recentValues?: Parameters<typeof search>[4],
  syntaxHints?: Parameters<typeof search>[5],
): ReturnType<typeof search> {
  return search(query, fields, operatorLabels, limits, recentValues, syntaxHints);
}

function field(overrides: Partial<FieldDef> & Pick<FieldDef, 'key' | 'label'>): FieldDef {
  return {
    allowExclusion: false,
    binding: { kind: 'filter' },
    multiple: true,
    operators: ['is'],
    valueType: FilterValueTypes.ENUM,
    ...overrides,
  };
}

const protocol = field({
  key: 'protocol',
  label: 'Protocol',
  suggest: (): string[] => ['aave', 'uniswap', 'ethena'],
});

const asset = field({
  key: 'asset',
  label: 'Asset',
  valueType: FilterValueTypes.ASSET,
});

const notes = field({
  freeText: true,
  key: 'notes',
  label: 'Notes',
  suggest: (): string[] => ['never offered'],
  validate: (value: string): boolean => value.length > 0,
});

const txHash = field({
  freeText: true,
  key: 'txHash',
  label: 'Tx hash',
  validate: (value: string): boolean => /^0x[a-f0-9]{6}$/i.test(value),
});

const account = field({
  display: 'account',
  key: 'account',
  label: 'Account',
  resolveCaption: (value: string): string => `0x${value.slice(2, 6)}...`,
  resolveKeywords: (value: string): string => `${value} alice.eth wallet`.toLowerCase(),
  resolveLabel: (value: string): string => (value === '0xAAAA1111' ? 'Savings' : '0xBBBB...'),
  suggest: (): string[] => ['0xAAAA1111', '0xBBBB2222'],
});

const amount = field({
  formatBound: (value: string): string => `${value} ETH`,
  key: 'amount',
  label: 'Amount',
  matchesTyped: (query: string): boolean => /^[\d<>]/.test(query),
  operators: ['between', 'gt', 'lt'],
  parseTyped: (query: string) => (/^\d+$/.test(query)
    ? [
        { op: 'gt' as const, range: { min: query }, values: [] },
        { op: 'lt' as const, range: { max: query }, values: [] },
      ]
    : []),
  valueType: FilterValueTypes.RANGE,
});

const period = field({
  key: 'period',
  label: 'Period',
  matchesTyped: (query: string): boolean =>
    query.startsWith('after') || query.startsWith('15/') || query.startsWith('peri'),
  operators: ['between', 'after', 'before'],
  parseTyped: (query: string) => (query === '15/01/2024'
    ? [{ date: { from: '1705276800' }, op: 'after' as const, values: [] }]
    : []),
  valueType: FilterValueTypes.DATE,
});

const hints = {
  examples: { date: ['after 15/01/2024', '15/01/2024 - 20/01/2024'], range: ['>100'] },
  keywords: { date: 'date time when', range: 'amount number value' },
};

describe('fieldSuggestions', () => {
  it('should offer every field as itself', () => {
    expect(fieldSuggestions([protocol, asset])).toEqual([
      { field: protocol, kind: 'field', label: 'Protocol' },
      { field: asset, kind: 'field', label: 'Asset' },
    ]);
  });

  it('should offer nothing when every field is in use', () => {
    expect(fieldSuggestions([])).toEqual([]);
  });
});

describe('syntaxExamples', () => {
  it('should offer the examples of every typed-into type on offer', () => {
    expect(syntaxExamples([period, amount, protocol], hints)).toStrictEqual([
      'after 15/01/2024',
      '15/01/2024 - 20/01/2024',
      '>100',
    ]);
  });

  it('should offer nothing for the types not on offer', () => {
    expect(syntaxExamples([protocol], hints)).toStrictEqual([]);
    expect(syntaxExamples([period], hints)).toStrictEqual(['after 15/01/2024', '15/01/2024 - 20/01/2024']);
  });

  it('should ignore a field of a typed-into type that reads nothing typed', () => {
    const bare = field({ key: 'bare', label: 'Bare', valueType: FilterValueTypes.DATE });
    expect(syntaxExamples([bare], hints)).toStrictEqual([]);
  });

  it('should offer one set of examples for two fields of the same type', () => {
    const second = field({ ...period, key: 'settled', label: 'Settled' });
    expect(syntaxExamples([period, second], hints)).toStrictEqual(['after 15/01/2024', '15/01/2024 - 20/01/2024']);
  });
});

describe('searchFieldsAndValues', () => {
  it('should return nothing for a blank query', () => {
    expect(searchFieldsAndValues('', [protocol])).toEqual([]);
    expect(searchFieldsAndValues('   ', [protocol])).toEqual([]);
  });

  it('should match fields and values in one pass', () => {
    const result = searchFieldsAndValues('eth', [asset, protocol]);

    expect(result).toEqual([
      { field: protocol, kind: 'value', label: 'ethena', value: 'ethena' },
    ]);
  });

  it('should rank a field-label prefix above a value prefix', () => {
    const result = searchFieldsAndValues('as', [protocol, asset, field({
      key: 'other',
      label: 'Other',
      suggest: (): string[] => ['aster'],
    })]);

    expect(result.map(entry => [entry.kind, entry.label])).toEqual([
      ['field', 'Asset'],
      ['value', 'aster'],
    ]);
  });

  it('should rank a value prefix above a field-label substring', () => {
    const wave = field({ key: 'wave', label: 'Wave' });
    const other = field({ key: 'other', label: 'Other', suggest: (): string[] => ['aveline'] });

    const result = searchFieldsAndValues('ave', [wave, other]);

    expect(result.map(entry => entry.label)).toEqual(['aveline', 'Wave']);
  });

  it('should offer values by their resolved display label', () => {
    const location = field({
      key: 'location',
      label: 'Location',
      resolveLabel: (value: string): string => (value === 'polygon_pos' ? 'Polygon PoS' : value),
      suggest: (): string[] => ['polygon_pos'],
    });

    const result = searchFieldsAndValues('polygon p', [location]);

    expect(result).toEqual([
      { field: location, kind: 'value', label: 'Polygon PoS', value: 'polygon_pos' },
    ]);
  });

  it('should not offer list values for free-text or asset fields', () => {
    expect(searchFieldsAndValues('never', [asset])).toEqual([]);
    expect(searchFieldsAndValues('never', [notes])).toEqual([
      { field: notes, kind: 'value', label: 'never', value: 'never' },
    ]);
  });

  it('should offer a typed value once a free-text field accepts it', () => {
    expect(searchFieldsAndValues('0xabc123', [txHash])).toEqual([
      { field: txHash, kind: 'value', label: '0xabc123', value: '0xabc123' },
    ]);
  });

  it('should not offer a typed value its field rejects', () => {
    expect(searchFieldsAndValues('0xab', [txHash])).toEqual([]);
  });

  it('should echo the typed text rather than a resolved display form', () => {
    const address = field({
      freeText: true,
      key: 'address',
      label: 'Address',
      resolveLabel: (): string => 'scrambled',
    });

    expect(searchFieldsAndValues('0xdeadbeef', [address])[0].label).toBe('0xdeadbeef');
  });

  it('should rank a typed value below every matched field and value', () => {
    const result = searchFieldsAndValues('aave', [notes, protocol]);

    expect(result.map(entry => [entry.field.key, entry.label])).toEqual([
      ['protocol', 'aave'],
      ['notes', 'aave'],
    ]);
  });

  it('should cap the values offered per field', () => {
    const many = field({
      key: 'many',
      label: 'Many',
      suggest: (): string[] => ['zz1', 'zz2', 'zz3', 'zz4', 'zz5', 'zz6'],
    });

    const result = searchFieldsAndValues('zz', [many], { perField: 2, total: 20 });

    expect(result.map(entry => entry.label)).toEqual(['zz1', 'zz2']);
  });

  it('should cap the suggestions returned in total', () => {
    const many = field({
      key: 'many',
      label: 'Many',
      suggest: (): string[] => ['zz1', 'zz2', 'zz3', 'zz4', 'zz5'],
    });

    expect(searchFieldsAndValues('zz', [many], { perField: 5, total: 3 })).toHaveLength(3);
  });

  it('should offer a remembered value that matches, ranked above the typed one', () => {
    const address = field({ freeText: true, key: 'address', label: 'Address' });
    const recent = (): string[] => ['0xabc123', '0xdef456'];

    const result = searchFieldsAndValues('0xabc', [address], { perField: 5, total: 20 }, recent);

    expect(result.map(entry => entry.label)).toEqual(['0xabc123', '0xabc']);
  });

  it('should not repeat a remembered value as the typed one', () => {
    const address = field({ freeText: true, key: 'address', label: 'Address' });
    const recent = (): string[] => ['0xabc'];

    const result = searchFieldsAndValues('0xabc', [address], { perField: 5, total: 20 }, recent);

    expect(result.map(entry => entry.label)).toEqual(['0xabc']);
  });

  it('should ignore remembered values that do not match', () => {
    const address = field({ freeText: true, key: 'address', label: 'Address' });
    const recent = (): string[] => ['0xzzz'];

    const result = searchFieldsAndValues('0xabc', [address], { perField: 5, total: 20 }, recent);

    expect(result.map(entry => entry.label)).toEqual(['0xabc']);
  });

  it('should keep the declared order within a rank', () => {
    const result = searchFieldsAndValues('a', [protocol]);

    expect(result.map(entry => entry.label)).toEqual(['aave', 'uniswap', 'ethena']);
  });
});

describe('searchFieldsAndValues account keywords', () => {
  it('should find an account by its visible label', () => {
    const [first] = searchFieldsAndValues('savings', [account]);
    expect(first).toMatchObject({ kind: 'value', label: 'Savings', value: '0xAAAA1111' });
  });

  it('should find an account by a full address the label never shows', () => {
    const matches = searchFieldsAndValues('0xaaaa1111', [account]);
    expect(matches).toHaveLength(1);
    expect(matches[0]).toMatchObject({ kind: 'value', value: '0xAAAA1111' });
  });

  it('should find an account by its ens name', () => {
    const matches = searchFieldsAndValues('alice.eth', [account]);
    expect(matches.map(match => match.kind === 'value' && match.value)).toStrictEqual(['0xAAAA1111', '0xBBBB2222']);
  });

  it('should rank a label match above a keyword-only match', () => {
    const matches = searchFieldsAndValues('wallet', [account]);
    expect(matches.every(match => match.kind === 'value')).toBe(true);
  });

  it('should carry the caption so two accounts are told apart', () => {
    const [first] = searchFieldsAndValues('savings', [account]);
    expect(first).toMatchObject({ caption: '0xAAAA...' });
  });
  describe('written values', () => {
    it('should offer the filters a field reads out of the query', () => {
      const matches = searchFieldsAndValues('100', [amount]);

      expect(matches).toStrictEqual([
        { field: amount, filter: { fieldKey: 'amount', op: 'gt', range: { min: '100' }, values: [] }, kind: 'filter', label: 'greater than 100 ETH' },
        { field: amount, filter: { fieldKey: 'amount', op: 'lt', range: { max: '100' }, values: [] }, kind: 'filter', label: 'less than 100 ETH' },
      ]);
    });

    it('should hide the operator when it is the field default, as the pill it produces does', () => {
      const between = field({
        key: 'amount',
        label: 'Amount',
        operators: ['between', 'gt'],
        parseTyped: () => [{ op: 'between' as const, range: { max: '50', min: '10' }, values: [] }],
        valueType: FilterValueTypes.RANGE,
      });

      expect(searchFieldsAndValues('10-50', [between])[0]).toMatchObject({ label: '10 - 50' });
    });

    it('should offer nothing for a query the field cannot read', () => {
      expect(searchFieldsAndValues('uniswap', [amount])).toStrictEqual([]);
    });

    it('should offer the field with its example for a half-written value', () => {
      expect(searchFieldsAndValues('after', [period], undefined, undefined, hints)).toStrictEqual([
        { field: period, kind: 'field', label: 'Period' },
      ]);
    });

    it('should not offer guidance once the query reads as a filter', () => {
      const matches = searchFieldsAndValues('15/01/2024', [period], undefined, undefined, hints);
      expect(matches).toHaveLength(1);
      expect(matches[0]).toMatchObject({ kind: 'filter' });
    });

    it('should rank guidance below every real match', () => {
      const matches = searchFieldsAndValues('after', [period, field({
        key: 'protocol',
        label: 'Aftermath',
        suggest: (): string[] => [],
      })], undefined, undefined, hints);

      expect(matches[0]).toMatchObject({ label: 'Aftermath' });
      expect(matches[1]).toMatchObject({ label: 'Period' });
    });

    it('should find a field by the words its value type is known by, which its label does not contain', () => {
      expect(searchFieldsAndValues('time', [period], undefined, undefined, hints)).toStrictEqual([
        { field: period, kind: 'field', label: 'Period' },
      ]);
    });

    it('should not match a keyword on a fragment of one, while the whole word and its prefixes still do', () => {
      const shipped = {
        keywords: {
          date: 'date time when period since after before until',
          range: 'amount number value range more less over under above below at least at most',
        },
      };

      expect(searchFieldsAndValues('in', [period], undefined, undefined, shipped)).toStrictEqual([]);
      expect(searchFieldsAndValues('an', [amount], undefined, undefined, shipped)).toStrictEqual([]);
      expect(searchFieldsAndValues('since', [period], undefined, undefined, shipped)).toStrictEqual([
        { field: period, kind: 'field', label: 'Period' },
      ]);
      expect(searchFieldsAndValues('num', [amount], undefined, undefined, shipped)).toStrictEqual([
        { field: amount, kind: 'field', label: 'Amount' },
      ]);
      expect(searchFieldsAndValues('at le', [amount], undefined, undefined, shipped)).toStrictEqual([
        { field: amount, kind: 'field', label: 'Amount' },
      ]);
    });

    it('should offer a field only once when its label and its guidance both match', () => {
      expect(period.matchesTyped?.('peri')).toBe(true);

      const matches = searchFieldsAndValues('peri', [period], undefined, undefined, hints);
      expect(matches).toStrictEqual([
        { field: period, kind: 'field', label: 'Period' },
      ]);
    });

    it('should rank a read-out filter below a matching field or value', () => {
      const matches = searchFieldsAndValues('100', [amount, field({
        key: 'validator',
        label: '100',
        suggest: (): string[] => [],
      })]);

      expect(matches[0]).toMatchObject({ kind: 'field' });
    });
  });
  it('should match a remembered value on what was stored but show it through the field resolver', () => {
    const address = field({
      freeText: true,
      key: 'addresses',
      label: 'Address',
      resolveLabel: (value: string): string => `0x${value.slice(2, 6)}...scrambled`,
      validate: (): boolean => false,
    });

    const [match] = searchFieldsAndValues('0xd8da', [address], undefined, () => ['0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045']);

    expect(match).toMatchObject({
      kind: 'value',
      label: '0xd8dA...scrambled',
      value: '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045',
    });
  });
});
