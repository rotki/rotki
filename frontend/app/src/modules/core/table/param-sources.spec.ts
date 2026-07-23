import { describe, expect, it } from 'vitest';
import { FilterBehaviour, type MatchedKeywordWithBehaviour, type SearchMatcher, type StringSuggestionMatcher } from '@/modules/core/table/filtering';
import { collectSources, mergeParams, type ParamSource, transformFilters } from '@/modules/core/table/param-sources';

type Filters = MatchedKeywordWithBehaviour<string>;

function stringMatcher(overrides: Partial<Omit<StringSuggestionMatcher<string, string>, 'string'>> = {}): SearchMatcher<string, string> {
  const matcher: StringSuggestionMatcher<string, string> = {
    behaviourRequired: true,
    description: 'Type',
    key: 'type',
    string: true,
    suggestions: () => [],
    validate: () => true,
    ...overrides,
  };
  return matcher;
}

describe('transformFilters', () => {
  it('should return the filters unchanged when they are not an object', () => {
    expect(transformFilters(undefined, [stringMatcher()])).toBeUndefined();
  });

  it('should return the filters unchanged when there are no matchers', () => {
    const filters: Filters = { type: 'deposit' };
    expect(transformFilters(filters, [])).toStrictEqual({ type: 'deposit' });
  });

  it('should ignore matchers that do not require a behaviour', () => {
    const filters: Filters = { type: 'deposit' };
    const result = transformFilters(filters, [stringMatcher({ behaviourRequired: false })]);
    expect(result).toStrictEqual({ type: 'deposit' });
  });

  it('should ignore keys that are not present in the filters', () => {
    const filters: Filters = { location: 'kraken' };
    const result = transformFilters(filters, [stringMatcher({ key: 'type' })]);
    expect(result).toStrictEqual({ location: 'kraken' });
  });

  it('should ignore falsy values', () => {
    const filters: Filters = { type: '' };
    const result = transformFilters(filters, [stringMatcher()]);
    expect(result).toStrictEqual({ type: '' });
  });

  it('should wrap a plain string value with the INCLUDE behaviour', () => {
    const filters: Filters = { type: 'deposit' };
    const result = transformFilters(filters, [stringMatcher()]);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviour.INCLUDE, values: 'deposit' } });
  });

  it('should wrap a boolean value with the INCLUDE behaviour', () => {
    const filters: Filters = { type: true };
    const result = transformFilters(filters, [stringMatcher()]);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviour.INCLUDE, values: true } });
  });

  it('should use keyValue over key for the lookup', () => {
    const filters: Filters = { eventTypes: 'deposit' };
    const result = transformFilters(filters, [stringMatcher({ key: 'type', keyValue: 'eventTypes' })]);
    expect(result).toStrictEqual({ eventTypes: { behaviour: FilterBehaviour.INCLUDE, values: 'deposit' } });
  });

  it('should resolve a leading ! on a string to EXCLUDE when exclusion is allowed', () => {
    const filters: Filters = { type: '!deposit' };
    const result = transformFilters(filters, [stringMatcher({ allowExclusion: true })]);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviour.EXCLUDE, values: 'deposit' } });
  });

  it('should keep the ! and use INCLUDE when exclusion is not allowed', () => {
    const filters: Filters = { type: '!deposit' };
    const result = transformFilters(filters, [stringMatcher({ allowExclusion: false })]);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviour.INCLUDE, values: '!deposit' } });
  });

  it('should resolve a leading ! on an array to EXCLUDE and strip every element', () => {
    const filters: Filters = { type: ['!deposit', '!withdrawal'] };
    const result = transformFilters(filters, [stringMatcher({ allowExclusion: true })]);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviour.EXCLUDE, values: ['deposit', 'withdrawal'] } });
  });

  it('should keep an array as INCLUDE when its first element has no !', () => {
    const filters: Filters = { type: ['deposit', 'withdrawal'] };
    const result = transformFilters(filters, [stringMatcher({ allowExclusion: true })]);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviour.INCLUDE, values: ['deposit', 'withdrawal'] } });
  });

  it('should normalize an already-wrapped value, defaulting the behaviour to INCLUDE', () => {
    const filters: Filters = { type: { values: 'deposit' } };
    const result = transformFilters(filters, [stringMatcher()]);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviour.INCLUDE, values: 'deposit' } });
  });

  it('should preserve an explicit behaviour on an already-wrapped value', () => {
    const filters: Filters = { type: { behaviour: FilterBehaviour.EXCLUDE, values: 'deposit' } };
    const result = transformFilters(filters, [stringMatcher()]);
    expect(result).toStrictEqual({ type: { behaviour: FilterBehaviour.EXCLUDE, values: 'deposit' } });
  });

  it('should transform several matchers independently', () => {
    const filters: Filters = { location: '!kraken', type: 'deposit' };
    const result = transformFilters(filters, [
      stringMatcher({ key: 'type' }),
      stringMatcher({ allowExclusion: true, key: 'location' }),
    ]);
    expect(result).toStrictEqual({
      location: { behaviour: FilterBehaviour.EXCLUDE, values: 'kraken' },
      type: { behaviour: FilterBehaviour.INCLUDE, values: 'deposit' },
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
