import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { get } from '@vueuse/shared';
import { describe, expect, it } from 'vitest';
import { useFilterState } from '@/modules/core/table/pill/composables/use-filter-state';

const protocol: FieldDef = {
  allowExclusion: true,
  binding: { kind: 'filter' },
  key: 'protocols',
  label: 'Protocol',
  multiple: true,
  operators: ['is', 'is_not'],
  valueType: 'enum',
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

const account: FieldDef = {
  allowExclusion: false,
  binding: { kind: 'param', paramKey: 'locationLabels', to: 'both' },
  key: 'account',
  label: 'Account',
  multiple: true,
  operators: ['is'],
  valueType: 'asset',
};

const fields = [protocol, ignored, account];

describe('useFilterState', () => {
  it('should start empty', () => {
    const { matches, params, state } = useFilterState(fields);
    expect(get(state)).toStrictEqual([]);
    expect(get(matches)).toStrictEqual({});
    expect(get(params)).toStrictEqual({});
  });

  it('should add a filter and derive matches', () => {
    const { addFilter, matches, state } = useFilterState(fields);
    addFilter({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    expect(get(state)).toHaveLength(1);
    expect(get(matches)).toStrictEqual({ protocols: ['aave'] });
  });

  it('should replace an existing filter for the same field', () => {
    const { addFilter, state } = useFilterState(fields);
    addFilter({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    addFilter({ fieldKey: 'protocols', op: 'is_not', values: ['uniswap'] });
    expect(get(state)).toStrictEqual([{ fieldKey: 'protocols', op: 'is_not', values: ['uniswap'] }]);
  });

  it('should route a param-bound field into params', () => {
    const { addFilter, matches, params } = useFilterState(fields);
    addFilter({ fieldKey: 'account', op: 'is', values: ['0xaaa'] });
    expect(get(matches)).toStrictEqual({});
    expect(get(params)).toStrictEqual({ locationLabels: ['0xaaa'] });
  });

  it('should patch an existing filter and no-op an absent one', () => {
    const { addFilter, state, updateFilter } = useFilterState(fields);
    addFilter({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    updateFilter('protocols', { op: 'is_not' });
    expect(get(state)).toStrictEqual([{ fieldKey: 'protocols', op: 'is_not', values: ['aave'] }]);
    updateFilter('missing', { op: 'is' });
    expect(get(state)).toStrictEqual([{ fieldKey: 'protocols', op: 'is_not', values: ['aave'] }]);
  });

  it('should remove and clear filters', () => {
    const { addFilter, clearAll, removeFilter, state } = useFilterState(fields);
    addFilter({ fieldKey: 'protocols', op: 'is', values: ['aave'] });
    addFilter({ fieldKey: 'account', op: 'is', values: ['0xaaa'] });
    removeFilter('protocols');
    expect(get(state)).toStrictEqual([{ fieldKey: 'account', op: 'is', values: ['0xaaa'] }]);
    clearAll();
    expect(get(state)).toStrictEqual([]);
  });

  it('should rebuild the state from an external matches + params', () => {
    const { setFromMatches, state } = useFilterState(fields);
    setFromMatches({ protocols: ['!aave'] }, { locationLabels: ['0xaaa'] });
    expect(get(state)).toStrictEqual([
      { fieldKey: 'protocols', op: 'is_not', values: ['aave'] },
      { fieldKey: 'account', op: 'is', values: ['0xaaa'] },
    ]);
  });

  // The bar is the only place the rule is applied, so every door into the state has to pass through
  // it. A user edit and a route restore are two different doors.
  describe('admissibility', () => {
    const subtypes: FieldDef = {
      admits: values => ((values.types ?? []).includes('spend') ? ['fee'] : []),
      allowExclusion: false,
      binding: { kind: 'filter' },
      key: 'subtypes',
      label: 'Subtype',
      multiple: true,
      operators: ['is'],
      valueType: 'enum',
    };
    const types: FieldDef = { ...protocol, key: 'types', label: 'Type' };
    const narrowing = [types, subtypes];

    it('should drop a value once an edit stops admitting it', () => {
      const { addFilter, matches } = useFilterState(narrowing);
      addFilter({ fieldKey: 'types', op: 'is', values: ['spend'] });
      addFilter({ fieldKey: 'subtypes', op: 'is', values: ['fee', 'airdrop'] });

      expect(get(matches).subtypes).toStrictEqual(['fee']);
    });

    it('should drop a value arriving from the route', () => {
      const { matches, setFromMatches } = useFilterState(narrowing);
      setFromMatches({ subtypes: ['airdrop', 'fee'], types: ['spend'] }, {});

      expect(get(matches).subtypes).toStrictEqual(['fee']);
    });

    // The option list is store-backed, so a restored link can land before the mapping does. The
    // value is kept then, and pruned when the list finally arrives — without this the bar would
    // have to be touched again before it corrected itself.
    it('should re-prune when the option list arrives late', async () => {
      const loaded = ref<boolean>(false);
      const late: FieldDef = {
        ...subtypes,
        admits: values => (get(loaded) && (values.types ?? []).includes('spend') ? ['fee'] : []),
      };
      const { matches, setFromMatches } = useFilterState(() => [types, late]);

      setFromMatches({ subtypes: ['airdrop'], types: ['spend'] }, {});
      expect(get(matches).subtypes).toStrictEqual(['airdrop']);

      set(loaded, true);
      await nextTick();

      expect(get(matches).subtypes).toBeUndefined();
    });
  });

  it('should skip the self echo so a round-trip does not reorder', () => {
    const { addFilter, matches, params, setFromMatches, state } = useFilterState(fields);
    addFilter({ fieldKey: 'protocols', op: 'is', values: ['aave', 'uniswap'] });
    const before = get(state);
    // echo of our own emit: identical wire form must not rebuild
    setFromMatches(get(matches), get(params));
    expect(get(state)).toBe(before);
    // an explicit self source is also skipped
    setFromMatches({ protocols: ['curve'] }, {}, 'self');
    expect(get(state)).toBe(before);
  });
});
