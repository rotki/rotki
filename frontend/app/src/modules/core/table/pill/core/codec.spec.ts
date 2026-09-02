import type { FieldDef, FilterState } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { FilterBehaviours } from '@/modules/core/table/filtering';
import { hasWritableValue, matchesFromState, stateFromMatches } from '@/modules/core/table/pill/core/codec';

const protocol: FieldDef = {
  allowExclusion: true,
  binding: { kind: 'filter' },
  key: 'protocols',
  label: 'Protocol',
  multiple: true,
  operators: ['is', 'is_not'],
  valueType: 'enum',
};

const asset: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
  key: 'assets',
  label: 'Asset',
  multiple: true,
  operators: ['is'],
  valueType: 'asset',
};

const ignored: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
  key: 'excludeIgnoredAssets',
  label: 'Ignored',
  multiple: false,
  operators: ['is'],
  valueType: 'boolean',
};

const showIgnored: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'param', paramKey: 'showIgnoredAssets', to: 'both' },
  key: 'ignored',
  label: 'Show ignored',
  multiple: false,
  operators: ['is'],
  valueType: 'boolean',
};

const account: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'param', paramKey: 'locationLabels', to: 'both' },
  key: 'account',
  label: 'Account',
  multiple: true,
  operators: ['is'],
  valueType: 'asset',
};

const amount: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
  bounds: { lower: 'minAmount', upper: 'maxAmount' },
  key: 'amount',
  label: 'Amount',
  multiple: false,
  operators: ['between', 'gt', 'lt'],
  valueType: 'range',
};

const period: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'filter' },
  bounds: { lower: 'fromTimestamp', upper: 'toTimestamp' },
  deserializer: (value: string) => `d:${value}`,
  key: 'period',
  label: 'Period',
  multiple: false,
  operators: ['between', 'after', 'before'],
  serializer: (value: string) => `ts:${value}`,
  valueType: 'date',
};

const fields = [protocol, asset, ignored, account, amount, period];

describe('pill codec', () => {
  describe('matchesFromState', () => {
    it('should serialize a multi enum field into the matches bag', () => {
      const state: FilterState = [{ fieldKey: 'protocols', op: 'is', values: ['aave', 'uniswap'] }];
      expect(matchesFromState(state, fields)).toStrictEqual({
        matches: { protocols: ['aave', 'uniswap'] },
        params: {},
      });
    });

    it('should prefix excluded (is_not) enum values with !', () => {
      const state: FilterState = [{ fieldKey: 'protocols', op: 'is_not', values: ['aave'] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({ protocols: ['!aave'] });
    });

    it('should drop is_not and apply as is on a field that does not allow exclusion', () => {
      const state: FilterState = [{ fieldKey: 'assets', op: 'is_not', values: ['ETH'] }];

      expect(matchesFromState(state, fields).matches).toStrictEqual({ assets: ['ETH'] });
    });

    it('should serialize a boolean field as true', () => {
      const state: FilterState = [{ fieldKey: 'excludeIgnoredAssets', op: 'is', values: [] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({ excludeIgnoredAssets: true });
    });

    it('should route a param-bound boolean into params as a real boolean, not a stringified one', () => {
      const state: FilterState = [{ fieldKey: 'ignored', op: 'is', values: [] }];
      expect(matchesFromState(state, [...fields, showIgnored])).toStrictEqual({
        matches: {},
        params: { showIgnoredAssets: true },
      });
    });

    it('should rebuild a param-bound boolean pill from its param', () => {
      const state = stateFromMatches({}, { showIgnoredAssets: true }, [...fields, showIgnored]);
      expect(state).toStrictEqual([{ fieldKey: 'ignored', op: 'is', values: [] }]);
    });

    it('should drop a param-bound boolean that is absent or false', () => {
      expect(stateFromMatches({}, {}, [...fields, showIgnored])).toStrictEqual([]);
      expect(stateFromMatches({}, { showIgnoredAssets: false }, [...fields, showIgnored])).toStrictEqual([]);
    });

    it('should route a param-bound field into params, not matches', () => {
      const state: FilterState = [{ fieldKey: 'account', op: 'is', values: ['0xaaa', '0xbbb'] }];
      expect(matchesFromState(state, fields)).toStrictEqual({
        matches: {},
        params: { locationLabels: ['0xaaa', '0xbbb'] },
      });
    });

    it('should drop a field with no values and ignore unknown fields', () => {
      const state: FilterState = [
        { fieldKey: 'protocols', op: 'is', values: [] },
        { fieldKey: 'nope', op: 'is', values: ['x'] },
      ];
      expect(matchesFromState(state, fields)).toStrictEqual({ matches: {}, params: {} });
    });

    it('should not prefix ! when the field cannot exclude', () => {
      const state: FilterState = [{ fieldKey: 'assets', op: 'is_not', values: ['ETH'] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({ assets: ['ETH'] });
    });

    it('should fold a range field into its two wire keys', () => {
      const state: FilterState = [{ fieldKey: 'amount', op: 'between', range: { max: '10', min: '1' }, values: [] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({ maxAmount: '10', minAmount: '1' });
    });

    it('should write only the lower bound for a gt range', () => {
      const state: FilterState = [{ fieldKey: 'amount', op: 'gt', range: { max: '10', min: '1' }, values: [] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({ minAmount: '1' });
    });

    it('should write only the upper bound for an lt range', () => {
      const state: FilterState = [{ fieldKey: 'amount', op: 'lt', range: { max: '10', min: '1' }, values: [] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({ maxAmount: '10' });
    });

    it('should serialize each date bound to its wire key', () => {
      const state: FilterState = [{ date: { from: '2024-01-01', to: '2024-02-01' }, fieldKey: 'period', op: 'between', values: [] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({
        fromTimestamp: 'ts:2024-01-01',
        toTimestamp: 'ts:2024-02-01',
      });
    });

    it('should write only the from bound for an after date', () => {
      const state: FilterState = [{ date: { from: '2024-01-01', to: '2024-02-01' }, fieldKey: 'period', op: 'after', values: [] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({ fromTimestamp: 'ts:2024-01-01' });
    });

    it('should drop a range field with no bounds', () => {
      const state: FilterState = [{ fieldKey: 'amount', op: 'between', range: {}, values: [] }];
      expect(matchesFromState(state, fields).matches).toStrictEqual({});
    });
  });

  describe('stateFromMatches', () => {
    it('should rebuild an enum field from the matches bag', () => {
      const state = stateFromMatches({ protocols: ['aave', 'uniswap'] }, {}, fields);
      expect(state).toStrictEqual([{ fieldKey: 'protocols', op: 'is', values: ['aave', 'uniswap'] }]);
    });

    it('should decode a ! prefix into the is_not operator', () => {
      const state = stateFromMatches({ protocols: ['!aave'] }, {}, fields);
      expect(state).toStrictEqual([{ fieldKey: 'protocols', op: 'is_not', values: ['aave'] }]);
    });

    it('should decode a behaviour-wrapped exclude value', () => {
      const state = stateFromMatches(
        { protocols: { behaviour: FilterBehaviours.EXCLUDE, values: ['aave'] } },
        {},
        fields,
      );
      expect(state).toStrictEqual([{ fieldKey: 'protocols', op: 'is_not', values: ['aave'] }]);
    });

    it('should rebuild a boolean field', () => {
      expect(stateFromMatches({ excludeIgnoredAssets: true }, {}, fields))
        .toStrictEqual([{ fieldKey: 'excludeIgnoredAssets', op: 'is', values: [] }]);
      expect(stateFromMatches({ excludeIgnoredAssets: false }, {}, fields)).toStrictEqual([]);
    });

    it('should drop a stored key naming a field the table does not have', () => {
      const state = stateFromMatches({ gone: ['whatever'], protocols: ['aave'] }, { alsoGone: ['x'] }, fields);

      expect(state).toStrictEqual([{ fieldKey: 'protocols', op: 'is', values: ['aave'] }]);
    });

    it('should rebuild a param-bound field from params', () => {
      const state = stateFromMatches({}, { locationLabels: ['0xaaa', '0xbbb'] }, fields);
      expect(state).toStrictEqual([{ fieldKey: 'account', op: 'is', values: ['0xaaa', '0xbbb'] }]);
    });

    it('should rebuild a range field from both wire keys as between', () => {
      const state = stateFromMatches({ maxAmount: '10', minAmount: '1' }, {}, fields);
      expect(state).toStrictEqual([{ fieldKey: 'amount', op: 'between', range: { max: '10', min: '1' }, values: [] }]);
    });

    it('should infer gt when only the lower range key is present', () => {
      const state = stateFromMatches({ minAmount: '1' }, {}, fields);
      expect(state).toStrictEqual([{ fieldKey: 'amount', op: 'gt', range: { min: '1' }, values: [] }]);
    });

    it('should infer lt when only the upper range key is present', () => {
      const state = stateFromMatches({ maxAmount: '10' }, {}, fields);
      expect(state).toStrictEqual([{ fieldKey: 'amount', op: 'lt', range: { max: '10' }, values: [] }]);
    });

    it('should deserialize date wire keys and infer before', () => {
      const state = stateFromMatches({ toTimestamp: '1700000000' }, {}, fields);
      expect(state).toStrictEqual([{ date: { to: 'd:1700000000' }, fieldKey: 'period', op: 'before', values: [] }]);
    });
  });

  describe('round-trip', () => {
    it('should preserve state through matches and back for every field kind', () => {
      const state: FilterState = [
        { fieldKey: 'protocols', op: 'is_not', values: ['aave'] },
        { fieldKey: 'assets', op: 'is', values: ['ETH', 'BTC'] },
        { fieldKey: 'excludeIgnoredAssets', op: 'is', values: [] },
        { fieldKey: 'account', op: 'is', values: ['0xaaa'] },
      ];
      const { matches, params } = matchesFromState(state, fields);
      expect(stateFromMatches(matches, params, fields)).toStrictEqual(state);
    });

    it('should preserve a between range (no serializer) through the wire', () => {
      const state: FilterState = [{ fieldKey: 'amount', op: 'between', range: { max: '10', min: '1' }, values: [] }];
      const { matches, params } = matchesFromState(state, fields);
      expect(stateFromMatches(matches, params, fields)).toStrictEqual(state);
    });
  });

  describe('hasWritableValue', () => {
    it('should call a field with no value empty', () => {
      expect(hasWritableValue(protocol, { fieldKey: 'protocols', op: 'is', values: [] })).toBe(false);
      expect(hasWritableValue(protocol, { fieldKey: 'protocols', op: 'is', values: [''] })).toBe(false);
      expect(hasWritableValue(amount, { fieldKey: 'amount', op: 'between', range: {}, values: [] })).toBe(false);
      expect(hasWritableValue(period, { fieldKey: 'period', op: 'between', date: {}, values: [] })).toBe(false);
    });

    it('should call one bound enough for a range or a date', () => {
      expect(hasWritableValue(amount, { fieldKey: 'amount', op: 'gt', range: { min: '10' }, values: [] })).toBe(true);
      expect(hasWritableValue(period, { fieldKey: 'period', op: 'before', date: { to: '1' }, values: [] })).toBe(true);
    });

    it('should never call a boolean field empty, since presence is the whole value', () => {
      expect(hasWritableValue(ignored, { fieldKey: 'ignored', op: 'is', values: [] })).toBe(true);
    });
  });
});
