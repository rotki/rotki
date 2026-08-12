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

  // The url carries them joined, the request carries them as a list, and both come off the one
  // declaration: the source emits the array and the url half stringifies it.
  it('should send the tags to the request as a list', () => {
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

  // Removing the pill is how the filter is turned off, so no tags means no key at all rather than
  // an empty list the bar would draw as a pill.
  it('should draw no pill when nothing is picked', () => {
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
