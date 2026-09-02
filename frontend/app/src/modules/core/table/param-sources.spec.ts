import { describe, expect, it } from 'vitest';
import { FilterBehaviours, type MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { collectSources, mergeParams, type ParamSource, transformFilters } from '@/modules/core/table/param-sources';

type Filters = MatchedKeywordWithBehaviour<string>;

const TYPE = ['type'];

describe('transformFilters', () => {
  it('should return an empty bag unchanged', () => {
    expect(transformFilters({}, TYPE)).toStrictEqual({});
  });

  it('should return the filters unchanged when no key carries a behaviour', () => {
    const filters: Filters = { type: 'deposit' };
    expect(transformFilters(filters, [])).toStrictEqual({ type: 'deposit' });
  });

  it('should leave a key the table did not declare alone', () => {
    const filters: Filters = { location: 'kraken', type: 'deposit' };
    const result = transformFilters(filters, TYPE);
    expect(result).toStrictEqual({ location: 'kraken', type: { behaviour: FilterBehaviours.INCLUDE, values: 'deposit' } });
  });

  it('should ignore keys that are not present in the filters', () => {
    const filters: Filters = { location: 'kraken' };
    expect(transformFilters(filters, TYPE)).toStrictEqual({ location: 'kraken' });
  });

  it('should ignore falsy values', () => {
    const filters: Filters = { type: '' };
    expect(transformFilters(filters, TYPE)).toStrictEqual({ type: '' });
  });

  it('should wrap a plain string value with the INCLUDE behaviour', () => {
    const filters: Filters = { type: 'deposit' };
    const result = transformFilters(filters, TYPE);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviours.INCLUDE, values: 'deposit' } });
  });

  it('should wrap a boolean value with the INCLUDE behaviour', () => {
    const filters: Filters = { type: true };
    const result = transformFilters(filters, TYPE);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviours.INCLUDE, values: true } });
  });

  it('should resolve a leading ! on a string to EXCLUDE', () => {
    const filters: Filters = { type: '!deposit' };
    const result = transformFilters(filters, TYPE);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviours.EXCLUDE, values: 'deposit' } });
  });

  it('should resolve a leading ! on an array to EXCLUDE and strip every element', () => {
    const filters: Filters = { type: ['!deposit', '!withdrawal'] };
    const result = transformFilters(filters, TYPE);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviours.EXCLUDE, values: ['deposit', 'withdrawal'] } });
  });

  it('should keep an array as INCLUDE when its first element has no !', () => {
    const filters: Filters = { type: ['deposit', 'withdrawal'] };
    const result = transformFilters(filters, TYPE);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviours.INCLUDE, values: ['deposit', 'withdrawal'] } });
  });

  it('should normalize an already-wrapped value, defaulting the behaviour to INCLUDE', () => {
    const filters: Filters = { type: { values: 'deposit' } };
    const result = transformFilters(filters, TYPE);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviours.INCLUDE, values: 'deposit' } });
  });

  it('should preserve an explicit behaviour on an already-wrapped value', () => {
    const filters: Filters = { type: { behaviour: FilterBehaviours.EXCLUDE, values: 'deposit' } };
    const result = transformFilters(filters, TYPE);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviours.EXCLUDE, values: 'deposit' } });
  });

  it('should transform several declared keys independently', () => {
    const filters: Filters = { location: '!kraken', type: 'deposit' };
    const result = transformFilters(filters, ['type', 'location']);
    expect(result).toStrictEqual({
      location: { behaviour: FilterBehaviours.EXCLUDE, values: 'kraken' },
      type: { behaviour: FilterBehaviours.INCLUDE, values: 'deposit' },
    });
  });
});

describe('collectSources', () => {
  function source(overrides: Partial<ParamSource>): ParamSource {
    return { to: 'both', values: {}, ...overrides };
  }

  it('should merge only the sources that contribute to the destination', () => {
    const sources = [
      source({ to: 'request', values: { a: 1 } }),
      source({ to: 'url', values: { b: 2 } }),
      source({ to: 'both', values: { c: 3 } }),
    ];
    expect(collectSources(sources, 'request')).toStrictEqual({ a: 1, c: 3 });
    expect(collectSources(sources, 'url')).toStrictEqual({ b: '2', c: '3' });
  });

  it('should apply the predicate filter', () => {
    const sources = [
      source({ isDefault: true, values: { a: 1 } }),
      source({ values: { b: 2 } }),
    ];
    expect(collectSources(sources, 'request', s => !!s.isDefault)).toStrictEqual({ a: 1 });
  });

  it('should drop null request values only when skipEmpty is set', () => {
    expect(collectSources([source({ skipEmpty: true, values: { a: null, b: 2 } })], 'request')).toStrictEqual({ b: 2 });
    expect(collectSources([source({ values: { a: null, b: 2 } })], 'request')).toStrictEqual({ a: null, b: 2 });
  });
});

describe('mergeParams', () => {
  function source(overrides: Partial<ParamSource>): ParamSource {
    return { to: 'request', values: {}, ...overrides };
  }

  it('should let non-default sources win over the filter, and the filter win over defaults', () => {
    const sources = [
      source({ isDefault: true, values: { shared: 'default' } }),
      source({ values: { shared: 'source' } }),
    ];
    const merged = mergeParams(sources, 'request', { shared: 'filter', only: 'filter' });
    expect(merged).toStrictEqual({ only: 'filter', shared: 'source' });
  });

  it('should let the filter override a default source', () => {
    const sources = [source({ isDefault: true, values: { shared: 'default' } })];
    expect(mergeParams(sources, 'request', { shared: 'filter' })).toStrictEqual({ shared: 'filter' });
  });
});
