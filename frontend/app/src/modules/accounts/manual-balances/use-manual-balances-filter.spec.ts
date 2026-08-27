import { describe, expect, it } from 'vitest';
import { manualBalanceTagsParams } from '@/modules/accounts/manual-balances/use-manual-balances-filter';

describe('manualBalanceTagsParams', () => {
  it('should split a comma-separated tags string into an array', () => {
    const tags = ref<string[]>([]);

    manualBalanceTagsParams(tags).source.fromQuery?.({ tags: 'a,b,c' });

    expect(get(tags)).toStrictEqual(['a', 'b', 'c']);
  });

  it('should read missing tags as an empty array', () => {
    const tags = ref<string[]>(['stale']);

    manualBalanceTagsParams(tags).source.fromQuery?.({});

    expect(get(tags)).toStrictEqual([]);
  });

  it('should send the tags to the request as a list, while the url half of the same declaration stringifies them', () => {
    const tags = ref<string[]>(['a', 'b']);

    expect(toValue(manualBalanceTagsParams(tags).source.values)).toStrictEqual({ tags: ['a', 'b'] });
  });

  it('should ride both the request and the url', () => {
    expect(manualBalanceTagsParams(ref<string[]>([])).source.to).toBe('both');
  });

  it('should draw the picked tags as a pill', () => {
    const tags = ref<string[]>(['a']);

    expect(get(manualBalanceTagsParams(tags).pillParams)).toStrictEqual({ tags: ['a'] });
  });

  it('should draw no pill when nothing is picked, emitting no key at all rather than an empty list', () => {
    expect(get(manualBalanceTagsParams(ref<string[]>([])).pillParams)).toStrictEqual({});
  });

  it('should write the ref back from the bar\'s bag', () => {
    const tags = ref<string[]>([]);
    const { pillParams } = manualBalanceTagsParams(tags);

    set(pillParams, { tags: ['a', 'b'] });
    expect(get(tags)).toStrictEqual(['a', 'b']);

    set(pillParams, {});
    expect(get(tags)).toStrictEqual([]);
  });
});
